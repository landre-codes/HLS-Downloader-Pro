"""Compressão local de vídeos para HEVC (Intel QSV / NVENC / AMF / x265).

Fila própria (independente dos downloads), com paralelismo, progresso por
arquivo, validação de saída e substituição atômica. Usa as mesmas proteções de
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
import time
from dataclasses import dataclass
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
from .services.procutils import (
    popen_kwargs,
    spawn_kwargs,
    terminate_tree,
    which,
)

log = logging.getLogger("hlsdl")

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts"}
SAFE_AUDIO = {"aac", "ac3", "eac3", "mp3", "alac"}
TEXT_SUBS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text"}
IMAGE_SUBS = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvb_subtitle", "xsub"}
ENCODER_ORDER = ("qsv", "nvenc", "amf", "x265")
# Preferência do "Auto": GPUs dedicadas (NVIDIA/AMD) antes do QSV (que pode
# estar na iGPU). Em máquinas só Intel, o QSV usa o dispositivo dedicado (Arc).
AUTO_ORDER = ("nvenc", "amf", "qsv", "x265")
ENCODER_NAMES = {
    "qsv": "Intel QSV (HEVC)",
    "nvenc": "NVIDIA NVENC (HEVC)",
    "amf": "AMD AMF (HEVC)",
    "x265": "Software x265",
}
SPEEDS = ("fast", "balanced", "slow")


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
    encoder: str = "auto"
    quality: int = 24
    speed: str = "balanced"
    parallel: int = 1
    min_size_mb: int = 0
    only_if_smaller: bool = True
    replace_original: bool = False
    reencode_hevc: bool = False
    skip_hdr: bool = True
    qsv_device: int = -1  # -1 = automático (prefere a GPU dedicada)


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
# Detecção / argumentos
# ---------------------------------------------------------------------------
def detect_encoders() -> dict[str, bool]:
    """Detecta encoders HEVC disponíveis no ffmpeg instalado."""
    result = {key: False for key in ENCODER_ORDER}
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return result
    try:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        text = out.stdout or ""
    except Exception:
        return result
    result["qsv"] = "hevc_qsv" in text
    result["nvenc"] = "hevc_nvenc" in text
    result["amf"] = "hevc_amf" in text
    result["x265"] = "libx265" in text
    return result


def resolve_encoder(settings: CompressionSettings,
                    available: dict[str, bool]) -> str:
    if settings.encoder in ENCODER_ORDER and available.get(settings.encoder):
        return settings.encoder
    for key in AUTO_ORDER:
        if available.get(key):
            return key
    return "x265"


def is_integrated_gpu(name: str) -> bool:
    """Heurística: Intel UHD/HD/Iris = integrada; Arc/NVIDIA/AMD = dedicada."""
    value = (name or "").lower()
    if "arc" in value:
        return False
    if any(token in value for token in ("uhd", "hd graphics", "iris", "integrated")):
        return True
    if any(token in value for token in ("nvidia", "geforce", "rtx", "quadro",
                                        "radeon", "rx ")):
        return False
    return False


def detect_gpus() -> list[dict]:
    """Lista as GPUs do sistema (melhor esforço, sem dependências)."""
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
    return [
        {"index": i, "name": name, "integrated": is_integrated_gpu(name)}
        for i, name in enumerate(names)
    ]


def detect_qsv_devices(max_devices: int = 4) -> list[dict]:
    """Mapeia índices ``-qsv_device`` para o nome real da GPU.

    O ffmpeg imprime ``Using device 8086:e20b (Intel(R) Arc(TM) B580)`` em
    loglevel verbose; isso permite escolher a GPU dedicada.
    """
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
    """Escolhe o índice QSV (prefere GPU dedicada/Arc quando automático)."""
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


def video_args(encoder: str, quality: int, speed: str) -> list[str]:
    q = max(1, min(51, int(quality)))
    speed = speed if speed in SPEEDS else "balanced"
    if encoder == "qsv":
        preset = {"fast": "fast", "balanced": "medium", "slow": "slow"}[speed]
        return ["-c:v", "hevc_qsv", "-preset", preset,
                "-global_quality", str(q), "-tag:v", "hvc1"]
    if encoder == "nvenc":
        preset = {"fast": "p3", "balanced": "p5", "slow": "p7"}[speed]
        return ["-c:v", "hevc_nvenc", "-gpu", "0", "-preset", preset, "-tune", "hq",
                "-rc", "vbr", "-cq", str(q), "-b:v", "0", "-tag:v", "hvc1"]
    if encoder == "amf":
        preset = {"fast": "speed", "balanced": "balanced", "slow": "quality"}[speed]
        return ["-c:v", "hevc_amf", "-quality", preset, "-rc", "cqp",
                "-qp_i", str(q), "-qp_p", str(q), "-tag:v", "hvc1"]
    preset = {"fast": "fast", "balanced": "medium", "slow": "slow"}[speed]
    return ["-c:v", "libx265", "-preset", preset, "-crf", str(q),
            "-tag:v", "hvc1", "-x265-params", "log-level=error"]


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
    if (video.get("codec_name") or "").lower() == "hevc" and not settings.reencode_hevc:
        return "already_hevc"
    transfer = (video.get("color_transfer") or "").lower()
    if settings.skip_hdr and transfer in ("smpte2084", "arib-std-b67"):
        return "hdr"
    return ""


def output_path(src: str) -> str:
    base, _ = os.path.splitext(src)
    candidate = f"{base}_hevc.mp4"
    n = 2
    while os.path.exists(candidate):
        candidate = f"{base}_hevc-{n}.mp4"
        n += 1
    return candidate


def build_args(src: str, tmp: str, settings: CompressionSettings,
               encoder: str, probe: dict, qsv_device: int = 0) -> list[str]:
    _videos, audios, subs, _duration = analyze(probe)
    ffmpeg = which("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y"]
    if encoder == "qsv":
        cmd += ["-qsv_device", str(qsv_device)]
    cmd += ["-progress", "pipe:1", "-nostats", "-i", src,
            "-map", "0:V:0", "-map", "0:a?"]

    for i, audio in enumerate(audios):
        codec = (audio.get("codec_name") or "").lower()
        if codec in SAFE_AUDIO:
            cmd += [f"-c:a:{i}", "copy"]
        else:
            cmd += [f"-c:a:{i}", "aac", f"-b:a:{i}", "192k"]

    text_subs = [
        i for i, sub in enumerate(subs)
        if (sub.get("codec_name") or "").lower() in TEXT_SUBS
    ]
    if text_subs:
        for i in text_subs:
            cmd += ["-map", f"0:s:{i}"]
        cmd += ["-c:s", "mov_text"]
    else:
        cmd += ["-sn"]

    cmd += video_args(encoder, settings.quality, settings.speed)
    cmd += ["-map_chapters", "0", "-map_metadata", "0",
            "-movflags", "+faststart", "-max_muxing_queue_size", "4096", tmp]
    return cmd


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
            probe = probe_media(self.src)
            if not probe:
                self.failed.emit(self._t("compress_probe_failed"))
                return
            reason = skip_reason(self.settings, probe)
            if reason:
                self.skipped.emit(self._t("compress_skip_" + reason))
                return
            _videos, _audios, _subs, duration = analyze(probe)
            final = output_path(self.src)
            tmp = final + ".part.mp4"
            cmd = build_args(self.src, tmp, self.settings, self.encoder, probe,
                             self.qsv_device)
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
            stderr_lines: list[str] = []

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
            rc = self._proc.wait()
            drainer.join(timeout=2)
            self._proc = None

            if self._cancel:
                self._safe_remove(tmp)
                self.cancelled.emit()
                return
            if rc != 0:
                message = stderr_lines[-1] if stderr_lines else f"ffmpeg rc={rc}"
                self._safe_remove(tmp)
                self.failed.emit(message)
                return
            out_probe = probe_media(tmp)
            videos, _a, _s, _d = analyze(out_probe or {})
            if not os.path.exists(tmp) or not videos or os.path.getsize(tmp) == 0:
                self._safe_remove(tmp)
                self.failed.emit(self._t("compress_invalid_output"))
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

    def __init__(self, model: CompressionModel, parent: QObject | None = None):
        super().__init__(parent)
        self.model = model
        self.items: list[dict] = model.items()
        self.settings = CompressionSettings()
        self.available = detect_encoders()
        self.qsv_devices: list[dict] = []
        self._qsv_device = 0
        self._active = False
        self._paused = False
        self._running = 0
        self._threads: dict[int, tuple[QThread, CompressionWorker, dict]] = {}
        self._counter = 0
        self._encoder = "x265"
        self._t = translator("pt")
        self._emit_stats()

    def _detect_qsv_devices(self) -> None:
        devices = detect_qsv_devices()
        if devices:
            self.qsv_devices = devices
            self.qsvDevicesChanged.emit()

    def set_translator(self, fn) -> None:
        self._t = fn

    # ------------------------------------------------------------- settings
    def apply_settings(self, settings: CompressionSettings) -> None:
        settings.quality = max(1, min(51, int(settings.quality)))
        settings.parallel = max(1, min(8, int(settings.parallel)))
        settings.speed = settings.speed if settings.speed in SPEEDS else "balanced"
        self.settings = settings

    def refresh_encoders(self) -> dict[str, bool]:
        self.available = detect_encoders()
        if self.available.get("qsv"):
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
            self._emit_stats()
        return added

    # -------------------------------------------------------------- control
    @Slot()
    def start(self) -> None:
        self._encoder = resolve_encoder(self.settings, self.available)
        if self._encoder == "qsv":
            if not self.qsv_devices:
                self.qsv_devices = detect_qsv_devices()
                if self.qsv_devices:
                    self.qsvDevicesChanged.emit()
            self._qsv_device = resolve_qsv_device(
                self.settings.qsv_device, self.qsv_devices
            )
        log.info("compressão: encoder=%s qsv_device=%s", self._encoder, self._qsv_device)
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

    def shutdown(self, timeout: float = 8.0) -> None:
        self.cancelAll()
        deadline = time.time() + timeout
        for thread, _worker, _item in list(self._threads.values()):
            remaining = max(0.0, deadline - time.time())
            try:
                thread.quit()
                thread.wait(int(remaining * 1000))
            except RuntimeError:
                pass
        self._threads.clear()
        self._running = 0

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

    def _launch(self, item: dict) -> None:
        item["status"] = CompressStatus.ANALYZING
        item["encoder"] = self._encoder
        self._touch(item)
        thread = QThread(self)
        worker = CompressionWorker(
            item["input"], self.settings, self._encoder, self._t,
            qsv_device=self._qsv_device,
        )
        worker.moveToThread(thread)
        worker.statusChanged.connect(lambda st, it=item: self._on_status(it, st))
        worker.progressChanged.connect(lambda pct, sp, it=item: self._on_progress(it, pct, sp))
        worker.succeeded.connect(
            lambda tmp, final, before, after, it=item:
            self._on_success(it, tmp, final, before, after)
        )
        worker.skipped.connect(lambda reason, it=item: self._on_skipped(it, reason))
        worker.failed.connect(lambda err, it=item: self._on_failed(it, err))
        worker.cancelled.connect(lambda it=item: self._on_cancelled(it))
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda it=item: self._on_thread_done(it))
        self._threads[item["id"]] = (thread, worker, item)
        self._running += 1
        self._emit_stats()
        thread.start()

    # ------------------------------------------------------------ callbacks
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
        if self.settings.only_if_smaller and after >= before:
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
        if self.settings.replace_original and os.path.abspath(final) != os.path.abspath(item["input"]):
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

    def _emit_state(self) -> None:
        self.stateChanged.emit(self._active, self._paused)
