"""Media probing, stable identity and perceptual signatures.

This module is intentionally dependency-light: it shells out to ``ffmpeg``/
``ffprobe`` and uses only the standard library.  It is the single place that
answers three different questions:

* *What is this media?*          -> :func:`probe_media` / :func:`analyze`
* *Is it the same remote item?*  -> :func:`source_identity` / :func:`manifest_hash`
* *Does it look/sound the same?* -> :class:`MediaSignature` + :func:`compare_signatures`

The perceptual layer is a multi-frame dHash (advanced path) with aHash,
audio-envelope, duration/resolution and filename fallbacks.  It is deliberately
not the only validation: completeness and integrity live in
:mod:`hlsdl.integrity`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import subprocess
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import USER_AGENT
from .services.procutils import popen_kwargs, which

log = logging.getLogger("hlsdl")

HDR_TRANSFERS = ("smpte2084", "arib-std-b67")
AUDIO_CODECS = {"aac", "ac3", "eac3", "mp3", "opus", "vorbis", "flac", "alac",
                "dts", "truehd", "pcm_s16le", "pcm_s24le"}

# Query parameters that identify a session/token rather than the media.  They
# are removed when building a stable source key.
_VOLATILE_PARAMS = re.compile(
    r"(?i)^(token|sig|signature|expires?|exp|hdnts|hdnea|auth|authorization|"
    r"key|policy|session|sid|jwt|access_token|download_token|verify)$"
)

_YOUTUBE_RE = re.compile(
    r"(?i)(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{6,})"
)
_VIMEO_RE = re.compile(r"(?i)vimeo\.com/(?:video/)?(\d+)")


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------
def _probe_first_frame_side_data(ffprobe: str, path: str) -> list[dict]:
    """Lê side data HDR10 do primeiro frame (SEI do HEVC/AV1).

    Em MP4/MKV com x265/HEVC, o ffprobe costuma expor mastering display e
    content-light em ``frames[0].side_data_list``, e não em
    ``stream.side_data_list``. Sem esta segunda leitura o app não enxerga
    metadados HDR10 reais.
    """
    cmd = [
        ffprobe, "-v", "error", "-print_format", "json",
        "-select_streams", "v:0", "-read_intervals", "%+#1",
        "-show_frames", "-show_entries", "frame=side_data_list", path,
    ]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        payload = json.loads(out.stdout or "{}")
    except Exception:
        return []
    frames = payload.get("frames") or []
    return list((frames[0] or {}).get("side_data_list") or []) if frames else []


def _side_data_has_hdr(items: list[dict]) -> bool:
    for item in items or []:
        kind = str(item.get("side_data_type") or "").lower()
        if "mastering display" in kind or "content light" in kind:
            return True
    return False


def probe_media(path: str) -> dict | None:
    """Return ffprobe JSON for ``path`` (local file or URL), or ``None``."""
    ffprobe = which("ffprobe")
    if not ffprobe:
        return None
    cmd = [
        ffprobe, "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", path,
    ]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        data = json.loads(out.stdout or "{}")
    except Exception:
        return None
    videos, _audios, _subs, _duration = analyze(data)
    if videos:
        transfer = str(videos[0].get("color_transfer") or "").lower()
        stream_side_data = list(videos[0].get("side_data_list") or [])
        if transfer in HDR_TRANSFERS and not _side_data_has_hdr(stream_side_data):
            frame_side_data = _probe_first_frame_side_data(ffprobe, path)
            if frame_side_data:
                data["frames"] = [{"side_data_list": frame_side_data}]
    return data


def analyze(probe: dict | None) -> tuple[list, list, list, float]:
    """Split an ffprobe result into videos, audios, subtitles and duration."""
    streams = (probe or {}).get("streams", [])
    videos = [
        s for s in streams
        if s.get("codec_type") == "video"
        and not (s.get("disposition") or {}).get("attached_pic")
    ]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    subs = [s for s in streams if s.get("codec_type") == "subtitle"]
    try:
        duration = float((probe or {}).get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return videos, audios, subs, duration


def stream_duration(stream: dict | None) -> float:
    try:
        return float((stream or {}).get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def is_hdr(probe: dict | None) -> bool:
    videos, _audios, _subs, _duration = analyze(probe)
    if not videos:
        return False
    return str(videos[0].get("color_transfer") or "").lower() in HDR_TRANSFERS


def _rational_float(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("n/a", "unknown", "none"):
        return None
    try:
        if "/" in text:
            numerator, denominator = text.split("/", 1)
            return float(numerator) / float(denominator) if float(denominator) else None
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def hdr_metadata(probe: dict | None) -> dict:
    """Extract mastering-display/content-light metadata from ffprobe.

    ffprobe exposes HDR10 static metadata as stream side data.  We keep the
    raw rational values and a normalized copy so the encoder planner and the
    validator can use them without guessing.
    """
    videos, _audios, _subs, _duration = analyze(probe)
    if not videos:
        return {}
    result: dict = {}
    side_data = list(videos[0].get("side_data_list") or [])
    if not _side_data_has_hdr(side_data):
        for frame in (probe or {}).get("frames") or []:
            side_data.extend((frame or {}).get("side_data_list") or [])
            if _side_data_has_hdr(side_data):
                break
    for item in side_data:
        kind = str(item.get("side_data_type") or "").lower()
        if "mastering display" in kind:
            result["mastering"] = {
                key: item.get(key)
                for key in (
                    "red_x", "red_y", "green_x", "green_y", "blue_x", "blue_y",
                    "white_point_x", "white_point_y", "min_luminance",
                    "max_luminance",
                )
                if item.get(key) is not None
            }
        elif "content light" in kind:
            result["content_light"] = {
                key: item.get(key)
                for key in ("max_content", "max_average")
                if item.get(key) is not None
            }
    return result


def _metadata_value(value) -> float | None:
    return _rational_float(value)


def hdr_metadata_matches(source: dict, output: dict) -> tuple[bool, str]:
    """Compara metadados HDR10 estáticos preservados entre origem e saída.

    Master display e content-light precisam sobreviver ao encode sempre que a
    interface promete preservação HDR10. A ausência de uma etiqueta na saída
    não é tratada como "formato não suporta" quando a origem a tinha: o
    chamador deve recusar a saída ou pedir confirmação explícita.
    """
    source_mastering = (source or {}).get("mastering") or {}
    output_mastering = (output or {}).get("mastering") or {}
    if source_mastering:
        if not output_mastering:
            return False, "mastering_missing"
        for key, raw in source_mastering.items():
            if key not in output_mastering:
                return False, f"mastering_{key}_missing"
            expected = _metadata_value(raw)
            actual = _metadata_value(output_mastering.get(key))
            if expected is None or actual is None:
                continue
            tolerance = max(0.0005, abs(expected) * 0.001)
            if abs(expected - actual) > tolerance:
                return False, f"mastering_{key}_mismatch"
    source_light = (source or {}).get("content_light") or {}
    output_light = (output or {}).get("content_light") or {}
    if source_light:
        if not output_light:
            return False, "content_light_missing"
        for key, raw in source_light.items():
            if key not in output_light:
                return False, f"content_light_{key}_missing"
            try:
                expected = int(float(str(raw)))
                actual = int(float(str(output_light.get(key))))
            except (TypeError, ValueError):
                continue
            if expected != actual:
                return False, f"content_light_{key}_mismatch"
    return True, "ok"


def x265_hdr_params(metadata: dict) -> list[str]:
    """Build x265 ``master-display``/``max-cll``/``hdr10-opt`` parameters."""
    params: list[str] = []
    mastering = (metadata or {}).get("mastering") or {}
    if mastering:
        def coord(key: str) -> int:
            value = _rational_float(mastering.get(key))
            return int(round((value or 0.0) * 50000))

        def luminance(key: str) -> int:
            value = _rational_float(mastering.get(key))
            return int(round((value or 0.0) * 10000))

        display = (
            f"G({coord('green_x')},{coord('green_y')})"
            f"B({coord('blue_x')},{coord('blue_y')})"
            f"R({coord('red_x')},{coord('red_y')})"
            f"WP({coord('white_point_x')},{coord('white_point_y')})"
            f"L({luminance('max_luminance')},{luminance('min_luminance')})"
        )
        params.append(f"master-display={display}")
        params.append("hdr10-opt=1")
    light = (metadata or {}).get("content_light") or {}
    if light:
        try:
            max_content = int(float(str(light.get("max_content") or 0)))
            max_average = int(float(str(light.get("max_average") or 0)))
            if max_content or max_average:
                params.append(f"max-cll={max_content},{max_average}")
        except (TypeError, ValueError):
            pass
    return params


def media_summary(probe: dict | None) -> dict:
    """Small, JSON-safe summary used in completion sidecars and the UI."""
    videos, audios, subs, duration = analyze(probe)
    video = videos[0] if videos else {}
    audio_items = []
    for track in audios:
        try:
            channels = int(track.get("channels") or 0)
        except (TypeError, ValueError):
            channels = 0
        audio_items.append({
            "codec": str(track.get("codec_name") or ""),
            "channels": channels,
            "sample_rate": str(track.get("sample_rate") or ""),
            "language": str((track.get("tags") or {}).get("language") or ""),
            "duration": stream_duration(track),
        })
    subtitle_items = [
        {
            "codec": str(track.get("codec_name") or ""),
            "language": str((track.get("tags") or {}).get("language") or ""),
        }
        for track in subs
    ]
    try:
        bit_rate = int((probe or {}).get("format", {}).get("bit_rate") or 0)
    except (TypeError, ValueError):
        bit_rate = 0
    return {
        "duration": round(duration, 3),
        "bit_rate": bit_rate,
        "video": {
            "codec": str(video.get("codec_name") or ""),
            "profile": str(video.get("profile") or ""),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "pix_fmt": str(video.get("pix_fmt") or ""),
            "color_primaries": str(video.get("color_primaries") or ""),
            "color_transfer": str(video.get("color_transfer") or ""),
            "color_space": str(video.get("color_space") or ""),
            "color_range": str(video.get("color_range") or ""),
            "field_order": str(video.get("field_order") or ""),
            "nb_frames": str(video.get("nb_frames") or ""),
            "duration": stream_duration(video),
        },
        "audio": audio_items,
        "subtitles": subtitle_items,
        "hdr": is_hdr(probe),
        "hdr_metadata": hdr_metadata(probe),
    }


def parse_fraction(value: str | None) -> float:
    """Parse ffprobe rationals such as ``30000/1001``."""
    if not value:
        return 0.0
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            return float(num) / float(den) if float(den) else 0.0
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


# ---------------------------------------------------------------------------
# Frame / audio perceptual signatures
# ---------------------------------------------------------------------------
def _run_ffmpeg_raw(args: list[str], timeout: int = 20) -> bytes:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return b""
    cmd = [ffmpeg, "-v", "error", "-nostdin", *args]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout, **popen_kwargs()
        )
        return result.stdout if result.returncode == 0 else b""
    except Exception:
        return b""


def dhash_from_gray(raw: bytes, width: int = 9, height: int = 8) -> str:
    """64-bit difference hash from a 9x8 grayscale frame."""
    if len(raw) < width * height:
        return ""
    bits = 0
    for y in range(height):
        row = y * width
        for x in range(width - 1):
            bits = (bits << 1) | int(raw[row + x] > raw[row + x + 1])
    return f"{bits:016x}"


def ahash_from_gray(raw: bytes, width: int = 9, height: int = 8) -> str:
    """64-bit average hash from the top-left 8x8 area of a 9x8 frame."""
    if len(raw) < width * height:
        return ""
    values = [raw[y * width + x] for y in range(8) for x in range(8)]
    mean = sum(values) / len(values)
    bits = 0
    for value in values:
        bits = (bits << 1) | int(value > mean)
    return f"{bits:016x}"


def frame_hashes(path: str, samples: int = 5,
                 cancel: Callable[[], bool] | None = None) -> tuple[list[str], list[str]]:
    """Sample frame dHash/aHash, stopping early when ``cancel()`` is true."""
    """Sample frames across the file and return dHash/aHash lists.

    Uses fast seeks before ``-i`` and a tiny grayscale scale.  This is the
    advanced path; callers must handle an empty result as a fallback.
    """
    probe = probe_media(path)
    _videos, _audios, _subs, duration = analyze(probe)
    if duration <= 0:
        timestamps = [0.0]
    else:
        fractions = [0.05, 0.25, 0.50, 0.75, 0.95]
        if samples <= 1:
            fractions = [0.50]
        elif samples < len(fractions):
            step = 1.0 / samples
            fractions = [step * (i + 0.5) for i in range(samples)]
        timestamps = [max(0.0, min(duration - 0.05, duration * f)) for f in fractions]
    dhashes: list[str] = []
    ahashes: list[str] = []
    for timestamp in dict.fromkeys(round(t, 3) for t in timestamps):
        if cancel is not None and cancel():
            return [], []
        raw = _run_ffmpeg_raw([
            "-ss", f"{timestamp:.3f}", "-i", path,
            "-frames:v", "1", "-an", "-sn",
            "-vf", "scale=9:8:flags=area,format=gray",
            "-f", "rawvideo", "pipe:1",
        ])
        dhash = dhash_from_gray(raw)
        ahash = ahash_from_gray(raw)
        if dhash and ahash:
            dhashes.append(dhash)
            ahashes.append(ahash)
    return dhashes, ahashes


def audio_envelope(path: str, bins: int = 8, max_seconds: int = 300) -> list[float]:
    """Coarse RMS envelope (0..1) from the first audio track.

    ffmpeg's ``astats`` + ``ametadata`` gives one RMS value per second.  The
    values are normalized and reduced to ``bins``; this is a robust fallback
    when video frames are unavailable (audio-only files, broken video).
    """
    probe = probe_media(path)
    _videos, audios, _subs, _duration = analyze(probe)
    if not audios:
        return []
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return []
    cmd = [
        ffmpeg, "-v", "error", "-nostdin", "-i", path,
        "-map", "0:a:0", "-t", str(int(max_seconds)),
        "-af",
        "aresample=8000,asetnsamples=n=8000,"
        "astats=metadata=1:reset=1,"
        "ametadata=mode=print:file=-",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        text = result.stdout or ""
    except Exception:
        return []
    values: list[float] = []
    for line in text.splitlines():
        match = re.search(r"lavfi\.astats\.Overall\.RMS_level=([-\d.]+|inf|-inf)", line)
        if not match:
            continue
        raw = match.group(1).lower()
        if raw in ("-inf", "inf"):
            values.append(0.0)
            continue
        try:
            db = float(raw)
        except ValueError:
            continue
        values.append(max(0.0, min(1.0, (db + 60.0) / 60.0)))
    if not values:
        return []
    if len(values) <= bins:
        return [round(v, 3) for v in values]
    chunk = len(values) / bins
    reduced = []
    for i in range(bins):
        start = int(i * chunk)
        end = int((i + 1) * chunk) or start + 1
        segment = values[start:end]
        reduced.append(round(sum(segment) / len(segment), 3) if segment else 0.0)
    return reduced


def sampled_ssim(source: str, output: str, samples: int = 3,
                 seconds: float = 2.0) -> float | None:
    """Mean SSIM over a few evenly spaced clips, or ``None`` if unavailable.

    This is a pragmatic quality gate for normal SDR re-encodes.  Filters that
    intentionally change pixels (tone mapping, denoise, deinterlace) should
    skip it; the caller decides that policy.
    """
    ffmpeg = which("ffmpeg")
    if not ffmpeg or not os.path.isfile(source) or not os.path.isfile(output):
        return None
    source_probe = probe_media(source)
    output_probe = probe_media(output)
    src_videos, _sa, _ss, src_duration = analyze(source_probe)
    out_videos, _oa, _os, out_duration = analyze(output_probe)
    if not src_videos or not out_videos:
        return None
    if (int(src_videos[0].get("width") or 0) != int(out_videos[0].get("width") or 0)
            or int(src_videos[0].get("height") or 0)
            != int(out_videos[0].get("height") or 0)):
        return None
    duration = min(x for x in (src_duration, out_duration) if x > 0) if (
        src_duration > 0 or out_duration > 0
    ) else 0
    if duration <= 0:
        return None
    fractions = [0.10, 0.50, 0.90] if samples >= 3 else [0.50]
    if samples == 1:
        fractions = [0.50]
    elif samples == 2:
        fractions = [0.25, 0.75]
    values: list[float] = []
    for fraction in fractions[:samples]:
        timestamp = max(0.0, min(duration - 0.1, duration * fraction))
        clip = max(0.2, min(float(seconds), max(0.2, duration - timestamp)))
        cmd = [
            ffmpeg, "-v", "info", "-nostdin",
            "-ss", f"{timestamp:.3f}", "-i", source,
            "-ss", f"{timestamp:.3f}", "-i", output,
            "-t", f"{clip:.3f}",
            "-lavfi", "[0:v][1:v]ssim", "-f", "null", "-",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
        except Exception:
            continue
        matches = re.findall(r"All:([0-9.]+)", result.stderr or "")
        if matches:
            try:
                values.append(float(matches[-1]))
            except ValueError:
                continue
    return round(sum(values) / len(values), 5) if values else None


def _quick_hash(path: str) -> str:
    """Cheap content fingerprint: size + first/last 1 MiB."""
    try:
        size = os.path.getsize(path)
        digest = hashlib.sha256()
        digest.update(str(size).encode("ascii"))
        with open(path, "rb") as handle:
            digest.update(handle.read(1024 * 1024))
            if size > 2 * 1024 * 1024:
                handle.seek(max(0, size - 1024 * 1024))
                digest.update(handle.read(1024 * 1024))
        return digest.hexdigest()
    except OSError:
        return ""


@dataclass
class MediaSignature:
    path: str
    size: int = 0
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    pix_fmt: str = ""
    audio_codecs: tuple[str, ...] = ()
    audio_channels: tuple[int, ...] = ()
    frame_dhashes: tuple[str, ...] = ()
    frame_ahashes: tuple[str, ...] = ()
    audio_envelope: tuple[float, ...] = ()
    quick_hash: str = ""
    error: str = ""
    probe: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size": self.size,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "video_codec": self.video_codec,
            "pix_fmt": self.pix_fmt,
            "audio_codecs": list(self.audio_codecs),
            "audio_channels": list(self.audio_channels),
            "frame_dhashes": list(self.frame_dhashes),
            "frame_ahashes": list(self.frame_ahashes),
            "audio_envelope": list(self.audio_envelope),
            "quick_hash": self.quick_hash,
            "error": self.error,
        }


def build_signature(path: str, with_frames: bool = True,
                    with_audio: bool = True,
                    cancel: Callable[[], bool] | None = None) -> MediaSignature:
    """Build a perceptual/metadata signature, degrading gracefully.

    ``cancel`` é consultado entre etapas caras (hash, frames, áudio) para que o
    encerramento do app não espere uma análise longa terminar.
    """
    signature = MediaSignature(path=path)
    if cancel is not None and cancel():
        signature.error = "cancelled"
        return signature
    try:
        signature.size = os.path.getsize(path)
    except OSError:
        signature.error = "missing"
        return signature
    signature.quick_hash = _quick_hash(path)
    if cancel is not None and cancel():
        signature.error = "cancelled"
        return signature
    probe = probe_media(path) or {}
    signature.probe = probe
    videos, audios, _subs, duration = analyze(probe)
    signature.duration = duration
    if videos:
        video = videos[0]
        signature.width = int(video.get("width") or 0)
        signature.height = int(video.get("height") or 0)
        signature.video_codec = str(video.get("codec_name") or "")
        signature.pix_fmt = str(video.get("pix_fmt") or "")
        if with_frames:
            try:
                dhashes, ahashes = frame_hashes(path, cancel=cancel)
                signature.frame_dhashes = tuple(dhashes)
                signature.frame_ahashes = tuple(ahashes)
            except Exception:
                log.debug("frame signature failed for %s", path, exc_info=True)
    if cancel is not None and cancel():
        signature.error = "cancelled"
        return signature
    signature.audio_codecs = tuple(
        str(track.get("codec_name") or "") for track in audios
    )
    channels = []
    for track in audios:
        try:
            channels.append(int(track.get("channels") or 0))
        except (TypeError, ValueError):
            channels.append(0)
    signature.audio_channels = tuple(channels)
    if with_audio and audios:
        try:
            signature.audio_envelope = tuple(audio_envelope(path))
        except Exception:
            log.debug("audio signature failed for %s", path, exc_info=True)
    return signature


def _hamming(a: str, b: str) -> int:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except ValueError:
        return 64


def _frame_score(a: MediaSignature, b: MediaSignature) -> float | None:
    pairs = list(zip(a.frame_dhashes, b.frame_dhashes, strict=False))
    if not pairs:
        pairs = list(zip(a.frame_ahashes, b.frame_ahashes, strict=False))
        divisor = 64.0
    else:
        divisor = 64.0
    if not pairs:
        return None
    # A small temporal offset is possible when the samples fall near scene
    # boundaries.  Compare the aligned pairs and a one-step shift, keeping the
    # best result.
    candidates: list[float] = []
    for shift in (0, -1, 1):
        aligned = []
        for i, ahash in enumerate(a.frame_dhashes or a.frame_ahashes):
            j = i + shift
            if 0 <= j < len(b.frame_dhashes or b.frame_ahashes):
                other = (b.frame_dhashes or b.frame_ahashes)[j]
                aligned.append(1.0 - _hamming(ahash, other) / divisor)
        if aligned:
            candidates.append(sum(aligned) / len(aligned))
    return max(candidates) if candidates else None


def _envelope_score(a: MediaSignature, b: MediaSignature) -> float | None:
    left, right = list(a.audio_envelope), list(b.audio_envelope)
    if not left or not right:
        return None
    size = min(len(left), len(right))
    left, right = left[:size], right[:size]
    dot = sum(x * y for x, y in zip(left, right, strict=False))
    norm = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    if norm <= 0:
        return None
    return max(0.0, min(1.0, dot / norm))


def _name_score(a: MediaSignature, b: MediaSignature) -> float:
    name_a = os.path.splitext(os.path.basename(a.path))[0].lower()
    name_b = os.path.splitext(os.path.basename(b.path))[0].lower()
    return SequenceMatcher(None, name_a, name_b).ratio()


def compare_signatures(a: MediaSignature, b: MediaSignature) -> tuple[float, str, dict]:
    """Compare two signatures and return ``(score 0..100, method, details)``."""
    details: dict = {}
    if a.quick_hash and a.quick_hash == b.quick_hash and a.size == b.size and a.size > 0:
        return 100.0, "exact-sample", {"reason": "same size + sampled hash"}
    if not a.size or not b.size:
        return 0.0, "none", {"reason": "missing file"}

    duration_score = 1.0
    if a.duration > 0 and b.duration > 0:
        tolerance = max(1.5, 0.02 * max(a.duration, b.duration))
        delta = abs(a.duration - b.duration)
        duration_score = max(0.0, 1.0 - delta / tolerance) if delta > tolerance else 1.0
    details["duration_delta"] = round(abs(a.duration - b.duration), 3)

    resolution_score = 1.0
    if a.width and b.width and a.height and b.height:
        ratio = min(a.width / b.width, b.width / a.width)
        ratio *= min(a.height / b.height, b.height / a.height)
        resolution_score = max(0.0, min(1.0, ratio))
    details["resolution_score"] = round(resolution_score, 3)

    frame_score = _frame_score(a, b)
    envelope_score = _envelope_score(a, b)
    name_score = _name_score(a, b)
    details["frame_score"] = round(frame_score, 3) if frame_score is not None else None
    details["audio_score"] = round(envelope_score, 3) if envelope_score is not None else None

    if frame_score is not None:
        weights = {"frame": 0.65, "audio": 0.15, "duration": 0.10, "resolution": 0.05, "name": 0.05}
        if envelope_score is None:
            weights = {"frame": 0.80, "duration": 0.10, "resolution": 0.05, "name": 0.05}
        score = (
            weights.get("frame", 0) * frame_score
            + weights.get("audio", 0) * (envelope_score or 0)
            + weights.get("duration", 0) * duration_score
            + weights.get("resolution", 0) * resolution_score
            + weights.get("name", 0) * name_score
        )
        method = "perceptual"
    elif a.audio_envelope and b.audio_envelope:
        score = 0.70 * (envelope_score or 0) + 0.15 * duration_score + 0.10 * resolution_score + 0.05 * name_score
        method = "audio"
    else:
        score = 0.50 * duration_score + 0.25 * resolution_score + 0.25 * name_score
        method = "metadata"
    return round(max(0.0, min(1.0, score)) * 100.0, 1), method, details


def group_similar(signatures: list[MediaSignature], threshold: float = 85.0,
                  cancel: Callable[[], bool] | None = None) -> list[dict]:
    """Cluster signatures using pairwise similarity (union-find)."""
    parent = list(range(len(signatures)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        ra, rb = find(left), find(right)
        if ra != rb:
            parent[rb] = ra

    pair_scores: dict[tuple[int, int], tuple[float, str, dict]] = {}
    for i in range(len(signatures)):
        if cancel is not None and cancel():
            return []
        for j in range(i + 1, len(signatures)):
            if cancel is not None and cancel():
                return []
            a, b = signatures[i], signatures[j]
            # Cheap prefilter: wildly different durations/resolutions are not
            # worth running the expensive comparisons.
            if a.duration and b.duration:
                if abs(a.duration - b.duration) > max(5.0, 0.10 * max(a.duration, b.duration)):
                    continue
            score, method, details = compare_signatures(a, b)
            if score >= threshold:
                union(i, j)
            pair_scores[(i, j)] = (score, method, details)

    clusters: dict[int, list[int]] = {}
    for index in range(len(signatures)):
        clusters.setdefault(find(index), []).append(index)
    groups: list[dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        scores = []
        methods = set()
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                key = (min(members[x], members[y]), max(members[x], members[y]))
                item = pair_scores.get(key)
                if item:
                    scores.append(item[0])
                    methods.add(item[1])
        groups.append({
            "members": [
                {
                    "path": signatures[index].path,
                    "size": signatures[index].size,
                    "duration": signatures[index].duration,
                    "width": signatures[index].width,
                    "height": signatures[index].height,
                }
                for index in members
            ],
            "score": round(max(scores), 1) if scores else 0.0,
            "average": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "method": "/".join(sorted(methods)) if methods else "metadata",
        })
    groups.sort(key=lambda item: (-item["score"], -len(item["members"])))
    return groups


# ---------------------------------------------------------------------------
# Remote identity
# ---------------------------------------------------------------------------
def _clean_query(query: str) -> str:
    pairs = [(k, v) for k, v in parse_qsl(query, keep_blank_values=True)
             if not _VOLATILE_PARAMS.match(k)]
    return urlencode(pairs)


def canonical_url(url: str) -> str:
    """Remove volatile query parameters and fragments, keep path case."""
    value = (url or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if not parts.scheme and not parts.netloc:
        return value.rstrip("/")
    return urlunsplit((
        parts.scheme.lower(), parts.netloc.lower(), parts.path,
        _clean_query(parts.query), "",
    ))


def manifest_hash(text: str) -> str:
    """Stable hash of an HLS manifest, ignoring session tokens/order noise."""
    digest = hashlib.sha256()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-MEDIA-SEQUENCE") or \
           line.startswith("#EXT-X-TARGETDURATION") or \
           line.startswith("#EXT-X-PLAYLIST-TYPE") or \
           line.startswith("#EXT-X-ENDLIST"):
            digest.update(line.encode("utf-8", "replace"))
            digest.update(b"\n")
            continue
        if line.startswith("#"):
            continue
        # URI line: strip query/fragment so rotating tokens do not change it.
        try:
            parts = urlsplit(line)
            normalized = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        except ValueError:
            normalized = line
        digest.update(normalized.encode("utf-8", "replace"))
        digest.update(b"\n")
    return digest.hexdigest()


def fetch_manifest_text(url: str, timeout: int = 15) -> str | None:
    """Fetch a local/HTTP m3u8 for identity. Network failures are non-fatal."""
    if not url:
        return None
    lower = url.lower()
    if not (lower.startswith("http://") or lower.startswith("https://") or lower.endswith(".m3u8")):
        return None
    if lower.startswith(("http://", "https://")):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(2_000_000).decode("utf-8", "replace")
        except Exception:
            log.debug("manifest fetch failed: %s", url, exc_info=True)
            return None
    try:
        with open(url, encoding="utf-8", errors="replace") as handle:
            return handle.read(2_000_000)
    except OSError:
        return None


def source_identity(url: str) -> dict:
    """Return a stable identity dict for a remote URL.

    ``key`` is suitable as a catalog primary key; ``canonical_url`` is the
    human/debug URL.  The HLS manifest hash is added by the caller when a
    manifest is available (see :func:`identity_with_manifest`).
    """
    value = (url or "").strip()
    youtube = _YOUTUBE_RE.search(value)
    if youtube:
        return {
            "key": f"youtube:{youtube.group(1)}",
            "kind": "youtube",
            "id": youtube.group(1),
            "canonical_url": canonical_url(value),
            "manifest_hash": "",
        }
    vimeo = _VIMEO_RE.search(value)
    if vimeo:
        return {
            "key": f"vimeo:{vimeo.group(1)}",
            "kind": "vimeo",
            "id": vimeo.group(1),
            "canonical_url": canonical_url(value),
            "manifest_hash": "",
        }
    canonical = canonical_url(value) or value
    digest = hashlib.sha256(canonical.encode("utf-8", "replace")).hexdigest()
    kind = "hls" if ".m3u8" in value.lower() else "web"
    return {
        "key": f"{kind}:{digest}",
        "kind": kind,
        "id": "",
        "canonical_url": canonical,
        "manifest_hash": "",
    }


def identity_with_manifest(url: str, manifest_text: str | None = None) -> dict:
    identity = source_identity(url)
    if manifest_text:
        mhash = manifest_hash(manifest_text)
        identity["manifest_hash"] = mhash
        identity["key"] = f"hls:{mhash}"
        identity["kind"] = "hls"
    return identity


def hamming_hex(a: str, b: str) -> int:
    return _hamming(a, b)
