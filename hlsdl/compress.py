"""Compressão local de vídeos (HEVC/H.264/AV1) com fila e paralelismo.

Suporta Intel QSV, NVIDIA NVENC, AMD AMF e software (x264/x265/AV1), com
seleção de formato/contêiner, estimativa de economia por codec, progresso por
arquivo, validação da saída e substituição atômica. Usa as mesmas proteções de
subprocesso do motor de download (console oculto e kill da árvore).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
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

from . import config
from .catalog import Catalog
from .i18n import translator
from .integrity import (
    FileGuard,
    JobJournal,
    build_completion,
    disk_space_ok,
    install_output,
    release_output_path,
    reserve_output_path,
    sha256_file,
    write_completion,
)
from .jobs import JobThreadRegistry
from .media import (
    HDR_TRANSFERS,
    hdr_metadata,
    sampled_ssim,
    stream_duration,
    x265_hdr_params,
)
from .media import analyze as _media_analyze
from .media import is_hdr as _media_is_hdr
from .media import probe_media as _media_probe_media
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

# Valores aceitos pelos encoders/ffmpeg para tags de cor. Metadados
# "reserved"/"unknown"/"unspecified" (ou lixo de container) não podem
# ser repassados como opção do encoder — o hevc_qsv, por exemplo,
# aborta o job com "Unable to parse color_primaries option value reserved".
COLOR_PRIMARIES = {
    "bt709", "bt470m", "bt470bg", "smpte170m", "smpte240m", "film",
    "bt2020", "smpte428", "smpte431", "smpte432", "jedec-p22", "ebu3213",
}
COLOR_TRANSFERS = {
    "bt709", "gamma22", "gamma28", "smpte170m", "smpte240m", "linear",
    "log", "log_sqrt", "iec61966_2_4", "iec61966_2_1", "bt1361",
    "bt2020_10", "bt2020_12", "smpte2084", "smpte428", "arib_std_b67",
    "iec61966-2-4", "iec61966-2-1", "bt2020-10", "bt2020-12",
    "arib-std-b67", "bt1361e",
}
COLOR_SPACES = {
    "gbr", "bt709", "fcc", "bt470bg", "smpte170m", "smpte240m", "ycgco",
    "bt2020nc", "bt2020c", "smpte2085", "chroma-derived-nc",
    "chroma-derived-c", "ictcp",
}
COLOR_RANGES = {"tv", "pc", "mpeg", "jpeg"}


def safe_color_value(value, allowed: set[str]) -> str:
    """Normaliza uma tag de cor ou devolve "" quando não é segura."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else ""


class CompressStatus(str, Enum):
    WAITING = "waiting"
    ANALYZING = "analyzing"
    ENCODING = "encoding"
    VERIFYING = "verifying"
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
ACTIVE = {CompressStatus.ANALYZING, CompressStatus.ENCODING,
          CompressStatus.VERIFYING}


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
    hw_decode: bool = False     # -hwaccel auto (QSV/NVDEC/AMF quando disponível)
    crop: str = ""              # "w:h:x:y"
    scale_width: int = 0        # 0 = manter
    scale_height: int = 0       # 0 = manter
    rotate: int = 0             # 0/90/180/270
    fps: float = 0.0            # 0 = manter
    preset: str = "custom"      # preset da UI (não altera o encode sozinho)
    hdr_tonemap: bool = False   # converte HDR/HLG para SDR bt709
    deinterlace: str = "auto"   # auto | off | on
    denoise: str = "off"        # off | light | medium | strong
    audio_mode: str = "auto"    # auto | copy | aac
    subtitle_mode: str = "auto"  # auto | all | none
    quality_check: bool = True   # sampled SSIM for normal re-encodes


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
        "backup": "",
        "sha256": "",
        "validation": "",
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
        # ffmpeg -encoders lines start with flags such as "V....D"; section
        # headers ("V..... = Video") and audio/subtitle encoders must not enter
        # the video encoder capability set.
        if (len(parts) >= 3 and parts[0].startswith("V")
                and parts[1] not in ("=", "-----")):
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
    # RF maior = mais quantiza??o = arquivo menor; a economia cresce com o RF.
    return max(5, min(85, round(base + (int(quality) - 24) * 1.1)))


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
    """Monta a cadeia -vf (geometria, fps, desentrelaçar, denoise e HDR)."""
    filters: list[str] = []
    if settings.crop and re.fullmatch(r"\d+:\d+:\d+:\d+", settings.crop.strip()):
        filters.append(f"crop={settings.crop.strip()}")
    if settings.scale_width or settings.scale_height:
        width = settings.scale_width or -2
        height = settings.scale_height or -2
        filters.append(f"scale={width}:{height}:flags=lanczos")
    if settings.rotate == 90:
        filters.append("transpose=1")
    elif settings.rotate == 270:
        filters.append("transpose=2")
    elif settings.rotate == 180:
        filters.append("hflip,vflip")
    if settings.fps and settings.fps > 0:
        filters.append(f"fps={settings.fps:g}")
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


