# ruff: noqa: F401, F403, F405

from __future__ import annotations

import os

from PySide6.QtCore import Property, Slot
from PySide6.QtWidgets import QFileDialog

from ..config import BROWSERS, is_portable
from ..deps import YTDLP_VARIANTS
from ..formats import (
    AUDIO_CONTAINERS,
    CODECS,
    COMPRESS_LEVELS,
    DEFAULT_AUDIO_CONTAINER,
    DEFAULT_VIDEO_CONTAINER,
    FORMAT_MODES,
    NAMING_MODES,
    QUALITIES,
    VIDEO_CONTAINERS,
)
from ..i18n import LANGUAGE_NAMES, LANGUAGES
from ..integrity import cleanup_sidecars, set_sidecars_enabled
from .signals import *


class SettingsMixin(BridgeSignals):

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._lang

    @Slot(str)
    def setLanguage(self, lang: str) -> None:
        lang = lang if lang in LANGUAGES else "pt"
        if lang == self._lang:
            return
        self._lang = lang
        self._save("i18n/language", lang)
        self.manager.set_translator(self._translator())
        self.single_manager.set_translator(self._translator())
        self._playlist.set_translator(self._translator())
        self.compression.set_translator(self._translator())
        self.languageChanged.emit(lang)

    @Property(list, constant=True)
    def languages(self) -> list:
        """Idiomas disponíveis para o seletor (código + nome)."""
        return [{"code": code, "name": LANGUAGE_NAMES[code]} for code in LANGUAGES]

    @Property(str, notify=outputFolderChanged)
    def outputFolder(self) -> str:
        return self._output_folder

    @Property(bool, notify=darkChanged)
    def dark(self) -> bool:
        return self._dark

    @Property(bool, notify=sidecarsChanged)
    def sidecarsEnabled(self) -> bool:
        return self._sidecars_enabled

    @Slot(bool)
    def setSidecarsEnabled(self, value: bool) -> None:
        value = bool(value)
        if value == self._sidecars_enabled:
            return
        self._sidecars_enabled = value
        set_sidecars_enabled(value)
        self._save("integrity/sidecars", value)
        self.sidecarsChanged.emit(value)

    @Slot()
    def cleanupSidecars(self) -> None:
        removed = cleanup_sidecars(self._output_folder)
        self.notifyText.emit(self._tr("sidecars_cleaned", n=removed))

    @Property(int, notify=concurrencyChanged)
    def concurrency(self) -> int:
        return self._concurrency

    @Property(int, notify=limitRateChanged)
    def limitRateMB(self) -> int:
        return self._limit_rate_mb

    @Property(int, notify=fragmentsChanged)
    def fragments(self) -> int:
        return self._fragments

    @Property(bool, notify=cookiesEnabledChanged)
    def cookiesEnabled(self) -> bool:
        return self._cookies_enabled

    @Property(int, notify=cookiesBrowserIndexChanged)
    def cookiesBrowserIndex(self) -> int:
        return self._cookies_browser_index

    @Property(str, notify=cookiesFileChanged)
    def cookiesFile(self) -> str:
        return self._cookies_file

    @Property(str, notify=formatModeChanged)
    def formatMode(self) -> str:
        return self._format_mode

    @Slot(str)
    def setFormatMode(self, mode: str) -> None:
        mode = mode if mode in FORMAT_MODES else "video_audio"
        if mode == self._format_mode:
            return
        self._format_mode = mode
        self.manager.setFormatMode(mode)
        self.single_manager.setFormatMode(mode)
        self._save("download/format_mode", mode)
        # Ajusta o contêiner se ele não fizer sentido no novo modo.
        valid = AUDIO_CONTAINERS if mode == "audio_only" else VIDEO_CONTAINERS
        if self._container not in valid:
            self.setContainer(
                DEFAULT_AUDIO_CONTAINER if mode == "audio_only" else DEFAULT_VIDEO_CONTAINER
            )
        self.formatModeChanged.emit(mode)

    @Property(str, notify=qualityChanged)
    def quality(self) -> str:
        return self._quality

    @Slot(str)
    def setQuality(self, quality: str) -> None:
        quality = quality if quality in QUALITIES else "best"
        if quality == self._quality:
            return
        self._quality = quality
        self.manager.setQuality(quality)
        self.single_manager.setQuality(quality)
        self._save("download/quality", quality)
        self.qualityChanged.emit(quality)

    @Property(str, notify=containerChanged)
    def container(self) -> str:
        return self._container

    @Slot(str)
    def setContainer(self, container: str) -> None:
        valid = AUDIO_CONTAINERS if self._format_mode == "audio_only" else VIDEO_CONTAINERS
        container = container if container in valid else valid[0]
        if container == self._container:
            return
        self._container = container
        self.manager.setContainer(container)
        self.single_manager.setContainer(container)
        self._save("download/container", container)
        self.containerChanged.emit(container)

    @Property(str, notify=codecChanged)
    def codec(self) -> str:
        return self._codec

    @Slot(str)
    def setCodec(self, codec: str) -> None:
        codec = codec if codec in CODECS else "copy"
        if codec == self._codec:
            return
        self._codec = codec
        self.manager.setCodec(codec)
        self.single_manager.setCodec(codec)
        self._save("encode/codec", codec)
        self.codecChanged.emit(codec)

    @Property(str, notify=compressLevelChanged)
    def compressLevel(self) -> str:
        return self._compress_level

    @Slot(str)
    def setCompressLevel(self, level: str) -> None:
        level = level if level in COMPRESS_LEVELS else "medium"
        if level == self._compress_level:
            return
        self._compress_level = level
        self.manager.setCompressLevel(level)
        self.single_manager.setCompressLevel(level)
        self._save("encode/level", level)
        self.compressLevelChanged.emit(level)

    @Property(str, notify=namingModeChanged)
    def namingMode(self) -> str:
        return self._naming_mode

    @Slot(str)
    def setNamingMode(self, mode: str) -> None:
        mode = mode if mode in NAMING_MODES else "id"
        if mode == self._naming_mode:
            return
        self._naming_mode = mode
        self.manager.setNamingMode(mode)
        self.single_manager.setNamingMode(mode)
        self._save("naming/mode", mode)
        self.namingModeChanged.emit(mode)

    @Property(str, notify=ytdlpVariantChanged)
    def ytdlpVariant(self) -> str:
        return self._ytdlp_variant

    @Slot(str)
    def setYtdlpVariant(self, variant: str) -> None:
        variant = variant if variant in YTDLP_VARIANTS else "stable"
        if variant == self._ytdlp_variant:
            return
        self._ytdlp_variant = variant
        self._save("deps/ytdlp_variant", variant)
        set_variant = getattr(self.deps, "set_variant", None)
        if callable(set_variant):
            set_variant(variant)
        self.ytdlpVariantChanged.emit(variant)

    @Slot()
    def chooseOutputFolder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            None, self._tr("dlg_outdir"), self._output_folder
        )
        if path:
            path = os.path.abspath(os.path.expanduser(path))
            if not os.path.isdir(path) or not os.access(path, os.W_OK):
                self.notifyText.emit(self._tr("output_folder_readonly"))
                return
            self._output_folder = path
            self.manager.setOutdir(path)
            self.single_manager.setOutdir(path)
            self._save("download/folder", path)
            self.outputFolderChanged.emit(path)
            self.notifyText.emit(self._tr("output_folder", path=path))

    @Slot()
    def openOutputFolder(self) -> None:
        opener = getattr(self, "_open_directory", None)
        if callable(opener):
            opener(self._output_folder)

    @Slot(int)
    def setConcurrency(self, n: int) -> None:
        n = self._clamp(int(n), 1, 8)
        if n == self._concurrency:
            return
        self._concurrency = n
        self.manager.setConcurrency(n)
        self._save("download/concurrency", n)
        self.concurrencyChanged.emit(n)

    def _limit_rate_arg(self) -> str:
        if self._limit_rate_mb <= 0:
            return ""
        return f"{self._limit_rate_mb}M"

    @Slot(int)
    def setLimitRateMB(self, mb: int) -> None:
        mb = self._clamp(int(mb), 0, 1000)
        if mb == self._limit_rate_mb:
            return
        self._limit_rate_mb = mb
        self.manager.setLimitRate(self._limit_rate_arg())
        self.single_manager.setLimitRate(self._limit_rate_arg())
        self._save("download/limit_rate", mb)
        self.limitRateChanged.emit(mb)

    @Slot(int)
    def setFragments(self, n: int) -> None:
        n = self._clamp(int(n), 1, 8)
        if n == self._fragments:
            return
        self._fragments = n
        self.manager.setFragments(n)
        self.single_manager.setFragments(n)
        self._save("download/fragments", n)
        self.fragmentsChanged.emit(n)

    @Slot(bool)
    def setDark(self, value: bool) -> None:
        value = bool(value)
        if value == self._dark:
            return
        self._dark = value
        self._save("theme/dark", value)
        self.darkChanged.emit(value)

    @staticmethod
    def _cookies_file_valid(path: str) -> bool:
        """Accept a non-empty Netscape cookie file (7 tab-separated fields)."""
        if not path or not os.path.isfile(path):
            return False
        try:
            if os.path.getsize(path) <= 0:
                return False
            with open(path, encoding="utf-8", errors="ignore") as handle:
                for _ in range(20):
                    line = handle.readline()
                    if not line:
                        break
                    if line.startswith("#HttpOnly_"):
                        line = line[len("#HttpOnly_"):]
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    if len(stripped.split("\t")) >= 7:
                        return True
        except OSError:
            return False
        return False

    def _build_cookies_arg(self) -> str:
        if not self._cookies_enabled:
            return ""
        path = self._cookies_file.strip()
        if path:
            return "file:" + path if self._cookies_file_valid(path) else ""
        if 0 <= self._cookies_browser_index < len(BROWSERS):
            return "browser:" + BROWSERS[self._cookies_browser_index]
        return ""

    def _push_cookies(self) -> None:
        arg = self._build_cookies_arg()
        self.manager.setCookies(arg)
        self.single_manager.setCookies(arg)

    @Slot(bool)
    def setCookiesEnabled(self, value: bool) -> None:
        value = bool(value)
        if value == self._cookies_enabled:
            return
        self._cookies_enabled = value
        self._save("cookies/enabled", value)
        self._push_cookies()
        self.cookiesEnabledChanged.emit(value)

    @Slot(int)
    def setCookiesBrowserIndex(self, index: int) -> None:
        index = self._clamp(int(index), 0, len(BROWSERS) - 1)
        if index == self._cookies_browser_index:
            return
        self._cookies_browser_index = index
        self._save("cookies/browser_index", index)
        self._push_cookies()
        self.cookiesBrowserIndexChanged.emit(index)

    @Slot(str)
    def setCookiesFile(self, path: str) -> None:
        path = (path or "").strip()
        if path == self._cookies_file:
            return
        self._cookies_file = path
        self._save("cookies/file", path)
        self._push_cookies()
        if path:
            self.notifyText.emit(
                self._tr("cookies_file_ok") if self._cookies_file_valid(path)
                else self._tr("cookies_file_invalid")
            )
        self.cookiesFileChanged.emit(path)

    @Slot()
    def chooseCookiesFile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            self._tr("dlg_cookies"),
            "",
            self._tr("filter_cookies"),
        )
        if path:
            self.setCookiesFile(path)

    @Slot(int, int, int, int, bool)
    def saveGeometry(self, x: int, y: int, w: int, h: int, maximized: bool) -> None:
        self._save("window/geometry", f"{x},{y},{w},{h}")
        self._save("window/maximized", maximized)


