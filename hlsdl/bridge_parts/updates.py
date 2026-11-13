# ruff: noqa: F401, F403, F405

from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import Property, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from ..config import is_portable
from ..services.procutils import spawn_kwargs
from .signals import *


class UpdatesMixin(BridgeSignals):

    @Property(bool, notify=updateChanged)
    def updateAvailable(self) -> bool:
        return bool(self._update_info.get("available"))

    @Property(str, notify=updateChanged)
    def updateLatest(self) -> str:
        return str(self._update_info.get("latest", ""))

    @Property(str, notify=updateChanged)
    def updateStatus(self) -> str:
        return self._update_status

    @Property(bool, notify=updateChanged)
    def updateBusy(self) -> bool:
        return self._update_busy

    @Property(int, notify=updateProgressChanged)
    def updateProgress(self) -> int:
        return self._update_progress

    @Property(str, notify=updateChanged)
    def updateNotes(self) -> str:
        return str(self._update_info.get("notes", ""))

    @Property(str, notify=updateChanged)
    def updateHtmlUrl(self) -> str:
        return str(self._update_info.get("html_url", ""))

    @Slot()
    def checkForUpdates(self) -> None:
        if self._update_busy:
            return
        self._update_busy = True
        self._update_progress = 0
        self._update_status = self._tr("update_checking")
        self.updateChanged.emit()
        self.updater.check()

    @Slot()
    def downloadUpdate(self) -> None:
        if not self._update_info.get("available"):
            return
        if os.name != "nt" or is_portable():
            self.openReleasePage()
            return
        if not self._update_info.get("installer_url") or not self._update_info.get("checksums_url"):
            self.notifyText.emit(self._tr("update_no_assets"))
            return
        self._update_busy = True
        self._update_progress = 0
        self._update_status = self._tr("update_checking")
        self.updateChanged.emit()
        self.updater.download_and_verify(self._update_info)

    @Slot()
    def openReleasePage(self) -> None:
        url = str(self._update_info.get("html_url") or "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _on_update_checking(self, busy: bool) -> None:
        self._update_busy = busy
        self.updateChanged.emit()

    def _on_update_checked(self, info: dict) -> None:
        self._update_info = info
        self._update_busy = False
        if info.get("available"):
            self._update_status = self._tr(
                "update_available", version=info.get("latest", "")
            )
        else:
            self._update_status = self._tr("update_latest")
        self.updateChanged.emit()

    def _on_update_progress(self, pct: int) -> None:
        self._update_progress = int(pct)
        self.updateProgressChanged.emit(self._update_progress)

    def _on_update_failed(self, err: str) -> None:
        self._update_busy = False
        if err in ("missing_assets", "missing_checksum", "checksum_mismatch"):
            message = (
                self._tr("update_no_assets") if err == "missing_assets"
                else self._tr("update_download_failed", err=err)
            )
        else:
            message = self._tr("update_failed", err=err)
        self._update_status = message
        self.notifyText.emit(message)
        self.updateChanged.emit()

    def _on_update_ready(self, path: str) -> None:
        self._update_busy = False
        self._update_status = self._tr("update_ready")
        self.updateChanged.emit()
        self.notifyText.emit(self._update_status)
        if os.name == "nt" and not is_portable():
            try:
                subprocess.Popen(
                    [path, "/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"],
                    **spawn_kwargs(),
                )
            except Exception as exc:
                self._update_status = self._tr("update_failed", err=exc)
                self.updateChanged.emit()
                return
            QApplication.quit()
        else:
            self.openReleasePage()


