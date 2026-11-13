"""Similarity signatures, fallbacks and grouping tests."""

from __future__ import annotations

import subprocess

import pytest

from hlsdl.media import (
    MediaSignature,
    ahash_from_gray,
    compare_signatures,
    dhash_from_gray,
    group_similar,
    hdr_metadata,
    manifest_hash,
    sampled_ssim,
    source_identity,
    x265_hdr_params,
)
from hlsdl.services.procutils import popen_kwargs, which


def test_dhash_and_ahash_are_stable_and_discriminating():
    raw = bytes(range(72))
    assert len(dhash_from_gray(raw)) == 16
    assert len(ahash_from_gray(raw)) == 16
    inverted = bytes(255 - value for value in raw)
    assert dhash_from_gray(raw) != dhash_from_gray(inverted)
    assert dhash_from_gray(raw) == dhash_from_gray(bytes(range(72)))


def _sig(path: str, dhash: str = "0f0f0f0f0f0f0f0f",
         ahash: str = "aaaaaaaaaaaaaaaa", audio: tuple = (0.5, 0.6, 0.7),
         duration: float = 100.0) -> MediaSignature:
    return MediaSignature(
        path=path,
        size=1000,
        duration=duration,
        width=1920,
        height=1080,
        video_codec="h264",
        pix_fmt="yuv420p",
        frame_dhashes=(dhash, dhash, dhash),
        frame_ahashes=(ahash, ahash, ahash),
        audio_envelope=audio,
        quick_hash="q-" + path,
    )


def test_compare_identical_signatures_scores_high():
    a = _sig("a.mp4")
    b = _sig("b.mp4")
    score, method, details = compare_signatures(a, b)
    assert score >= 95
    assert method == "perceptual"
    assert details["frame_score"] == 1.0


def test_compare_different_frames_scores_lower():
    a = _sig("a.mp4", dhash="0000000000000000")
    b = _sig("b.mp4", dhash="ffffffffffffffff")
    score, _method, _details = compare_signatures(a, b)
    assert score < 80


def test_exact_sampled_hash_shortcut():
    a = _sig("a.mp4")
    b = _sig("b.mp4")
    b.quick_hash = a.quick_hash
    score, method, _details = compare_signatures(a, b)
    assert score == 100 and method == "exact-sample"


def test_metadata_fallback_without_frames_or_audio():
    a = MediaSignature(path="same-name.mp4", size=10, duration=100,
                       width=1920, height=1080)
    b = MediaSignature(path="same-name.mp4", size=10, duration=100,
                       width=1920, height=1080)
    score, method, _details = compare_signatures(a, b)
    assert method == "metadata"
    assert score >= 60


def test_group_similar_clusters_and_ignores_singletons():
    a = _sig("a.mp4", dhash="0000000000000000")
    b = _sig("b.mp4", dhash="0000000000000000")
    c = _sig("c.mp4", dhash="ffffffffffffffff", duration=100)
    groups = group_similar([a, b, c], threshold=85)
    assert len(groups) == 1
    assert {member["path"] for member in groups[0]["members"]} == {"a.mp4", "b.mp4"}


def test_manifest_hash_ignores_tokens_and_keeps_structure():
    one = "\n".join([
        "#EXTM3U",
        "#EXT-X-TARGETDURATION:6",
        "#EXT-X-MEDIA-SEQUENCE:10",
        "https://cdn/seg1.ts?token=one",
        "https://cdn/seg2.ts?token=one",
        "#EXT-X-ENDLIST",
    ])
    two = "\n".join([
        "#EXTM3U",
        "#EXT-X-TARGETDURATION:6",
        "#EXT-X-MEDIA-SEQUENCE:10",
        "https://cdn/seg1.ts?token=two",
        "https://cdn/seg2.ts?token=two",
        "#EXT-X-ENDLIST",
    ])
    assert manifest_hash(one) == manifest_hash(two)
    assert manifest_hash(one) != manifest_hash(one.replace("seg2", "seg3"))


def test_source_identity_youtube_and_generic_tokens():
    youtube = source_identity("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10")
    assert youtube["key"] == "youtube:dQw4w9WgXcQ"
    generic = source_identity("https://cdn/site/master.m3u8?token=secret&id=42")
    assert generic["kind"] == "hls"
    assert "secret" not in generic["canonical_url"]
    assert "id=42" in generic["canonical_url"]


@pytest.mark.skipif(which("ffmpeg") is None or which("ffprobe") is None,
                    reason="ffmpeg/ffprobe indisponíveis")
def test_hdr_metadata_and_x265_params():
    probe = {
        "streams": [{
            "codec_type": "video", "codec_name": "hevc",
            "width": 3840, "height": 2160, "pix_fmt": "yuv420p10le",
            "color_transfer": "smpte2084",
            "side_data_list": [
                {
                    "side_data_type": "Mastering display metadata",
                    "green_x": "13250/50000", "green_y": "34500/50000",
                    "blue_x": "7500/50000", "blue_y": "3000/50000",
                    "red_x": "34000/50000", "red_y": "16000/50000",
                    "white_point_x": "15635/50000", "white_point_y": "16450/50000",
                    "min_luminance": "50/10000", "max_luminance": "10000000/10000",
                },
                {
                    "side_data_type": "Content light level metadata",
                    "max_content": 1000, "max_average": 400,
                },
            ],
        }],
        "format": {"duration": "10"},
    }
    metadata = hdr_metadata(probe)
    assert metadata["mastering"]["max_luminance"] == "10000000/10000"
    params = x265_hdr_params(metadata)
    joined = " ".join(params)
    assert "master-display=G(13250,34500)B(7500,3000)R(34000,16000)" in joined
    assert "L(10000000,50)" in joined
    assert "max-cll=1000,400" in joined


def test_sampled_ssim_detects_a_faithful_reencode(tmp_path):
    ffmpeg = which("ffmpeg")
    source = tmp_path / "source.mp4"
    encoded = tmp_path / "encoded.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(source)],
        check=True, **popen_kwargs(),
    )
    subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(source), "-c:v", "libx264", "-crf", "30",
         "-pix_fmt", "yuv420p", str(encoded)],
        check=True, **popen_kwargs(),
    )
    score = sampled_ssim(str(source), str(encoded))
    assert score is not None and score > 0.85
