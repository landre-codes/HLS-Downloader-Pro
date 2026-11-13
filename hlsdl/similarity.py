"""Similarity search for local media (VDF/Czkawka-inspired).

The scanner uses a layered strategy, from strongest to weakest:

1. **exact** — size + sampled content hash (and full hash when needed);
2. **perceptual** — multi-frame dHash + aHash + audio RMS envelope + duration;
3. **audio** — RMS envelope + duration (audio-only or broken video);
4. **metadata** — duration + resolution + filename similarity.

The advanced path is the multi-frame perceptual signature.  Every layer is a
fallback for the previous one, so a missing ffmpeg, an unreadable video or a
corrupt frame does not abort the whole scan.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Iterable

from PySide6.QtCore import QObject, Signal

from .media import MediaSignature, build_signature, group_similar

log = logging.getLogger("hlsdl")

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts",
              ".mp3", ".m4a", ".flac", ".wav", ".opus", ".ogg"}


class SimilarityScanner(QObject):
    """Runs a similarity scan off the GUI thread and reports groups."""

    progress = Signal(int, int, str)
    finished = Signal(list)
    failed = Signal(str)
    stateChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._busy = False
        self._cancel = False
        self._thread: threading.Thread | None = None
        self._signatures: list[MediaSignature] = []
        self._groups: list[dict] = []

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def groups(self) -> list[dict]:
        return self._groups

    @staticmethod
    def _generated(path: str) -> bool:
        lower = os.path.basename(path).lower()
        return (
            ".hlsdl-backup-" in lower
            or ".part." in lower
            or lower.endswith(".invalid")
        )

    def scan_paths(self, paths: Iterable[str], threshold: float = 85.0,
                   frames: int = 5, with_audio: bool = True) -> bool:
        if self._busy:
            return False
        cleaned = []
        for path in paths:
            try:
                value = os.path.abspath(os.path.expanduser(str(path)))
            except (TypeError, ValueError):
                continue
            if (os.path.isfile(value)
                    and os.path.splitext(value)[1].lower() in VIDEO_EXTS
                    and not self._generated(value)):
                cleaned.append(value)
        cleaned = sorted(dict.fromkeys(cleaned))
        if not cleaned:
            self.failed.emit("no_files")
            return False
        self._busy = True
        self._cancel = False
        self._signatures = []
        self._groups = []
        self.stateChanged.emit(True)
        self._thread = threading.Thread(
            target=self._run,
            args=(cleaned, max(50.0, min(100.0, float(threshold))), int(frames), bool(with_audio)),
            daemon=True,
        )
        self._thread.start()
        return True

    def scan_folder(self, folder: str, recursive: bool = True,
                    threshold: float = 85.0) -> bool:
        folder = os.path.abspath(os.path.expanduser(folder or ""))
        if not os.path.isdir(folder):
            self.failed.emit("invalid_folder")
            return False
        paths: list[str] = []
        try:
            if recursive:
                for root, _dirs, names in os.walk(folder):
                    for name in names:
                        if os.path.splitext(name)[1].lower() in VIDEO_EXTS:
                            paths.append(os.path.join(root, name))
            else:
                for name in os.listdir(folder):
                    candidate = os.path.join(folder, name)
                    if (os.path.isfile(candidate)
                            and os.path.splitext(name)[1].lower() in VIDEO_EXTS):
                        paths.append(candidate)
        except OSError as exc:
            self.failed.emit(f"folder_read_error:{exc}")
            return False
        return self.scan_paths(paths, threshold=threshold)

    def cancel(self) -> None:
        self._cancel = True

    def _run(self, paths: list[str], threshold: float, frames: int,
             with_audio: bool) -> None:
        try:
            total = len(paths)
            for index, path in enumerate(paths, start=1):
                if self._cancel:
                    self.failed.emit("cancelled")
                    return
                self.progress.emit(index, total, path)
                signature = build_signature(path, with_frames=frames > 0,
                                            with_audio=with_audio)
                if frames > 1 and signature.frame_dhashes:
                    # ``build_signature`` already samples 5 points; keep the
                    # requested count by trimming deterministically.
                    signature.frame_dhashes = signature.frame_dhashes[:frames]
                    signature.frame_ahashes = signature.frame_ahashes[:frames]
                self._signatures.append(signature)
            if self._cancel:
                self.failed.emit("cancelled")
                return
            groups = group_similar(self._signatures, threshold=threshold)
            self._groups = groups
            self.progress.emit(total, total, "")
            self.finished.emit(groups)
        except Exception as exc:
            log.exception("falha na busca de similares")
            self.failed.emit(str(exc))
        finally:
            self._busy = False
            self.stateChanged.emit(False)