def expected_dimensions(settings: CompressionSettings,
                        video: dict | None) -> tuple[int, int]:
    """Expected output dimensions after crop/scale/rotate."""
    width = int((video or {}).get("width") or 0)
    height = int((video or {}).get("height") or 0)
    if width <= 0 or height <= 0:
        return 0, 0
    crop = (settings.crop or "").strip()
    if re.fullmatch(r"\d+:\d+:\d+:\d+", crop):
        crop_width, crop_height, _x, _y = (int(part) for part in crop.split(":"))
        if crop_width > 0 and crop_height > 0:
            width, height = crop_width, crop_height
    if settings.scale_width > 0 and settings.scale_height > 0:
        width, height = settings.scale_width, settings.scale_height
    elif settings.scale_width > 0:
        width = settings.scale_width
        height = max(2, round(width * height / max(1, int((video or {}).get("width") or width))))
    elif settings.scale_height > 0:
        height = settings.scale_height
        width = max(2, round(height * width / max(1, int((video or {}).get("height") or height))))
    if settings.rotate in (90, 270):
        width, height = height, width
    return int(width), int(height)


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


_QSV_CACHE: list[dict] | None = None
_QSV_CACHE_LOCK = threading.Lock()


def detect_qsv_devices(max_devices: int = 4, force: bool = False) -> list[dict]:
    """Mapeia indices ``-qsv_device`` para o nome real da GPU.

    O resultado e compartilhado entre managers: abrir varias janelas/testes
    nao dispara dezenas de probes concorrentes do ffmpeg.
    """
    global _QSV_CACHE
    with _QSV_CACHE_LOCK:
        if _QSV_CACHE is not None and not force:
            return _QSV_CACHE
        ffmpeg = which("ffmpeg")
        if not ffmpeg:
            _QSV_CACHE = []
            return _QSV_CACHE
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
                r"Using device\s+[0-9a-fA-F:.]+\s+\((.+)\)", text
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
        _QSV_CACHE = devices
        return _QSV_CACHE


def reset_qsv_device_cache() -> None:
    global _QSV_CACHE
    with _QSV_CACHE_LOCK:
        _QSV_CACHE = None


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
               ten_bit: bool = False, x265_tuning: bool = False,
               hdr_params: list[str] | None = None) -> list[str]:
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
    if hdr_params:
        params += hdr_params
    return (["-c:v", encoder, "-preset", preset_x26x, "-crf", str(q),
             "-x265-params", ":".join(params)] + software_pix + tag)


def probe_media(path: str) -> dict | None:
    """Compatibility wrapper around :func:`hlsdl.media.probe_media`."""
    return _media_probe_media(path)


def analyze(probe: dict) -> tuple[list, list, list, float]:
    """Compatibility wrapper around :func:`hlsdl.media.analyze`."""
    return _media_analyze(probe)


