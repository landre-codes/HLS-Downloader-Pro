# ruff: noqa: F401, F403, F405

from __future__ import annotations

from PySide6.QtCore import Property, Slot
from PySide6.QtWidgets import QFileDialog

from .signals import *


class SimilarityMixin(BridgeSignals):

    @Property(bool, notify=similarityChanged)
    def similarityBusy(self) -> bool:
        return self._similar_busy

    @Property(list, notify=similarityChanged)
    def similarityGroups(self) -> list:
        return self._similar_groups

    @Property(int, notify=similarityChanged)
    def similarityProgress(self) -> int:
        return self._similar_progress

    @Property(int, notify=similarityChanged)
    def similarityTotal(self) -> int:
        return self._similar_total

    @Property(str, notify=similarityChanged)
    def similarityStatus(self) -> str:
        return self._similar_status

    @Property(int, notify=similarityChanged)
    def similarityThreshold(self) -> int:
        return self._similar_threshold

    @Slot(int)
    def setSimilarityThreshold(self, value: int) -> None:
        self._similar_threshold = self._clamp(int(value), 50, 100)
        self.similarityChanged.emit()

    @Property(list, notify=recoveryChanged)
    def recoveryMessages(self) -> list:
        return self._recovery_messages

    @Slot()
    def clearRecoveryMessages(self) -> None:
        self._recovery_messages = []
        self.recoveryChanged.emit()

    @Slot()
    def scanSimilarQueue(self) -> None:
        paths = [item.get("input", "") for item in self.compression.items]
        if not paths:
            self.notifyText.emit(self._tr("similar_no_files"))
            return
        self._start_similarity(paths)

    @Slot()
    def scanSimilarFolder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            None, self._tr("similar_choose_folder"), self._output_folder
        )
        if not folder:
            return
        self._similar_status = self._tr("similar_scanning")
        self.notifyText.emit(self._tr("similar_scanning"))
        self.similarity.scan_folder(
            folder, recursive=True, threshold=self._similar_threshold
        )

    @Slot(list)
    def scanSimilarPaths(self, paths: list) -> None:
        self._start_similarity([str(path) for path in paths])

    def _start_similarity(self, paths: list) -> None:
        if self._similar_busy or self.similarity.busy:
            self.notifyText.emit(self._tr("similar_busy"))
            return
        self._similar_groups = []
        self._similar_progress = 0
        self._similar_total = len(paths)
        self._similar_status = self._tr("similar_scanning")
        self.similarityChanged.emit()
        self.similarity.scan_paths(paths, threshold=self._similar_threshold)

    @Slot()
    def cancelSimilarityScan(self) -> None:
        self.similarity.cancel()

    @Slot()
    def clearSimilarityResults(self) -> None:
        self._similar_groups = []
        self._similar_progress = 0
        self._similar_total = 0
        self._similar_status = ""
        self.similarityChanged.emit()

    def _on_similar_state(self, busy: bool) -> None:
        self._similar_busy = busy
        if busy:
            self._similar_status = self._tr("similar_scanning")
        self.similarityChanged.emit()

    def _on_similar_progress(self, current: int, total: int, path: str) -> None:
        self._similar_progress = current
        self._similar_total = total
        if path:
            self._similar_status = self._tr("similar_progress", current=current, total=total)
        self.similarityChanged.emit()

    def _on_similar_finished(self, groups: list) -> None:
        self._similar_groups = groups or []
        self._similar_busy = False
        self._similar_status = (
            self._tr("similar_found", n=len(self._similar_groups))
            if self._similar_groups else self._tr("similar_none")
        )
        self.similarityChanged.emit()
        self.notifyText.emit(self._similar_status)

    def _on_similar_failed(self, message: str) -> None:
        self._similar_busy = False
        if message == "cancelled":
            self._similar_status = self._tr("similar_cancelled")
        elif message == "no_files":
            self._similar_status = self._tr("similar_no_files")
        else:
            self._similar_status = self._tr("similar_failed", err=message)
        self.similarityChanged.emit()
        self.notifyText.emit(self._similar_status)


