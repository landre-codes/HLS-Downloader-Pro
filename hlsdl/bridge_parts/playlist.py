# ruff: noqa: F401, F403, F405

from __future__ import annotations

from PySide6.QtCore import Property, Slot

from .signals import *


class PlaylistMixin(BridgeSignals):

    @Property(list, notify=playlistChanged)
    def playlistItems(self) -> list:
        return self._playlist_items

    @Property(bool, notify=playlistLoadingChanged)
    def playlistLoading(self) -> bool:
        return self._playlist_loading

    @Slot(str, int)
    def loadPlaylist(self, url: str, limit: int) -> None:
        self._playlist.load(url, int(limit), self._build_cookies_arg())

    @Slot()
    def cancelPlaylist(self) -> None:
        if self._playlist_loading:
            self._playlist.cancel()
            self.notifyText.emit(self._tr("playlist_cancelled"))

    @Slot()
    def clearPlaylist(self) -> None:
        self._playlist_items = []
        self.playlistChanged.emit()

    def _on_playlist_loading(self, loading: bool) -> None:
        self._playlist_loading = loading
        self.playlistLoadingChanged.emit(loading)

    def _on_playlist_loaded(self, items: list) -> None:
        self._playlist_items = items
        self.playlistChanged.emit()

    def _on_playlist_failed(self, message: str) -> None:
        self.notifyText.emit(message)


