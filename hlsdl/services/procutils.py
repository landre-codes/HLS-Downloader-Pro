"""Utilitários de processo/ffmpeg: localização de binários, duração e miniaturas."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

log = logging.getLogger("hlsdl")


from .. import config


def which(name: str) -> str | None:
    """Localiza um binário no PATH e nas pastas gerenciadas/conhecidas."""
    return config.find_binary(name)


def thumbs_dir() -> str:
    from ..config import thumbs_dir as _dir

    return _dir()


def cleanup_thumbs() -> None:
    """Apaga a pasta temporária de miniaturas (chamado ao fechar o app)."""
    shutil.rmtree(thumbs_dir(), ignore_errors=True)


def probe_duration(media_url: str) -> float | None:
    """Obtém a duração total (segundos) do stream via ffprobe."""
    ffprobe = which("ffprobe")
    if not ffprobe:
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        media_url,
    ]
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40,
            encoding="utf-8",
            errors="replace",
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def extract_thumbnail(video_path: str) -> str | None:
    """Gera uma miniatura .jpg do vídeo com ffmpeg (usada na tabela).

    As miniaturas ficam em pasta TEMPORÁRIA do sistema e são apagadas ao
    fechar o app. Se falhar ou o ffmpeg não existir, retorna ``None`` sem
    afetar o download.
    """
    ffmpeg = which("ffmpeg")
    if not ffmpeg or not video_path or not os.path.exists(video_path):
        return None
    directory = thumbs_dir()
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return None
    base = os.path.splitext(os.path.basename(video_path))[0]
    thumb = os.path.join(directory, base + ".jpg")
    if os.path.exists(thumb):
        return thumb  # já existe de um download anterior na sessão
    for seek in ("2", "0"):
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            seek,
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-vf",
            "scale=320:-2",
            "-q:v",
            "4",
            thumb,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=40)
        except Exception:
            continue
        if os.path.exists(thumb):
            return thumb
    return None
