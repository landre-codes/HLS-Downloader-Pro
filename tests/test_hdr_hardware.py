"""Teste real de HDR10 com encoder de hardware (QSV).

Fica automaticamente skipado sem `HLSDL_TEST_QSV=1`. O workflow
``hardware.yml`` define a variável no runner self-hosted com Intel QSV.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from hlsdl.compress import (
    CompressionSettings,
    build_args,
    detect_encoders,
    validate_output_quality,
)
from hlsdl.media import hdr_metadata, is_hdr, probe_media
from hlsdl.services.procutils import popen_kwargs, which

pytestmark = pytest.mark.skipif(
    os.environ.get("HLSDL_TEST_QSV") != "1"
    or which("ffmpeg") is None
    or which("ffprobe") is None
    or "hevc_qsv" not in detect_encoders(),
    reason="defina HLSDL_TEST_QSV=1 em máquina com QSV real",
)


def _make_hdr10_source(path: Path) -> None:
    subprocess.run(
        [
            which("ffmpeg"),
            "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=duration=2:size=320x240:rate=24",
            "-pix_fmt", "yuv420p10le",
            "-c:v", "libx265", "-preset", "ultrafast",
            "-x265-params",
            "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:"
            "master-display=G(13250,34500)B(7500,3000)R(34000,16000)"
            "WP(15635,16450)L(10000000,50):max-cll=1000,400:hdr10=1",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc",
            "-color_range", "tv",
            "-an",
            str(path),
        ],
        check=True,
        **popen_kwargs(),
    )


@pytest.mark.parametrize("container", ["mkv", "mp4"])
def test_qsv_preserves_hdr10_metadata(tmp_path: Path, container: str):
    source = tmp_path / "hdr10-source.mp4"
    output = tmp_path / f"hdr10-qsv.{container}"
    _make_hdr10_source(source)
    source_probe = probe_media(str(source))
    assert source_probe and is_hdr(source_probe)
    source_metadata = hdr_metadata(source_probe)
    assert source_metadata.get("mastering")
    assert source_metadata.get("content_light")

    settings = CompressionSettings(
        codec="hevc",
        container=container,
        encoder="qsv",
        quality=30,
        speed="fast",
        skip_hdr=False,
        ten_bit=True,
        replace_original=False,
        only_if_smaller=False,
        subtitle_mode="none",
    )
    cmd = build_args(
        str(source), str(output), settings, "hevc_qsv", source_probe
    )
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", **popen_kwargs(),
    )
    assert result.returncode == 0, result.stderr[-1000:]

    output_probe = probe_media(str(output))
    assert output_probe and is_hdr(output_probe)
    output_metadata = hdr_metadata(output_probe)
    assert output_metadata.get("mastering")
    assert output_metadata.get("content_light")
    assert validate_output_quality(
        source_probe, output_probe, str(output), settings,
        encoder="hevc_qsv",
    ) == ""
    assert os.path.getsize(output) > 0