def skip_reason(settings: CompressionSettings, probe: dict) -> str:
    videos, _audios, _subs, _duration = analyze(probe)
    if not videos:
        return "no_video"
    video = videos[0]
    source_codec = (video.get("codec_name") or "").lower()
    if source_codec == settings.codec and not settings.reencode_hevc:
        return "already_codec"
    if settings.skip_hdr and _media_is_hdr(probe) and not settings.hdr_tonemap:
        return "hdr"
    # H.264 não é uma boa escolha para preservar HDR; sem tone mapping,
    # mantenha o original em vez de gravar metadados HDR num bitstream 8-bit.
    if _media_is_hdr(probe) and settings.codec == "h264" and not settings.hdr_tonemap:
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
    if settings.hw_decode:
        # Decode with the platform decoder when available; ffmpeg falls back
        # to software if the driver cannot open the stream.
        cmd += ["-hwaccel", "auto"]
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
        for source_key, option, allowed in (
            ("color_primaries", "-color_primaries", COLOR_PRIMARIES),
            ("color_transfer", "-color_trc", COLOR_TRANSFERS),
            ("color_space", "-colorspace", COLOR_SPACES),
            ("color_range", "-color_range", COLOR_RANGES),
        ):
            value = safe_color_value(video.get(source_key), allowed)
            if value:
                cmd += [option, value]

    preserve_hdr = bool(
        is_hdr_video(video) and not settings.hdr_tonemap and settings.codec != "h264"
    )
    hdr_params = (
        x265_hdr_params(hdr_metadata(probe))
        if preserve_hdr and encoder == "libx265" else None
    )
    cmd += video_args(
        encoder, settings.codec, settings.quality, settings.speed,
        ten_bit=settings.ten_bit or preserve_hdr,
        x265_tuning=settings.x265_tuning,
        hdr_params=hdr_params,
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


def _is_10bit(pix_fmt: str) -> bool:
    value = (pix_fmt or "").lower()
    return "10" in value or value.startswith(("p010", "p016", "y210", "y216"))


def _text_sub_count(streams: list) -> int:
    return sum(
        1 for stream in streams
        if str(stream.get("codec_name") or "").lower() in TEXT_SUBS
    )


def _attachment_count(probe: dict | None) -> int:
    streams = (probe or {}).get("streams", [])
    return sum(1 for stream in streams if stream.get("codec_type") == "attachment")


def _int_or_zero(value) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def validate_visual_quality(source_path: str, output_path: str,
                            settings: CompressionSettings,
                            source_probe: dict | None) -> str:
    """Sampled SSIM gate for encodes that do not intentionally alter pixels."""
    if not settings.quality_check:
        return ""
    videos, _audios, _subs, _duration = analyze(source_probe or {})
    if not videos:
        return ""
    if (settings.hdr_tonemap or settings.denoise != "off"
            or settings.crop or settings.scale_width or settings.scale_height
            or settings.rotate in (90, 180, 270)):
        return ""  # filters/geometry intentionally change pixels
    if settings.deinterlace == "on" or (
        settings.deinterlace == "auto" and is_interlaced_video(videos[0])
    ):
        return ""
    score = sampled_ssim(source_path, output_path)
    if score is not None and score < 0.78:
        log.warning("SSIM baixo (%.3f): %s -> %s", score, source_path, output_path)
        return "quality"
    return ""


def validate_output_quality(source_probe: dict, output_probe: dict | None,
                            path: str, settings: CompressionSettings,
                            source_duration: float = 0.0,
                            encoder: str | None = None) -> str:
    """Deep validation before installing an output.

    Extends :func:`validate_output` with resolution, bit depth, color/HDR,
    audio track count/codec/channels, subtitle policy and frame/duration
    checks.  Returns ``""`` or a short machine-readable reason.
    """
    reason = validate_output(source_probe, output_probe, path)
    if reason:
        return reason
    src_videos, src_audios, src_subs, src_duration = analyze(source_probe or {})
    out_videos, out_audios, out_subs, out_duration = analyze(output_probe or {})
    if not src_videos or not out_videos:
        return "no_video"
    src_video, out_video = src_videos[0], out_videos[0]

    expected_width, expected_height = expected_dimensions(settings, src_video)
    if expected_width and expected_height:
        if (
            expected_width != _int_or_zero(out_video.get("width"))
            or expected_height != _int_or_zero(out_video.get("height"))
        ):
            return "resolution"

    expected_10bit = bool(settings.ten_bit)
    if is_hdr_video(src_video) and not settings.hdr_tonemap and settings.codec != "h264":
        expected_10bit = True
    if expected_10bit and not _is_10bit(str(out_video.get("pix_fmt") or "")):
        return "bit_depth"

    source_transfer = str(src_video.get("color_transfer") or "").lower()
    output_transfer = str(out_video.get("color_transfer") or "").lower()
    if settings.hdr_tonemap and source_transfer in HDR_TRANSFERS:
        if output_transfer and output_transfer not in ("bt709", "unknown"):
            return "color_transfer"
    elif source_transfer and source_transfer not in ("unknown", "unspecified"):
        if output_transfer and output_transfer != source_transfer:
            return "color_transfer"
        source_primaries = str(src_video.get("color_primaries") or "").lower()
        output_primaries = str(out_video.get("color_primaries") or "").lower()
        if (source_transfer in HDR_TRANSFERS and source_primaries
                and output_primaries and output_primaries != source_primaries):
            return "color_primaries"

    preserve_hdr = bool(
        is_hdr_video(src_video) and not settings.hdr_tonemap
        and settings.codec != "h264"
    )
    if preserve_hdr and encoder == "libx265":
        source_hdr = hdr_metadata(source_probe)
        output_hdr = hdr_metadata(output_probe)
        if source_hdr.get("mastering") and not output_hdr.get("mastering"):
            return "hdr_metadata"

    if len(out_audios) != len(src_audios):
        return "audio_count"
    for src_audio, out_audio in zip(src_audios, out_audios, strict=False):
        src_codec = str(src_audio.get("codec_name") or "").lower()
        out_codec = str(out_audio.get("codec_name") or "").lower()
        if settings.audio_mode == "copy" and src_codec and out_codec and src_codec != out_codec:
            return "audio_codec"
        src_channels = _int_or_zero(src_audio.get("channels"))
        out_channels = _int_or_zero(out_audio.get("channels"))
        if src_channels and out_channels and src_channels != out_channels:
            return "audio_channels"
        src_dur = stream_duration(src_audio)
        out_dur = stream_duration(out_audio)
        if src_dur and out_dur:
            tolerance = max(1.5, min(4.0, src_dur * 0.005))
            if abs(src_dur - out_dur) > tolerance:
                return "audio_duration"

    if settings.subtitle_mode == "none":
        if out_subs:
            return "subtitles"
    elif settings.container == "mkv" and settings.subtitle_mode == "all":
        if len(out_subs) < len(src_subs):
            return "subtitles"
        if _attachment_count(output_probe) < _attachment_count(source_probe):
            return "attachments"
    else:
        if _text_sub_count(out_subs) < _text_sub_count(src_subs):
            return "subtitles"

    video_duration = stream_duration(src_video)
    out_video_duration = stream_duration(out_video)
    reference = video_duration or source_duration or src_duration
    if reference and out_video_duration:
        tolerance = max(1.5, min(4.0, reference * 0.003))
        if abs(reference - out_video_duration) > tolerance:
            return "video_duration"

    src_frames = _int_or_zero(src_video.get("nb_frames"))
    out_frames = _int_or_zero(out_video.get("nb_frames"))
    if src_frames and out_frames and abs(src_frames - out_frames) > 2:
        return "frames"
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
    BACKUP = int(Qt.ItemDataRole.UserRole) + 13
    SHA256 = int(Qt.ItemDataRole.UserRole) + 14
    VALIDATION = int(Qt.ItemDataRole.UserRole) + 15

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
            self.OUTPUT: b"output", self.BACKUP: b"backup",
            self.SHA256: b"sha256", self.VALIDATION: b"validation",
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
        if role == self.BACKUP:
            return item.get("backup", "")
        if role == self.SHA256:
            return item.get("sha256", "")
        if role == self.VALIDATION:
            return item.get("validation", "")
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
    # Compatibility signal: kept for scripts/tests that used to perform the
    # final ``os.replace`` themselves.  ``tmp`` is the installed final path.
    succeeded = Signal(str, str, int, int)
    # New transactional signal: final, backup, before, after, sha256, validation
    completed = Signal(str, str, int, int, str, str)
    skipped = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, src: str, settings: CompressionSettings,
                 encoder: str, translate=None, parent: QObject | None = None,
                 qsv_device: int = 0, job_id: int | str = 0,
                 journals_dir: str | None = None,
                 catalog_path: str | None = None):
        super().__init__(parent)
        self.src = src
        self.settings = settings
        self.encoder = encoder
        self.qsv_device = qsv_device
        self.job_id = job_id
        self.journals_dir = journals_dir
        self.catalog_path = catalog_path
        self._t = translate or translator("pt")
        self._cancel = False
        self._proc = None

    def cancel(self) -> None:
        self._cancel = True
        terminate_tree(self._proc)

    def run(self) -> None:
        final = ""
        temp = ""
        journal: JobJournal | None = None
        installed = False
        try:
            self.statusChanged.emit(CompressStatus.ANALYZING.value)
            if self._cancel:
                self.cancelled.emit()
                return
            guard = FileGuard.capture(self.src)
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
            final = reserve_output_path(
                self.src, self.settings.codec, self.settings.container
            )
            temp = f"{final}.part.{uuid.uuid4().hex[:10]}.{self.settings.container}"
            journal = JobJournal.create(
                self.journals_dir or config.journals_dir(),
                self.job_id or id(self),
                self.src,
                final,
                temp,
                settings=asdict(self.settings),
                source_guard=guard,
            )
            journal.stage("encoding")
            cmd = build_args(self.src, temp, self.settings, self.encoder,
                             probe, self.qsv_device)
            if not cmd[0]:
                raise RuntimeError(self._t("err_ffmpeg_missing"))
            size_before = os.path.getsize(self.src)
            ok_space, free = disk_space_ok(
                os.path.dirname(final) or ".", int(size_before * 0.55) + 256 * 1024 * 1024
            )
            if not ok_space:
                raise RuntimeError(
                    self._t("compress_disk_space", free=free // (1024 * 1024))
                )

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
                self._cleanup(temp, final, journal)
                self.cancelled.emit()
                return
            if rc != 0:
                detail = " | ".join(
                    line.strip() for line in stderr_lines if line.strip()
                )
                log.error("compressão falhou rc=%s: %s", rc, detail[-2000:])
                message = detail[-800:] if detail else f"ffmpeg rc={rc}"
                self._cleanup(temp, final, journal)
                self.failed.emit(message)
                return
            out_probe = probe_media(temp)
            reason = validate_output_quality(
                probe, out_probe, temp, self.settings, duration,
                encoder=self.encoder,
            )
            if reason:
                log.error("saída inválida (%s): %s", reason, temp)
                self._cleanup(temp, final, journal)
                self.failed.emit(
                    f"{self._t('compress_invalid_output')} ({reason})"
                )
                return
            visual_reason = validate_visual_quality(
                self.src, temp, self.settings, probe
            )
            if visual_reason:
                self._cleanup(temp, final, journal)
                self.failed.emit(
                    f"{self._t('compress_invalid_output')} ({visual_reason})"
                )
                return
            if self._cancel:
                self._cleanup(temp, final, journal)
                self.cancelled.emit()
                return
            size_after = os.path.getsize(temp)
            if self.settings.only_if_smaller and size_after >= size_before:
                self._cleanup(temp, final, journal)
                self.skipped.emit(self._t("compress_no_gain"))
                return
            self.statusChanged.emit(CompressStatus.VERIFYING.value)
            self.progressChanged.emit(99.0, "—")
            expected_hash = sha256_file(temp)
            journal.stage(
                "validating", expected_hash=expected_hash,
                output_size=size_after,
            )

            def verify_final(path: str) -> tuple[bool, str]:
                final_probe = probe_media(path)
                final_reason = validate_output_quality(
                    probe, final_probe, path, self.settings, duration,
                    encoder=self.encoder,
                )
                return (not final_reason, final_reason or "ok")

            backup = install_output(
                temp, final, self.src,
                replace_original=self.settings.replace_original,
                expected_hash=expected_hash,
                expected_size=size_after,
                journal=journal,
                verify_final=verify_final,
            )
            installed = True
            output_hash = expected_hash
            try:
                source_key = "file:" + hashlib.sha256(
                    os.path.abspath(self.src).lower().encode("utf-8", "replace")
                ).hexdigest()
                record = build_completion(
                    final,
                    source_key=source_key,
                    source_url=self.src,
                    settings=asdict(self.settings),
                    original_backup=backup,
                    extra={
                        "encoder": self.encoder,
                        "validation": "ok",
                        "source_guard": guard.to_dict(),
                        "source_size": size_before,
                        "kind": "compression",
                    },
                )
                write_completion(final, record)
                if self.catalog_path:
                    Catalog(self.catalog_path).register(record, kind="compression")
                output_hash = record.sha256 or expected_hash
            except Exception:
                log.exception("não foi possível gravar o sidecar de conclusão")
            if journal is not None:
                journal.finish()
            self.completed.emit(
                final, backup, size_before, size_after, output_hash, "ok"
            )
            self.succeeded.emit(final, final, size_before, size_after)
        except Exception as exc:
            log.exception("falha na compressão")
            if not installed:
                self._cleanup(temp, final, journal)
            message = str(exc) or self._t("compress_failed", err=exc)
            self.failed.emit(message)
        finally:
            if journal is not None and not installed:
                journal.finish()
            if final:
                # Release the in-process reservation even after a successful
                # install; otherwise later jobs skip to -2/-3 forever.
                release_output_path(final)
            self.finished.emit()

    def _cleanup(self, temp: str, final: str, journal: JobJournal | None) -> None:
        if temp:
            self._safe_remove(temp)
        if final:
            release_output_path(final)
        if journal is not None:
            journal.finish()

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
    itemsChanged = Signal()

    def __init__(
        self,
        model: CompressionModel,
        parent: QObject | None = None,
        worker_factory: Callable[..., CompressionWorker] = CompressionWorker,
        defer_detection: bool = False,
        catalog_path: str | None = None,
    ):
        super().__init__(parent)
        self.model = model
        self.items: list[dict] = model.items()
        self.settings = CompressionSettings()
        self._worker_factory = worker_factory
        self.catalog_path = catalog_path
        self.available = set() if defer_detection else detect_encoders()
        self._encoders_ready = not defer_detection
        self.qsv_devices: list[dict] = []
        self._qsv_device = 0
        self._qsv_detection_running = False
        self._qsv_detection_done = False
        self._active = False
        self._paused = False
        self._running = 0
        self._threads = JobThreadRegistry()
        self._job_settings: dict[int, CompressionSettings] = {}
        self._counter = 0
        self._encoder = ""
        self._last_error = ""
        self._t = translator("pt")
        self._emit_stats()
        if not defer_detection and any(
            name.endswith("_qsv") for name in self.available
        ):
            # Evita a lista de GPU vazia no primeiro uso, sem bloquear o
            # startup da janela.
            threading.Thread(target=self._detect_qsv_devices, daemon=True).start()

    def _detect_qsv_devices(self) -> None:
        if self._qsv_detection_running:
            return
        self._qsv_detection_running = True
        try:
            devices = detect_qsv_devices()
            if devices:
                self.qsv_devices = devices
        except Exception:
            log.exception("falha ao detectar dispositivos QSV")
        finally:
            self._qsv_detection_running = False
            self._qsv_detection_done = True
            self.qsvDevicesChanged.emit()

    def set_translator(self, fn) -> None:
        self._t = fn

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def encoders_ready(self) -> bool:
        return self._encoders_ready

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
        settings.rotate = settings.rotate if settings.rotate in (0, 90, 180, 270) else 0
        settings.scale_width = max(0, min(7680, int(settings.scale_width or 0)))
        settings.scale_height = max(0, min(4320, int(settings.scale_height or 0)))
        try:
            settings.fps = max(0.0, min(240.0, float(settings.fps or 0)))
        except (TypeError, ValueError):
            settings.fps = 0.0
        if settings.hdr_tonemap:
            # Tone mapping produces SDR bt709; skip/preserve and 10-bit would
            # contradict the selected policy.
            settings.skip_hdr = False
            settings.ten_bit = False
        if settings.codec != "hevc":
            settings.ten_bit = False
            settings.x265_tuning = False
        if settings.container not in CONTAINERS[settings.codec]:
            settings.container = DEFAULT_CONTAINERS[settings.codec]
        self.settings = settings
        # Aumentar o paralelismo com itens pendentes deve aproveitar as
        # vagas imediatamente, não só quando o job atual terminar.
        if getattr(self, "_active", False) and not getattr(self, "_paused", False):
            self._pump()

    def refresh_encoders(self) -> set[str]:
        try:
            self.available = detect_encoders()
        finally:
            self._encoders_ready = True
        if any(name.endswith("_qsv") for name in self.available):
            self._qsv_detection_done = False
            reset_qsv_device_cache()
            threading.Thread(target=self._detect_qsv_devices, daemon=True).start()
        return self.available

    # --------------------------------------------------------------- adding
    def add_paths(self, paths: list[str], recursive: bool = True) -> int:
        files: list[str] = []

        def is_generated(name: str) -> bool:
            lower = name.lower()
            return (
                ".hlsdl-backup-" in lower
                or ".part." in lower
                or lower.endswith(".invalid")
                or lower.endswith(".hlsdl.json")
            )

        for path in paths:
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.isdir(path) and recursive:
                for root, _dirs, names in os.walk(path):
                    for name in names:
                        if (os.path.splitext(name)[1].lower() in VIDEO_EXTS
                                and not is_generated(name)):
                            files.append(os.path.join(root, name))
            elif (os.path.isfile(path)
                  and os.path.splitext(path)[1].lower() in VIDEO_EXTS
                  and not is_generated(os.path.basename(path))):
                files.append(path)
        # Windows is case-insensitive and the same file can be reached through
        # different paths/symlinks; compare canonical case-folded paths.
        def key(value: str) -> str:
            try:
                return os.path.normcase(os.path.realpath(value))
            except OSError:
                return os.path.normcase(os.path.abspath(value))

        existing = {key(item["input"]) for item in self.items}
        added = 0
        for path in sorted(dict.fromkeys(files), key=key):
            identity = key(path)
            if identity in existing:
                continue
            existing.add(identity)
            self._counter += 1
            self.model.add(make_item(self._counter, path))
            added += 1
        if added:
            if self._active and not self._paused:
                self._pump()
            self._emit_stats()
            self.itemsChanged.emit()
        return added

    # -------------------------------------------------------------- control
    @Slot()
    def start(self) -> bool:
        """Start the queue.  Returns False when detection is still pending.

        The caller must not mark items as failed just because the asynchronous
        encoder probe has not finished yet (see the startup race fixed here).
        """
        self._last_error = ""
        if not self.available:
            self._last_error = "no_encoder" if self._encoders_ready else "detecting"
            return False
        self._encoder = resolve_encoder(self.settings, self.available)
        if self._encoder.endswith("_qsv"):
            if not self.qsv_devices and not self._qsv_detection_done:
                # Detection can take up to 20 s per device; never block the
                # GUI.  The caller will show "detecting" and the user retries.
                threading.Thread(
                    target=self._detect_qsv_devices, daemon=True
                ).start()
                self._last_error = "detecting_gpu"
                return False
            self._qsv_device = resolve_qsv_device(
                self.settings.qsv_device, self.qsv_devices
            )
        # Hardware probing happens per job in the worker thread
        # (``_encoder_for_job``).  Probing here blocked the GUI for up to 20 s
        # on slow drivers; the first job now reports "analyzing" instead.
        if not self._encoder:
            self._last_error = "no_encoder"
            return False
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
        return True

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
        self.itemsChanged.emit()

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
        elif item["id"] in self._threads:
            self._threads[item["id"]][1].cancel()
        try:
            current = self.items.index(item)
        except ValueError:
            return
        self.model.remove_rows([current])
        self._emit_stats()
        self.itemsChanged.emit()

    @Slot(int, result=bool)
    def retryItem(self, row: int) -> bool:
        """Requeue an errored/skipped/cancelled item after its thread died.

        Refusing while the old thread is still alive prevents the scheduler
        entry from being overwritten (the old ``finished`` handler would pop
        the new job).
        """
        if not (0 <= row < len(self.items)):
            return False
        item = self.items[row]
        if item["status"] not in (CompressStatus.ERROR, CompressStatus.SKIPPED,
                                  CompressStatus.CANCELLED):
            return False
        if item["id"] in self._threads:
            return False
        item["error"] = ""
        item["output"] = ""
        item["backup"] = ""
        item["sha256"] = ""
        item["validation"] = ""
        item["progress"] = 0.0
        item["speed"] = "—"
        item["saving"] = 0.0
        item["size_after"] = 0
        self._set_status(item, CompressStatus.WAITING)
        self.itemsChanged.emit()
        if self._active and not self._paused:
            self._pump()
        return True

    @Slot()
    def clearFinished(self) -> None:
        rows = [
            i for i, it in enumerate(self.items)
            if it["status"] in FINAL and it["id"] not in self._threads
        ]
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()
            self.itemsChanged.emit()

    def shutdown(self, timeout: float = 6.0) -> None:
        """Cancela tudo e aguarda as threads (mesma proteção de queue.py)."""
        self._threads.shutdown(
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
            if encoder.endswith("_qsv"):
                # Re-resolve the device for this job: changing the codec/vendor
                # while the queue is active must not reuse a stale index.
                self._qsv_device = resolve_qsv_device(
                    settings.qsv_device, self.qsv_devices
                )
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
        if item["id"] in self._threads:
            # A retry/relaunch must wait for the previous QThread to finish;
            # otherwise the old ``finished`` handler removes the new entry.
            return
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
            job_id=item["id"],
            journals_dir=config.journals_dir(),
            catalog_path=self.catalog_path,
        )
        worker.moveToThread(thread)
        # Slots do manager (thread da GUI): evita mutar modelo/QML a partir
        # da thread do encoder. Ver comentário equivalente em queue.py.
        worker._queue_item = item
        worker.statusChanged.connect(self._worker_status)
        worker.progressChanged.connect(self._worker_progress)
        worker.completed.connect(self._worker_completed)
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
        # Compatibility path only; the manager uses ``completed``.
        item = self._sender_item()
        if item is not None:
            self._on_success(item, tmp, final, before, after)

    @Slot(str, str, int, int, str, str)
    def _worker_completed(self, final: str, backup: str, before: int,
                          after: int, sha256: str, validation: str) -> None:
        item = self._sender_item()
        if item is not None:
            self._on_completed(item, final, backup, before, after, sha256, validation)

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
        """Compatibility with old workers that emitted ``succeeded``.

        New workers install transactionally and emit ``completed``.  If
        ``tmp == final`` the install already happened; just update the row.
        """
        if os.path.abspath(tmp) == os.path.abspath(final):
            self._on_completed(item, final, "", before, after, "", "ok")
            return
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
        self._on_completed(item, final, "", before, after, "", "ok")

    def _on_completed(self, item: dict, final: str, backup: str, before: int,
                      after: int, sha256: str, validation: str) -> None:
        item["output"] = final
        item["backup"] = backup
        item["sha256"] = sha256
        item["validation"] = validation
        item["size_before"] = before
        item["size_after"] = after
        item["saving"] = round(100.0 * (1 - after / before), 1) if before else 0.0
        item["speed"] = "—"
        item["progress"] = 100.0
        self._set_status(item, CompressStatus.DONE)
        self.itemsChanged.emit()

    def _on_skipped(self, item: dict, reason: str) -> None:
        item["error"] = reason
        self._set_status(item, CompressStatus.SKIPPED)
        self.itemsChanged.emit()

    def _on_failed(self, item: dict, error: str) -> None:
        item["error"] = error
        self._set_status(item, CompressStatus.ERROR)
        self.itemsChanged.emit()

    def _on_cancelled(self, item: dict) -> None:
        self._set_status(item, CompressStatus.CANCELLED)
        self.itemsChanged.emit()

    def _on_thread_done(self, item: dict) -> None:
        self._threads.pop(item["id"], None)  # registry cleans worker/thread
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
