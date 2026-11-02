"""Constantes de formatos suportados (fonte única de verdade)."""

from __future__ import annotations

# Modos de extração.
FORMAT_MODES = ("video_audio", "video_only", "audio_only")

# Qualidade (altura do vídeo). "best" = sem limite.
QUALITIES = ("best", "2160", "1440", "1080", "720", "480", "360", "240", "144")

# Contêineres de saída.
VIDEO_CONTAINERS = ("mp4", "mkv", "webm", "avi", "mov")
AUDIO_CONTAINERS = ("mp3", "m4a", "wav", "flac", "opus")

DEFAULT_VIDEO_CONTAINER = "mp4"
DEFAULT_AUDIO_CONTAINER = "mp3"

# Compressão/reencode de vídeo.
CODECS = ("copy", "h264", "h265")
COMPRESS_LEVELS = ("light", "medium", "strong")

# Nome do arquivo: id estável (hash da URL) ou título da página.
NAMING_MODES = ("id", "title")

# CRF por codec/nível (menor = melhor qualidade e maior tamanho).
CRF = {
    "h264": {"light": 18, "medium": 23, "strong": 28},
    "h265": {"light": 22, "medium": 28, "strong": 32},
}

