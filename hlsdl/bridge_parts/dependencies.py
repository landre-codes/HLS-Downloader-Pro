# ruff: noqa: F401, F403, F405

from __future__ import annotations

from PySide6.QtCore import Property, Slot

from .signals import *


class DependenciesMixin(BridgeSignals):

    def _ytdlp_available(self) -> bool:
        return any(d["key"] == "ytdlp" and d["found"] for d in self._deps_list)

    def _ffmpeg_available(self) -> bool:
        return any(d["key"] == "ffmpeg" and d["found"] for d in self._deps_list)

    @Property(bool, notify=depsChanged)
    def ytdlpAvailable(self) -> bool:
        return self._ytdlp_available()

    @Property(bool, notify=depsChanged)
    def ffmpegAvailable(self) -> bool:
        return self._ffmpeg_available()

    @Property(bool, notify=depsChanged)
    def anyEssentialMissing(self) -> bool:
        if not self._deps_list:
            return False
        return any(d["required"] and not d["found"] for d in self._deps_list)

    @Property(list, notify=depsChanged)
    def dependencies(self) -> list:
        return self._deps_list

    @Property(bool, notify=depsChanged)
    def depsBusy(self) -> bool:
        return self._deps_busy

    @Property(bool, notify=depsChanged)
    def depsPromptDismissed(self) -> bool:
        return self._deps_prompt_dismissed

    @Slot()
    def dismissDepsPrompt(self) -> None:
        """NÃ£o volta a perguntar sobre dependÃªncias nesta mÃ¡quina."""
        if not self._deps_prompt_dismissed:
            self._deps_prompt_dismissed = True
            self._save("deps/prompt_dismissed", True)
            self.depsChanged.emit()

    def _on_deps_checked(self, items: list) -> None:
        self._deps_list = items
        self.depsChanged.emit()

    def _on_deps_started(self, key: str) -> None:
        self._deps_busy = True
        self.depsChanged.emit()

    def _on_deps_finished(self, key: str, ok: bool, name: str) -> None:
        self._deps_busy = False
        if ok:
            self.notifyText.emit(self._tr("dep_updated", name=name))
        else:
            self.notifyText.emit(self._tr("dep_install_failed", name=name))
        self.depsInstallFinished.emit(key, ok, name)
        if ok and key == "ffmpeg":
            # A lista de encoders foi detectada antes da instalaÃ§Ã£o; o
            # refresh roda fora da thread da GUI porque sonda ffmpeg/GPU.
            self.refreshCompressionEncoders()
        self.depsChanged.emit()

    @Slot()
    def refreshDependencies(self) -> None:
        self.deps.check_all()

    @Slot()
    def installMissingDependencies(self) -> None:
        if self._jobs_active():
            self.notifyText.emit(self._tr("dep_job_active"))
            return
        self.deps.install_missing_required()

    @Slot(str)
    def installDependency(self, key: str) -> None:
        if self._jobs_active():
            self.notifyText.emit(self._tr("dep_job_active"))
            return
        if not self.deps.install(key):
            if not self._deps_busy:
                self.notifyText.emit(self._tr("dep_not_applicable", name=key))

    @Slot()
    def updateDependencies(self) -> None:
        if self._jobs_active():
            self.notifyText.emit(self._tr("dep_job_active"))
            return
        self.deps.update_all()

    def set_dependencies(self, items: list[dict]) -> None:
        """Permite injetar o estado (usado em testes)."""
        self._on_deps_checked(items)


