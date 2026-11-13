"""Compressão local de vídeos (HEVC/H.264/AV1) com fila e paralelismo.

Suporta Intel QSV, NVIDIA NVENC, AMD AMF e software (x264/x265/AV1), com
seleção de formato/contêiner, estimativa de economia por codec, progresso por
arquivo, validação da saída e substituição atômica. Usa as mesmas proteções de
subprocesso do motor de download (console oculto e kill da árvore).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    Signal,
    Slot,
)

from .i18n import translator
from .lifecycle import shutdown_threads
from .services.procutils import (
    popen_kwargs,
    spawn_kwargs,
    terminate_tree,
    wait_or_kill,
    which,
)

log = logging.getLogger("hlsdl")

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts"}
SAFE_AUDIO = {"aac", "ac3", "eac3", "mp3", "alac"}
TEXT_SUBS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text"}

# Fornecedores de encoder (a escolha do encoder real depende do codec).
ENCODER_ORDER = ("qsv", "nvenc", "amf", "software", "kvazaar")
AUTO_ORDER = ("nvenc", "amf", "qsv", "software")
ENCODER_NAMES = {
    "qsv": "Intel QSV",
    "nvenc": "NVIDIA NVENC",
    "amf": "AMD AMF",
    "software": "Software",
    "kvazaar": "Kvazaar (HEVC rápido)",
}
ENCODER_LABELS = {
    "hevc_qsv": "QSV HEVC",
    "h264_qsv": "QSV H.264",
    "av1_qsv": "QSV AV1",
    "hevc_nvenc": "NVENC HEVC",
    "h264_nvenc": "NVENC H.264",
    "av1_nvenc": "NVENC AV1",
    "hevc_amf": "AMF HEVC",
    "h264_amf": "AMF H.264",
    "av1_amf": "AMF AV1",
    "libx265": "x265",
    "libx264": "x264",
    "libsvtav1": "SVT-AV1",
    "libaom-av1": "libaom AV1",
    "libkvazaar": "Kvazaar",
}
SPEEDS = ("fast", "balanced", "slow", "slower")
DEINTERLACE_MODES = ("auto", "off", "on")
DENOISE_MODES = ("off", "light", "medium", "strong")
AUDIO_MODES = ("auto", "copy", "aac")
SUBTITLE_MODES = ("auto", "all", "none")
HDR_TRANSFERS = ("smpte2084", "arib-std-b67")
QUALITY_MAX = {"hevc": 51, "h264": 51, "av1": 63}
COMPRESSION_PRESETS = (
    "custom",
    "fast_h264",
    "balanced_hevc",
    "quality_hevc",
    "archive_hevc",
    "av1_balanced",
)
SPEED_NAMES = {
    "fast": "Fast",
    "balanced": "Balanced",
    "slow": "Slow",
    "slower": "Slower (max quality)",
}

CODECS = ("hevc", "h264", "av1")
CODEC_NAMES = {"hevc": "HEVC (H.265)", "h264": "H.264 (AVC)", "av1": "AV1"}
CONTAINERS = {
    "hevc": ("mp4", "mkv", "mov"),
    "h264": ("mp4", "mkv", "mov", "avi"),
    "av1": ("mp4", "mkv", "webm"),
}
DEFAULT_CONTAINERS = {"hevc": "mp4", "h264": "mp4", "av1": "mkv"}

ENCODER_MAP = {
    ("qsv", "hevc"): "hevc_qsv",
    ("qsv", "h264"): "h264_qsv",
    ("qsv", "av1"): "av1_qsv",
    ("nvenc", "hevc"): "hevc_nvenc",
    ("nvenc", "h264"): "h264_nvenc",
    ("nvenc", "av1"): "av1_nvenc",
    ("amf", "hevc"): "hevc_amf",
    ("amf", "h264"): "h264_amf",
    ("amf", "av1"): "av1_amf",
    ("kvazaar", "hevc"): "libkvazaar",
}

# Estimativa heurística de redução de tamanho em relação ao original
# (mesma qualidade percebida). É apenas uma referência para a UI.
ESTIMATE_BASE = {"av1": 58, "hevc": 48, "h264": 26}


class CompressStatus(str, Enum):
    WAITING = "waiting"
    ANALYZING = "analyzing"
    ENCODING = "encoding"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

    @property
    def is_final(self) -> bool:
        return self in {CompressStatus.DONE, CompressStatus.ERROR,
                        CompressStatus.CANCELLED, CompressStatus.SKIPPED}


FINAL = {CompressStatus.DONE, CompressStatus.ERROR,
         CompressStatus.CANCELLED, CompressStatus.SKIPPED}
ACTIVE = {CompressStatus.ANALYZING, CompressStatus.ENCODING}


@dataclass
class CompressionSettings:
    encoder: str = "auto"       # auto | qsv | nvenc | amf | software
    codec: str = "hevc"         # hevc | h264 | av1
    container: str = "mp4"      # mp4 | mkv | webm | mov | avi
    quality: int = 24           # 1..51
    speed: str = "balanced"     # fast | balanced | slow | slower
    parallel: int = 1
    min_size_mb: int = 0
    only_if_smaller: bool = True
    replace_original: bool = False
    reencode_hevc: bool = False
    skip_hdr: bool = True
    qsv_device: int = -1        # -1 = automático (prefere a GPU dedicada)
    ten_bit: bool = False       # x265/Kvazaar 10-bit
    x265_tuning: bool = False   # aq-mode/psy para máxima qualidade
    preset: str = "custom"      # preset da UI (não altera o encode sozinho)
    hdr_tonemap: bool = False   # converte HDR/HLG para SDR bt709
    deinterlace: str = "auto"   # auto | off | on
    denoise: str = "off"        # off | light | medium | strong
    audio_mode: str = "auto"    # auto | copy | aac
    subtitle_mode: str = "auto"  # auto | all | none


def make_item(item_id: int, path: str) -> dict:
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return {
        "id": item_id,
        "input": path,
        "name": os.path.basename(path),
        "status": CompressStatus.WAITING,
        "progress": 0.0,
        "speed": "—",
        "size_before": size,
        "size_after": 0,
        "saving": 0.0,
        "encoder": "",
        "error": "",
        "output": "",
    }


# ---------------------------------------------------------------------------
# Detecção / seleção de encoder
# ---------------------------------------------------------------------------
def detect_encoders() -> set[str]:
    """Nomes de encoders realmente disponíveis no ffmpeg (ex.: ``hevc_qsv``)."""
    ffmpeg = which("ffmpeg")
    names: set[str] = set()
    if not ffmpeg:
        return names
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        text = out.stdout or ""
    except Exception:
        return names
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0][:1] in ("V", "A", "S"):
            names.add(parts[1])
    return filter_hardware_encoders(names)


def hardware_vendors() -> set[str]:
    """Fornecedores de GPU presentes no sistema.

    O ffmpeg lista NVENC/AMF/QSV mesmo sem o hardware correspondente; usar
    essa lista sozinha fazia o modo Auto escolher ``hevc_nvenc`` em máquinas
    só com Intel, falhando na hora de comprimir.
    """
    gpus = detect_gpus()
    if not gpus:
        # Sem detecção de GPU: não filtra (melhor tentar do que remover tudo).
        return {"nvenc", "amf", "qsv"}
    text = " ".join(str(gpu.get("name", "")) for gpu in gpus).lower()
    vendors: set[str] = set()
    if any(token in text for token in ("nvidia", "geforce", "rtx", "quadro")):
        vendors.add("nvenc")
    if any(token in text for token in ("amd", "radeon", "rx ")):
        vendors.add("amf")
    if "intel" in text:
        vendors.add("qsv")
    return vendors


def filter_hardware_encoders(names: set[str]) -> set[str]:
    """Remove encoders de hardware cujo fornecedor não está presente."""
    allowed = hardware_vendors()
    filtered: set[str] = set()
    for name in names:
        if name.endswith("_nvenc") and "nvenc" not in allowed:
            continue
        if name.endswith("_amf") and "amf" not in allowed:
            continue
        if name.endswith("_qsv") and "qsv" not in allowed:
            continue
        filtered.add(name)
    return filtered


_PROBE_CACHE: dict[tuple[str, int, bool], bool] = {}


def probe_encoder(encoder: str, qsv_device: int = -1,
                  ten_bit: bool = False) -> bool:
    """Testa o encoder com 1 frame (cache por sessão).

    Alguns encoders aparecem no ffmpeg mas falham por falta de driver/GPU.
    Nesse caso o modo Auto cai para software em vez de abortar a fila.
    """
    if not encoder:
        return False
    key = (encoder, qsv_device if encoder.endswith("_qsv") else -1, bool(ten_bit))
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    ffmpeg = which("ffmpeg")
    ok = False
    if ffmpeg:
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
        if encoder.endswith("_qsv") and qsv_device >= 0:
            cmd += ["-qsv_device", str(qsv_device)]
        cmd += ["-f", "lavfi", "-i", "color=c=black:s=320x240:r=1:d=0.2"]
        if ten_bit:
            pixel_format = "p010le" if not encoder.startswith("lib") else "yuv420p10le"
            cmd += ["-pix_fmt", pixel_format]
        cmd += ["-frames:v", "1", "-c:v", encoder, "-f", "null", "-"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            ok = result.returncode == 0
        except Exception:
            ok = False
    _PROBE_CACHE[key] = ok
    return ok


def pick_encoder(vendor: str, codec: str, names: set[str]) -> str:
    """Retorna o encoder concreto do fornecedor/codec (ou "")."""
    if codec not in CODECS:
        return ""
    if vendor == "software":
        if codec == "av1":
            for candidate in ("libsvtav1", "libaom-av1"):
                if candidate in names:
                    return candidate
            return ""
        candidate = {"hevc": "libx265", "h264": "libx264"}[codec]
        return candidate if candidate in names else ""
    candidate = ENCODER_MAP.get((vendor, codec), "")
    return candidate if candidate in names else ""


def resolve_encoder(settings: CompressionSettings, names: set[str],
                    codec: str | None = None) -> str:
    codec = codec or settings.codec
    if settings.encoder in ("qsv", "nvenc", "amf", "software", "kvazaar"):
        candidates = (settings.encoder, "software")
    else:
        candidates = AUTO_ORDER
    for vendor in candidates:
        encoder = pick_encoder(vendor, codec, names)
        if encoder:
            return encoder
    return ""


def available_vendors(codec: str, names: set[str]) -> dict[str, bool]:
    return {vendor: bool(pick_encoder(vendor, codec, names))
            for vendor in ENCODER_ORDER}


def estimate_saving(codec: str, quality: int) -> int:
    """Estimativa grosseira de redução (%) em relação ao original."""
    base = ESTIMATE_BASE.get(codec, 35)
    return max(5, min(85, round(base - (int(quality) - 24) * 1.1)))


def quality_max_for_codec(codec: str) -> int:
    """Faixa de RF/quantização aceita pelo codec (AV1 vai até 63)."""
    return QUALITY_MAX.get(codec, 51)


def is_hdr_video(video: dict | None) -> bool:
    """True para HDR10/HLG (a transferência é o indicador mais confiável)."""
    transfer = str((video or {}).get("color_transfer") or "").lower()
    return transfer in HDR_TRANSFERS


def is_interlaced_video(video: dict | None) -> bool:
    """True quando o ffprobe indica campos entrelaçados."""
    order = str((video or {}).get("field_order") or "").lower()
    return order in ("tt", "bb", "tb", "bt")


def build_filters(settings: CompressionSettings, video: dict | None) -> str:
    """Monta a cadeia -vf (desentrelaçar, denoise e tone mapping HDR)."""
    filters: list[str] = []
    if settings.deinterlace == "on" or (
        settings.deinterlace == "auto" and is_interlaced_video(video)
    ):
        filters.append("yadif=deint=interlaced")
    denoise = {
        "light": "hqdn3d=1.5:1.5:6:6",
        "medium": "hqdn3d=3:3:12:12",
        "strong": "hqdn3d=6:6:24:24",
    }.get(settings.denoise)
    if denoise:
        filters.append(denoise)
    if settings.hdr_tonemap and is_hdr_video(video):
        # zscale é usado pelo HandBrake/ffmpeg para tone mapping de HDR.
        filters.append(
            "zscale=t=linear:npl=100,"
            "tonemap=hable:desat=0,"
            "zscale=p=bt709:t=bt709:m=bt709:r=tv,"
            "format=yuv420p"
        )
    return ",".join(filters)


def is_integrated_gpu(name: str) -> bool:
    value = (name or "").lower()
    if "arc" in value:
        return False
    if any(token in value for token in ("uhd", "hd graphics", "iris", "integrated")):
        return True
    if any(token in value for token in ("nvidia", "geforce", "rtx", "quadro",
                                        "radeon", "rx ")):
        return False
    return False


_GPU_CACHE: list[dict] | None = None


def detect_gpus(force: bool = False) -> list[dict]:
    """Lista as GPUs do sistema (melhor esforço, com cache)."""
    global _GPU_CACHE
    if _GPU_CACHE is not None and not force:
        return _GPU_CACHE
    names: list[str] = []
    try:
        if os.name == "nt":
            cmd = [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object -ExpandProperty Name",
            ]
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            names = [line.strip() for line in (out.stdout or "").splitlines() if line.strip()]
        elif sys.platform == "darwin":
            out = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            for line in (out.stdout or "").splitlines():
                if "Chipset Model:" in line:
                    names.append(line.split(":", 1)[1].strip())
        else:
            out = subprocess.run(
                ["lspci"], capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
            for line in (out.stdout or "").splitlines():
                if re.search(r"(VGA|3D|Display)", line, re.IGNORECASE):
                    names.append(line.split(":", 2)[-1].strip())
    except Exception:
        return []
    _GPU_CACHE = [
        {"index": i, "name": name, "integrated": is_integrated_gpu(name)}
        for i, name in enumerate(names)
    ]
    return _GPU_CACHE


def detect_qsv_devices(max_devices: int = 4) -> list[dict]:
    """Mapeia índices ``-qsv_device`` para o nome real da GPU."""
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return []
    devices: list[dict] = []
    misses = 0
    for index in range(max_devices):
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "verbose",
            "-qsv_device", str(index),
            "-f", "lavfi", "-i", "color=c=black:s=64x64:r=1",
            "-frames:v", "1", "-c:v", "hevc_qsv",
            "-global_quality", "30", "-an", "-f", "null", "-",
        ]
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **popen_kwargs(),
            )
        except Exception:
            break
        text = (out.stderr or "") + (out.stdout or "")
        match = re.search(
            r"Using device\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+\((.+)\)", text
        )
        if match:
            name = match.group(1).strip()
            if "basic render" in name.lower():
                continue
            devices.append({
                "index": index,
                "name": name,
                "integrated": is_integrated_gpu(name),
            })
            misses = 0
        elif out.returncode != 0:
            misses += 1
            if misses >= 2:
                break
    return devices


def resolve_qsv_device(preferred: int, devices: list[dict]) -> int:
    if preferred is not None and preferred >= 0:
        if not devices or any(d["index"] == preferred for d in devices):
            return preferred
    if devices:
        dedicated = [d for d in devices if not d["integrated"]]
        for device in dedicated:
            if "arc" in device["name"].lower():
                return device["index"]
        if dedicated:
            return dedicated[0]["index"]
        return devices[0]["index"]
    return 0


# ---------------------------------------------------------------------------
# Argumentos ffmpeg
# ---------------------------------------------------------------------------
def video_args(encoder: str, codec: str, quality: int, speed: str,
               ten_bit: bool = False, x265_tuning: bool = False) -> list[str]:
    q = max(1, min(quality_max_for_codec(codec), int(quality)))
    speed = speed if speed in SPEEDS else "balanced"
    tag = ["-tag:v", "hvc1"] if codec == "hevc" else []
    preset_x26x = {"fast": "fast", "balanced": "medium",
                   "slow": "slow", "slower": "slower"}[speed]
    software_pix = ["-pix_fmt", "yuv420p10le"] if ten_bit else []
    hardware_pix = ["-pix_fmt", "p010le"] if ten_bit else []
    if encoder == "libkvazaar":
        return ["-c:v", encoder, "-preset", preset_x26x,
                "-crf", str(q)] + software_pix + tag
    if encoder.endswith("_qsv"):
        preset = {"fast": "fast", "balanced": "medium",
                  "slow": "slow", "slower": "slower"}[speed]
        return ["-c:v", encoder, "-preset", preset,
                "-global_quality", str(q)] + hardware_pix + tag
    if encoder.endswith("_nvenc"):
        preset = {"fast": "p3", "balanced": "p5",
                  "slow": "p6", "slower": "p7"}[speed]
        return ["-c:v", encoder, "-gpu", "0", "-preset", preset, "-tune", "hq",
                "-rc", "vbr", "-cq", str(q), "-b:v", "0"] + hardware_pix + tag
    if encoder.endswith("_amf"):
        preset = {"fast": "speed", "balanced": "balanced",
                  "slow": "quality", "slower": "quality"}[speed]
        args = ["-c:v", encoder, "-quality", preset, "-rc", "cqp",
                "-qp_i", str(q), "-qp_p", str(q)]
        if encoder != "hevc_amf":
            # O encoder HEVC da AMF não expõe qp_b no ffmpeg.
            args += ["-qp_b", str(q)]
        return args + hardware_pix + tag
    if codec == "av1":
        preset = {"fast": "8", "balanced": "6", "slow": "4", "slower": "2"}[speed]
        if encoder == "libaom-av1":
            return ["-c:v", encoder, "-crf", str(q), "-b:v", "0",
                    "-cpu-used", preset, "-row-mt", "1"] + software_pix
        return ["-c:v", encoder, "-crf", str(q), "-preset", preset] + software_pix
    if encoder == "libx264":
        return ["-c:v", encoder, "-preset", preset_x26x, "-crf", str(q)] + software_pix
    params = ["log-level=error"]
    if x265_tuning:
        params += ["aq-mode=3", "psy-rd=2.0", "psy-rdoq=1.0", "deblock=-1,-1"]
    return (["-c:v", encoder, "-preset", preset_x26x, "-crf", str(q),
             "-x265-params", ":".join(params)] + software_pix + tag)


def probe_media(path: str) -> dict | None:
    ffprobe = which("ffprobe")
    if not ffprobe:
        return None
    cmd = [ffprobe, "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", path]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        return json.loads(out.stdout or "{}")
    except Exception:
        return None


def analyze(probe: dict) -> tuple[list, list, list, float]:
    streams = probe.get("streams", []) if probe else []
    videos = [
        s for s in streams
        if s.get("codec_type") == "video"
        and not (s.get("disposition") or {}).get("attached_pic")
    ]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    subs = [s for s in streams if s.get("codec_type") == "subtitle"]
    try:
        duration = float(probe.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return videos, audios, subs, duration


def skip_reason(settings: CompressionSettings, probe: dict) -> str:
    videos, _audios, _subs, _duration = analyze(probe)
    if not videos:
        return "no_video"
    video = videos[0]
    source_codec = (video.get("codec_name") or "").lower()
    if source_codec == settings.codec and not settings.reencode_hevc:
        return "already_codec"
    if settings.skip_hdr and is_hdr_video(video) and not settings.hdr_tonemap:
        return "hdr"
    # H.264 não é uma boa escolha para preservar HDR; sem tone mapping,
    # mantenha o original em vez de gravar metadados HDR num bitstream 8-bit.
    if is_hdr_video(video) and settings.codec == "h264" and not settings.hdr_tonemap:
        return "hdr"
    return ""


def output_path(src: str, codec: str, container: str,
                suffix: str | None = None) -> str:
    base, _ = os.path.splitext(src)
    suffix = suffix or codec
    candidate = f"{base}_{suffix}.{container}"
    n = 2
    while os.path.exists(candidate):
        candidate = f"{base}_{suffix}-{n}.{container}"
        n += 1
    return candidate


def audio_args(settings: CompressionSettings, audios: list,
               container: str) -> list[str]:
    """Argumentos de áudio por contêiner, copiando quando possível."""
    args: list[str] = []
    for i, audio in enumerate(audios):
        source = (audio.get("codec_name") or "").lower()
        try:
            channels = int(audio.get("channels") or 2)
        except (TypeError, ValueError):
            channels = 2
        bitrate = "320k" if channels > 2 else "192k"

        if container == "webm":
            if settings.audio_mode != "aac" and source in ("opus", "vorbis"):
                args += [f"-c:a:{i}", "copy"]
            else:
                args += [
                    f"-c:a:{i}", "libopus", f"-b:a:{i}",
                    "192k" if channels > 2 else "128k",
                ]
            continue
        if container == "avi":
            if settings.audio_mode != "aac" and source == "mp3":
                args += [f"-c:a:{i}", "copy"]
            else:
                args += [f"-c:a:{i}", "libmp3lame", f"-b:a:{i}", "192k"]
            continue
        # MP4/MOV/MKV
        if settings.audio_mode == "aac":
            if source == "aac":
                args += [f"-c:a:{i}", "copy"]
            else:
                args += [f"-c:a:{i}", "aac", f"-b:a:{i}", bitrate]
        elif settings.audio_mode == "copy" or container == "mkv" or source in SAFE_AUDIO:
            if container == "mkv" or source in SAFE_AUDIO:
                args += [f"-c:a:{i}", "copy"]
            else:
                args += [f"-c:a:{i}", "aac", f"-b:a:{i}", bitrate]
        else:
            args += [f"-c:a:{i}", "aac", f"-b:a:{i}", bitrate]
    return args


def subtitle_args(settings: CompressionSettings, subs: list,
                  container: str) -> list[str]:
    """Mapeia legendas e attachments preservando o que o contêiner aceita."""
    if settings.subtitle_mode == "none" or not subs:
        return ["-sn"]
    text_subs = [
        i for i, sub in enumerate(subs)
        if (sub.get("codec_name") or "").lower() in TEXT_SUBS
    ]
    if container in ("mp4", "mov"):
        if not text_subs:
            return ["-sn"]
        args: list[str] = []
        for i in text_subs:
            args += ["-map", f"0:s:{i}"]
        return args + ["-c:s", "mov_text"]
    if container == "mkv":
        selected = text_subs if settings.subtitle_mode == "auto" else list(range(len(subs)))
        if not selected:
            return ["-sn"]
        args = []
        for i in selected:
            args += ["-map", f"0:s:{i}"]
        # Fontes/anexos de ASS/SSA só existem em MKV.
        return args + ["-c:s", "copy", "-map", "0:t?", "-c:t", "copy"]
    if container == "webm":
        if not text_subs:
            return ["-sn"]
        args = []
        for i in text_subs:
            args += ["-map", f"0:s:{i}"]
        return args + ["-c:s", "webvtt"]
    return ["-sn"]


def build_args(src: str, tmp: str, settings: CompressionSettings,
               encoder: str, probe: dict, qsv_device: int = 0,
               *, progress_pipe: bool = True,
               log_level: str = "warning") -> list[str]:
    videos, audios, subs, _duration = analyze(probe)
    ffmpeg = which("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", log_level]
    if encoder.endswith("_qsv"):
        cmd += ["-qsv_device", str(qsv_device)]
    if progress_pipe:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += ["-i", src, "-map", "0:V:0", "-map", "0:a?"]

    video = videos[0] if videos else None
    filters = build_filters(settings, video)
    if filters:
        cmd += ["-vf", filters]

    cmd += audio_args(settings, audios, settings.container)
    cmd += subtitle_args(settings, subs, settings.container)

    if settings.hdr_tonemap and is_hdr_video(video):
        cmd += [
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-colorspace", "bt709",
            "-color_range", "tv",
        ]
    elif video:
        for source_key, option in (
            ("color_primaries", "-color_primaries"),
            ("color_transfer", "-color_trc"),
            ("color_space", "-colorspace"),
            ("color_range", "-color_range"),
        ):
            value = str(video.get(source_key) or "").lower()
            if value and value != "unknown":
                cmd += [option, value]

    preserve_hdr = bool(
        is_hdr_video(video) and not settings.hdr_tonemap and settings.codec != "h264"
    )
    cmd += video_args(
        encoder, settings.codec, settings.quality, settings.speed,
        ten_bit=settings.ten_bit or preserve_hdr,
        x265_tuning=settings.x265_tuning,
    )
    cmd += ["-map_chapters", "0", "-map_metadata", "0",
            "-max_muxing_queue_size", "4096"]
    if settings.container in ("mp4", "mov"):
        cmd += ["-movflags", "+faststart"]
    cmd.append(tmp)
    return cmd


def validate_output(source_probe: dict, output_probe: dict | None,
                    path: str) -> str:
    """Valida a saída antes de substituir o original.

    Retorna ``""`` quando ok ou um código curto (``empty``, ``no_video``,
    ``duration``, ``audio``). A duração é comparada com tolerância de 2% ou
    2 segundos, o que pega encodes truncados sem rejeitar diferenças normais
    de container.
    """
    if not path or not os.path.isfile(path) or os.path.getsize(path) <= 0:
        return "empty"
    out_videos, out_audios, _out_subs, out_duration = analyze(output_probe or {})
    if not out_videos:
        return "no_video"
    _src_videos, src_audios, _src_subs, src_duration = analyze(source_probe or {})
    if src_duration > 0 and out_duration > 0:
        tolerance = max(2.0, src_duration * 0.02)
        if abs(src_duration - out_duration) > tolerance:
            return "duration"
    if len(out_audios) < len(src_audios):
        return "audio"
    return ""


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
class CompressionModel(QAbstractListModel):
    ID = int(Qt.ItemDataRole.UserRole) + 1
    NAME = int(Qt.ItemDataRole.UserRole) + 2
    PATH = int(Qt.ItemDataRole.UserRole) + 3
    STATUS = int(Qt.ItemDataRole.UserRole) + 4
    PROGRESS = int(Qt.ItemDataRole.UserRole) + 5
    SPEED = int(Qt.ItemDataRole.UserRole) + 6
    SIZE_BEFORE = int(Qt.ItemDataRole.UserRole) + 7
    SIZE_AFTER = int(Qt.ItemDataRole.UserRole) + 8
    SAVING = int(Qt.ItemDataRole.UserRole) + 9
    ENCODER = int(Qt.ItemDataRole.UserRole) + 10
    ERROR = int(Qt.ItemDataRole.UserRole) + 11
    OUTPUT = int(Qt.ItemDataRole.UserRole) + 12

    def __init__(self, items: list[dict] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._items = items if items is not None else []

    def items(self) -> list[dict]:
        return self._items

    def roleNames(self) -> dict:
        return {
            self.ID: b"id", self.NAME: b"name", self.PATH: b"path",
            self.STATUS: b"status", self.PROGRESS: b"progress",
            self.SPEED: b"speed", self.SIZE_BEFORE: b"sizeBefore",
            self.SIZE_AFTER: b"sizeAfter", self.SAVING: b"saving",
            self.ENCODER: b"encoder", self.ERROR: b"error",
            self.OUTPUT: b"output",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.NAME:
            return item.get("name", "")
        if role == self.PATH:
            return item.get("input", "")
        if role == self.STATUS:
            status = item.get("status", CompressStatus.WAITING)
            return status.value if isinstance(status, CompressStatus) else str(status)
        if role == self.PROGRESS:
            return round(float(item.get("progress", 0.0)), 1)
        if role == self.SPEED:
            return item.get("speed", "—")
        if role == self.SIZE_BEFORE:
            return int(item.get("size_before", 0))
        if role == self.SIZE_AFTER:
            return int(item.get("size_after", 0))
        if role == self.SAVING:
            return round(float(item.get("saving", 0.0)), 1)
        if role == self.ENCODER:
            return item.get("encoder", "")
        if role == self.ERROR:
            return item.get("error", "")
        if role == self.OUTPUT:
            return item.get("output", "")
        if role == self.ID:
            return item.get("id", 0)
        return None

    def add(self, item: dict) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def touch(self, row: int) -> None:
        if 0 <= row < len(self._items):
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx)

    def index_of(self, item: dict) -> int:
        try:
            return self._items.index(item)
        except ValueError:
            return -1

    def remove_rows(self, rows: list[int]) -> None:
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._items):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._items.pop(row)
                self.endRemoveRows()


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
class CompressionWorker(QObject):
    statusChanged = Signal(str)
    progressChanged = Signal(float, str)
    succeeded = Signal(str, str, int, int)  # tmp, final, antes, depois
    skipped = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, src: str, settings: CompressionSettings,
                 encoder: str, translate=None, parent: QObject | None = None,
                 qsv_device: int = 0):
        super().__init__(parent)
        self.src = src
        self.settings = settings
        self.encoder = encoder
        self.qsv_device = qsv_device
        self._t = translate or translator("pt")
        self._cancel = False
        self._proc = None

    def cancel(self) -> None:
        self._cancel = True
        terminate_tree(self._proc)

    def run(self) -> None:
        try:
            self.statusChanged.emit(CompressStatus.ANALYZING.value)
            if self._cancel:
                self.cancelled.emit()
                return
            probe = probe_media(self.src)
            if self._cancel:
                self.cancelled.emit()
                return
            if not probe:
                self.failed.emit(self._t("compress_probe_failed"))
                return
            reason = skip_reason(self.settings, probe)
            if reason:
                if reason == "already_codec":
                    message = self._t(
                        "compress_skip_already_codec",
                        codec=self.settings.codec.upper(),
                    )
                else:
                    message = self._t("compress_skip_" + reason)
                self.skipped.emit(message)
                return
            _videos, _audios, _subs, duration = analyze(probe)
            final = output_path(self.src, self.settings.codec,
                                self.settings.container)
            tmp = final + ".part." + self.settings.container
            cmd = build_args(self.src, tmp, self.settings, self.encoder,
                             probe, self.qsv_device)
            if not cmd[0]:
                self.failed.emit(self._t("err_ffmpeg_missing"))
                return
            size_before = os.path.getsize(self.src)

            self.statusChanged.emit(CompressStatus.ENCODING.value)
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                **spawn_kwargs(),
            )
            stderr_lines: deque[str] = deque(maxlen=400)

            def drain() -> None:
                assert self._proc is not None and self._proc.stderr is not None
                for line in self._proc.stderr:
                    stderr_lines.append(line.rstrip())

            drainer = threading.Thread(target=drain, daemon=True)
            drainer.start()

            speed = ""
            for line in self._proc.stdout:
                line = line.strip()
                if self._cancel:
                    terminate_tree(self._proc)
                    break
                if line.startswith("speed="):
                    speed = line.split("=", 1)[1]
                    continue
                if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1_000_000
                    except ValueError:
                        continue
                    pct = min(99.0, seconds / duration * 100.0) if duration else 0.0
                    self.progressChanged.emit(pct, speed)
            rc = wait_or_kill(self._proc, timeout=10)
            drainer.join(timeout=2)
            self._proc = None

            if self._cancel:
                self._safe_remove(tmp)
                self.cancelled.emit()
                return
            if rc != 0:
                detail = " | ".join(
                    line.strip() for line in stderr_lines if line.strip()
                )
                log.error("compressão falhou rc=%s: %s", rc, detail[-2000:])
                message = detail[-800:] if detail else f"ffmpeg rc={rc}"
                self._safe_remove(tmp)
                self.failed.emit(message)
                return
            out_probe = probe_media(tmp)
            reason = validate_output(probe, out_probe, tmp)
            if reason:
                log.error("saída inválida (%s): %s", reason, tmp)
                self._safe_remove(tmp)
                self.failed.emit(
                    f"{self._t('compress_invalid_output')} ({reason})"
                )
                return
            self.succeeded.emit(tmp, final, size_before, os.path.getsize(tmp))
        except Exception as exc:
            log.exception("falha na compressão")
            self.failed.emit(self._t("compress_failed", err=exc))
        finally:
            self.finished.emit()

    @staticmethod
    def _safe_remove(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Gerenciador
# ---------------------------------------------------------------------------
class CompressionManager(QObject):
    statsChanged = Signal(int, int, int, int, int)  # waiting, encoding, done, err, skip
    stateChanged = Signal(bool, bool)              # active, paused
    qsvDevicesChanged = Signal()
    finishedAll = Signal(int, int, int)            # done, errors, skipped

    def __init__(
        self,
        model: CompressionModel,
        parent: QObject | None = None,
        worker_factory: Callable[..., CompressionWorker] = CompressionWorker,
        defer_detection: bool = False,
    ):
        super().__init__(parent)
        self.model = model
        self.items: list[dict] = model.items()
        self.settings = CompressionSettings()
        self._worker_factory = worker_factory
        self.available = set() if defer_detection else detect_encoders()
        self.qsv_devices: list[dict] = []
        self._qsv_device = 0
        self._active = False
        self._paused = False
        self._running = 0
        self._threads: dict[int, tuple[QThread, CompressionWorker, dict]] = {}
        self._job_settings: dict[int, CompressionSettings] = {}
        self._counter = 0
        self._encoder = ""
        self._t = translator("pt")
        self._emit_stats()
        if not defer_detection and any(
            name.endswith("_qsv") for name in self.available
        ):
            # Evita a lista de GPU vazia no primeiro uso, sem bloquear o
            # startup da janela.
            threading.Thread(target=self._detect_qsv_devices, daemon=True).start()

    def _detect_qsv_devices(self) -> None:
        devices = detect_qsv_devices()
        if devices:
            self.qsv_devices = devices
            self.qsvDevicesChanged.emit()

    def set_translator(self, fn) -> None:
        self._t = fn

    # ------------------------------------------------------------- settings
    def apply_settings(self, settings: CompressionSettings) -> None:
        if settings.codec not in CODECS:
            settings.codec = "hevc"
        settings.quality = max(
            1, min(quality_max_for_codec(settings.codec), int(settings.quality))
        )
        settings.parallel = max(1, min(8, int(settings.parallel)))
        settings.speed = settings.speed if settings.speed in SPEEDS else "balanced"
        settings.deinterlace = (
            settings.deinterlace if settings.deinterlace in DEINTERLACE_MODES else "auto"
        )
        settings.denoise = settings.denoise if settings.denoise in DENOISE_MODES else "off"
        settings.audio_mode = settings.audio_mode if settings.audio_mode in AUDIO_MODES else "auto"
        settings.subtitle_mode = (
            settings.subtitle_mode
            if settings.subtitle_mode in SUBTITLE_MODES
            else "auto"
        )
        settings.preset = settings.preset if settings.preset in COMPRESSION_PRESETS else "custom"
        if settings.container not in CONTAINERS[settings.codec]:
            settings.container = DEFAULT_CONTAINERS[settings.codec]
        self.settings = settings
        # Aumentar o paralelismo com itens pendentes deve aproveitar as
        # vagas imediatamente, não só quando o job atual terminar.
        if getattr(self, "_active", False) and not getattr(self, "_paused", False):
            self._pump()

    def refresh_encoders(self) -> set[str]:
        self.available = detect_encoders()
        if any(name.endswith("_qsv") for name in self.available):
            threading.Thread(target=self._detect_qsv_devices, daemon=True).start()
        return self.available

    # --------------------------------------------------------------- adding
    def add_paths(self, paths: list[str], recursive: bool = True) -> int:
        files: list[str] = []
        for path in paths:
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(path) and recursive:
                for root, _dirs, names in os.walk(path):
                    for name in names:
                        if os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                            files.append(os.path.join(root, name))
            elif os.path.isfile(path) and os.path.splitext(path)[1].lower() in VIDEO_EXTS:
                files.append(path)
        existing = {item["input"] for item in self.items}
        added = 0
        for path in sorted(dict.fromkeys(files)):
            if path in existing:
                continue
            self._counter += 1
            self.model.add(make_item(self._counter, path))
            added += 1
        if added:
            if self._active and not self._paused:
                self._pump()
            self._emit_stats()
        return added

    # -------------------------------------------------------------- control
    @Slot()
    def start(self) -> None:
        self._encoder = resolve_encoder(self.settings, self.available)
        if self._encoder.endswith("_qsv"):
            if not self.qsv_devices:
                self.qsv_devices = detect_qsv_devices()
                if self.qsv_devices:
                    self.qsvDevicesChanged.emit()
            self._qsv_device = resolve_qsv_device(
                self.settings.qsv_device, self.qsv_devices
            )
        if self._encoder and not self._encoder.startswith("lib"):
            device = self._qsv_device if self._encoder.endswith("_qsv") else -1
            if not probe_encoder(self._encoder, device, self.settings.ten_bit):
                fallback = pick_encoder(
                    "software", self.settings.codec, self.available
                )
                log.warning(
                    "encoder %s falhou no teste; usando %s",
                    self._encoder, fallback or "nenhum",
                )
                self._encoder = fallback
        if not self._encoder:
            for item in self.items:
                if item["status"] == CompressStatus.WAITING:
                    item["error"] = self._t("err_ffmpeg_missing")
                    self._set_status(item, CompressStatus.ERROR)
            return
        log.info("compressão: encoder=%s codec=%s container=%s qsv_device=%s",
                 self._encoder, self.settings.codec, self.settings.container,
                 self._qsv_device)
        threshold = self.settings.min_size_mb * 1024 * 1024
        if threshold:
            for item in self.items:
                if (
                    item["status"] == CompressStatus.WAITING
                    and 0 < item["size_before"] < threshold
                ):
                    item["error"] = self._t("compress_skip_small")
                    self._set_status(item, CompressStatus.SKIPPED)
        self._active = True
        self._paused = False
        self._pump()
        self._emit_stats()
        self._emit_state()

    @Slot()
    def pause(self) -> None:
        self._paused = True
        self._emit_state()

    @Slot()
    def resume(self) -> None:
        self._paused = False
        self._pump()
        self._emit_state()

    @Slot()
    def cancelAll(self) -> None:
        self._active = False
        self._paused = False
        for item in self.items:
            if item["status"] in ACTIVE or item["status"] == CompressStatus.WAITING:
                self._set_status(item, CompressStatus.CANCELLED)
        for _, worker, _ in list(self._threads.values()):
            worker.cancel()
        self._emit_state()

    @Slot(int)
    def cancelItem(self, row: int) -> None:
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] in ACTIVE:
            entry = self._threads.get(item["id"])
            if entry:
                entry[1].cancel()
            self._set_status(item, CompressStatus.CANCELLED)
        elif item["status"] == CompressStatus.WAITING:
            self._set_status(item, CompressStatus.CANCELLED)

    @Slot(int)
    def removeItem(self, row: int) -> None:
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] in ACTIVE or item["status"] == CompressStatus.WAITING:
            self.cancelItem(row)
        try:
            current = self.items.index(item)
        except ValueError:
            return
        self.model.remove_rows([current])
        self._emit_stats()

    @Slot()
    def clearFinished(self) -> None:
        rows = [i for i, it in enumerate(self.items) if it["status"] in FINAL]
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()

    def shutdown(self, timeout: float = 6.0) -> None:
        """Cancela tudo e aguarda as threads (mesma proteção de queue.py)."""
        self._threads = shutdown_threads(
            self._threads,
            timeout=timeout,
            label="thread de compressão",
            cancel=self.cancelAll,
        )
        self._running = len(self._threads)

    # ------------------------------------------------------------- scheduler
    def _pump(self) -> None:
        if not self._active or self._paused:
            return
        while self._running < self.settings.parallel:
            item = next(
                (i for i in self.items if i["status"] == CompressStatus.WAITING),
                None,
            )
            if item is None:
                break
            self._launch(item)

    def _encoder_label(self, encoder: str | None = None) -> str:
        encoder = encoder or self._encoder
        label = ENCODER_LABELS.get(encoder, encoder)
        if encoder.endswith("_qsv") and self.qsv_devices:
            device = next(
                (d for d in self.qsv_devices if d["index"] == self._qsv_device),
                None,
            )
            if device:
                label = f"{label} · {device['name']}"
        return label

    def _encoder_for_job(self, settings: CompressionSettings) -> str:
        """Resolve o encoder para um job, sem reutilizar a escolha antiga.

        Mudar o codec com a fila ativa precisa usar o encoder correspondente;
        o encoder global escolhido no ``start`` não pode vazar para o job.
        """
        encoder = resolve_encoder(settings, self.available)
        if encoder and not encoder.startswith("lib"):
            device = self._qsv_device if encoder.endswith("_qsv") else -1
            if not probe_encoder(encoder, device, settings.ten_bit):
                fallback = pick_encoder("software", settings.codec, self.available)
                log.warning(
                    "encoder %s falhou no teste para o job; usando %s",
                    encoder,
                    fallback or "nenhum",
                )
                encoder = fallback
        return encoder

    def _launch(self, item: dict) -> None:
        item["status"] = CompressStatus.ANALYZING
        # Snapshot: mudar opções na UI não pode alterar um encode em curso
        # nem a decisão de apagar/substituir o original no fim.
        job_settings = replace(self.settings)
        encoder = self._encoder_for_job(job_settings)
        if not encoder:
            item["error"] = self._t("err_ffmpeg_missing")
            self._set_status(item, CompressStatus.ERROR)
            return
        item["encoder"] = self._encoder_label(encoder)
        self._job_settings[item["id"]] = job_settings
        self._touch(item)
        thread = QThread(self)
        worker = self._worker_factory(
            item["input"], job_settings, encoder, self._t,
            qsv_device=self._qsv_device,
        )
        worker.moveToThread(thread)
        # Slots do manager (thread da GUI): evita mutar modelo/QML a partir
        # da thread do encoder. Ver comentário equivalente em queue.py.
        worker._queue_item = item
        worker.statusChanged.connect(self._worker_status)
        worker.progressChanged.connect(self._worker_progress)
        worker.succeeded.connect(self._worker_success)
        worker.skipped.connect(self._worker_skipped)
        worker.failed.connect(self._worker_failed)
        worker.cancelled.connect(self._worker_cancelled)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda it=item: self._on_thread_done(it))
        self._threads[item["id"]] = (thread, worker, item)
        self._running += 1
        self._emit_stats()
        thread.start()

    # ------------------------------------------------------------ callbacks
    def _sender_item(self) -> dict | None:
        worker = self.sender()
        item = getattr(worker, "_queue_item", None)
        return item if isinstance(item, dict) else None

    @Slot(str)
    def _worker_status(self, status: str) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_status(item, status)

    @Slot(float, str)
    def _worker_progress(self, pct: float, speed: str) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_progress(item, pct, speed)

    @Slot(str, str, int, int)
    def _worker_success(self, tmp: str, final: str, before: int, after: int) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_success(item, tmp, final, before, after)

    @Slot(str)
    def _worker_skipped(self, reason: str) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_skipped(item, reason)

    @Slot(str)
    def _worker_failed(self, error: str) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_failed(item, error)

    @Slot()
    def _worker_cancelled(self) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_cancelled(item)

    def _on_status(self, item: dict, status: str) -> None:
        try:
            self._set_status(item, CompressStatus(status))
        except ValueError:
            pass

    def _on_progress(self, item: dict, pct: float, speed: str) -> None:
        item["progress"] = pct
        item["speed"] = speed or "—"
        self._touch(item)

    def _on_success(self, item: dict, tmp: str, final: str,
                    before: int, after: int) -> None:
        settings = self._job_settings.get(item["id"], self.settings)
        if settings.only_if_smaller and after >= before:
            CompressionWorker._safe_remove(tmp)
            item["size_before"] = before
            item["size_after"] = after
            item["error"] = self._t("compress_no_gain")
            self._set_status(item, CompressStatus.SKIPPED)
            return
        try:
            os.replace(tmp, final)
        except OSError as exc:
            CompressionWorker._safe_remove(tmp)
            self._on_failed(item, self._t("compress_failed", err=exc))
            return
        if settings.replace_original and os.path.abspath(final) != os.path.abspath(item["input"]):
            try:
                os.remove(item["input"])
            except OSError:
                pass
        item["output"] = final
        item["size_before"] = before
        item["size_after"] = after
        item["saving"] = round(100.0 * (1 - after / before), 1) if before else 0.0
        item["speed"] = "—"
        item["progress"] = 100.0
        self._set_status(item, CompressStatus.DONE)

    def _on_skipped(self, item: dict, reason: str) -> None:
        item["error"] = reason
        self._set_status(item, CompressStatus.SKIPPED)

    def _on_failed(self, item: dict, error: str) -> None:
        item["error"] = error
        self._set_status(item, CompressStatus.ERROR)

    def _on_cancelled(self, item: dict) -> None:
        self._set_status(item, CompressStatus.CANCELLED)

    def _on_thread_done(self, item: dict) -> None:
        self._threads.pop(item["id"], None)
        self._job_settings.pop(item["id"], None)
        self._running = max(0, self._running - 1)
        self._pump()
        self._emit_stats()

    # --------------------------------------------------------------- helpers
    def _set_status(self, item: dict, status: CompressStatus) -> None:
        item["status"] = status
        self._touch(item)
        self._emit_stats()

    def _touch(self, item: dict) -> None:
        row = self.model.index_of(item)
        if row >= 0:
            self.model.touch(row)

    def _emit_stats(self) -> None:
        waiting = sum(1 for i in self.items if i["status"] == CompressStatus.WAITING)
        encoding = sum(1 for i in self.items if i["status"] in ACTIVE)
        done = sum(1 for i in self.items if i["status"] == CompressStatus.DONE)
        errors = sum(1 for i in self.items if i["status"] == CompressStatus.ERROR)
        skipped = sum(1 for i in self.items if i["status"] == CompressStatus.SKIPPED)
        self.statsChanged.emit(waiting, encoding, done, errors, skipped)
        if (
            self._active
            and not self._paused
            and waiting == 0
            and encoding == 0
            and not self._threads
        ):
            self._active = False
            self._emit_state()
            self.finishedAll.emit(done, errors, skipped)

    def _emit_state(self) -> None:
        self.stateChanged.emit(self._active, self._paused)
