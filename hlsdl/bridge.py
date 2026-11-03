"""Ponte entre o QML e o backend.

O QML chama os ``@Slot`` e reage aos sinais. Também persiste as
preferências em ``settings.ini`` e expõe o estado das dependências externas.
"""

from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import Property, QObject, QSettings, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import __version__
from .compress import (
    CODEC_NAMES,
    CONTAINERS,
    DEFAULT_CONTAINERS,
    ENCODER_NAMES,
    ENCODER_ORDER,
    SPEEDS,
    CompressionManager,
    CompressionModel,
    CompressionSettings,
    available_vendors,
    estimate_saving,
)
from .compress import (
    CODECS as COMPRESSION_CODECS,
)
from .config import BROWSERS, is_portable, user_config_dir
from .config import settings_path as default_settings_path
from .deps import YTDLP_VARIANTS, DependencyManager
from .formats import (
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
from .i18n import LANGUAGE_NAMES, LANGUAGES, tr
from .playlist import PlaylistLoader
from .queue import QueueManager
from .services.procutils import spawn_kwargs
from .updater import Updater
from .urlutils import normalize_url


class Bridge(QObject):
    """Ponte entre o QML e o backend (``QueueManager``/``DependencyManager``)."""

    statsChanged = Signal(int, int, int, int)   # aguardando, baixando, ok, erro
    notifyText = Signal(str)                    # toast no QML
    outputFolderChanged = Signal(str)
    darkChanged = Signal(bool)
    concurrencyChanged = Signal(int)
    limitRateChanged = Signal(int)
    fragmentsChanged = Signal(int)
    cookiesEnabledChanged = Signal(bool)
    cookiesBrowserIndexChanged = Signal(int)
    cookiesFileChanged = Signal(str)
    languageChanged = Signal(str)
    queueActiveChanged = Signal(bool)
    queuePausedChanged = Signal(bool)
    formatModeChanged = Signal(str)
    qualityChanged = Signal(str)
    containerChanged = Signal(str)
    codecChanged = Signal(str)
    compressLevelChanged = Signal(str)
    namingModeChanged = Signal(str)
    ytdlpVariantChanged = Signal(str)
    lastItemChanged = Signal()
    playlistChanged = Signal()
    playlistLoadingChanged = Signal(bool)
    compressionStatsChanged = Signal(int, int, int, int, int)
    compressionStateChanged = Signal(bool, bool)
    compressionConfigChanged = Signal()
    compressionEncodersChanged = Signal()
    compressionQsvDevicesChanged = Signal()
    updateChanged = Signal()
    updateProgressChanged = Signal(int)
    depsChanged = Signal()
    depsOutput = Signal(str)
    depsInstallFinished = Signal(str, bool, str)

    def __init__(
        self,
        manager: QueueManager,
        default_outdir: str,
        parent: QObject | None = None,
        settings_path: str | None = None,
        deps: DependencyManager | None = None,
    ):
        super().__init__(parent)
        self.manager = manager
        self._settings = QSettings(
            settings_path or default_settings_path(), QSettings.Format.IniFormat
        )

        # -------------------------------------------------- carrega o estado
        self._dark = self._settings.value("theme/dark", True, type=bool)
        self._concurrency = self._clamp(int(self._settings.value("download/concurrency", 3)), 1, 8)
        self._limit_rate_mb = self._clamp(int(self._settings.value("download/limit_rate", 0)), 0, 1000)
        self._fragments = self._clamp(int(self._settings.value("download/fragments", 1)), 1, 8)
        self._output_folder = str(self._settings.value("download/folder", default_outdir))
        self._cookies_enabled = self._settings.value("cookies/enabled", False, type=bool)
        self._cookies_browser_index = self._clamp(
            int(self._settings.value("cookies/browser_index", 0)), 0, len(BROWSERS) - 1
        )
        self._cookies_file = str(self._settings.value("cookies/file", ""))
        self._deps_prompt_dismissed = self._settings.value(
            "deps/prompt_dismissed", False, type=bool
        )
        self._lang = str(self._settings.value("i18n/language", "pt"))
        if self._lang not in LANGUAGES:
            self._lang = "pt"
        self._format_mode = str(self._settings.value("download/format_mode", "video_audio"))
        if self._format_mode not in FORMAT_MODES:
            self._format_mode = "video_audio"
        self._quality = str(self._settings.value("download/quality", "best"))
        if self._quality not in QUALITIES:
            self._quality = "best"
        self._container = str(self._settings.value("download/container", ""))
        _valid_containers = AUDIO_CONTAINERS if self._format_mode == "audio_only" else VIDEO_CONTAINERS
        if self._container not in _valid_containers:
            self._container = (
                DEFAULT_AUDIO_CONTAINER if self._format_mode == "audio_only"
                else DEFAULT_VIDEO_CONTAINER
            )
        self._codec = str(self._settings.value("encode/codec", "copy"))
        if self._codec not in CODECS:
            self._codec = "copy"
        self._compress_level = str(self._settings.value("encode/level", "medium"))
        if self._compress_level not in COMPRESS_LEVELS:
            self._compress_level = "medium"
        self._naming_mode = str(self._settings.value("naming/mode", "id"))
        if self._naming_mode not in NAMING_MODES:
            self._naming_mode = "id"
        self._ytdlp_variant = str(self._settings.value("deps/ytdlp_variant", "stable"))
        if self._ytdlp_variant not in YTDLP_VARIANTS:
            self._ytdlp_variant = "stable"

        self._deps_list: list[dict] = []
        self._deps_busy = False
        self._last_item: dict = {}
        self._single_item_id: int | None = None
        self._queue_active = False
        self._queue_paused = False
        self._playlist_items: list = []
        self._playlist_loading = False
        self._comp_active = False
        self._comp_paused = False

        # ------------------------------------------------------ compressão
        self.compression = CompressionManager(CompressionModel([]), self)
        self.compression.set_translator(self._translator())
        self.compression.statsChanged.connect(self.compressionStatsChanged.emit)
        self.compression.stateChanged.connect(self._on_comp_state)
        self.compression.qsvDevicesChanged.connect(self.compressionQsvDevicesChanged.emit)
        self._comp_settings = CompressionSettings(
            encoder=str(self._settings.value("compress/encoder", "auto")),
            codec=str(self._settings.value("compress/codec", "hevc")),
            container=str(self._settings.value("compress/container", "mp4")),
            quality=self._clamp(int(self._settings.value("compress/quality", 24)), 1, 51),
            speed=str(self._settings.value("compress/speed", "balanced")),
            parallel=self._clamp(int(self._settings.value("compress/parallel", 1)), 1, 8),
            min_size_mb=self._clamp(int(self._settings.value("compress/min_size_mb", 0)), 0, 100000),
            only_if_smaller=self._settings.value("compress/only_if_smaller", True, type=bool),
            replace_original=self._settings.value("compress/replace_original", False, type=bool),
            reencode_hevc=self._settings.value("compress/reencode_hevc", False, type=bool),
            skip_hdr=self._settings.value("compress/skip_hdr", True, type=bool),
            qsv_device=self._clamp(
                int(self._settings.value("compress/qsv_device", -1)), -1, 15
            ),
            ten_bit=self._settings.value("compress/ten_bit", False, type=bool),
            x265_tuning=self._settings.value("compress/x265_tuning", False, type=bool),
        )
        if self._comp_settings.encoder == "x265":
            self._comp_settings.encoder = "software"
        if self._comp_settings.encoder not in ("auto", *ENCODER_ORDER):
            self._comp_settings.encoder = "auto"
        if self._comp_settings.codec not in COMPRESSION_CODECS:
            self._comp_settings.codec = "hevc"
        if self._comp_settings.container not in CONTAINERS[self._comp_settings.codec]:
            self._comp_settings.container = DEFAULT_CONTAINERS[self._comp_settings.codec]
        if self._comp_settings.speed not in SPEEDS:
            self._comp_settings.speed = "balanced"
        self.compression.apply_settings(self._comp_settings)
        self.compression.finishedAll.connect(self._on_comp_finished)

        # ------------------------------------------------------ atualizações
        self._update_info: dict = {}
        self._update_status = ""
        self._update_busy = False
        self._update_progress = 0
        self.updater = Updater(self)
        self.updater.checkingChanged.connect(self._on_update_checking)
        self.updater.checked.connect(self._on_update_checked)
        self.updater.downloadProgress.connect(self._on_update_progress)
        self.updater.ready.connect(self._on_update_ready)
        self.updater.failed.connect(self._on_update_failed)

        # -------------------------------------------------- dependências
        self.deps = deps or DependencyManager(self)
        self.deps.variant = self._ytdlp_variant
        self.deps.checked.connect(self._on_deps_checked)
        self.deps.installStarted.connect(self._on_deps_started)
        self.deps.installOutput.connect(self.depsOutput.emit)
        self.deps.installFinished.connect(self._on_deps_finished)

        # ------------------------------------------------------ playlists
        self._playlist = PlaylistLoader(self._translator(), self)
        self._playlist.loadingChanged.connect(self._on_playlist_loading)
        self._playlist.loaded.connect(self._on_playlist_loaded)
        self._playlist.failed.connect(self._on_playlist_failed)

        # ------------------------------------------------------- aplica tudo
        manager.statsChanged.connect(self.statsChanged.emit)
        manager.outdirChanged.connect(self.outputFolderChanged.emit)
        manager.itemUpdated.connect(self._on_item_updated)
        manager.queueStateChanged.connect(self._on_queue_state)
        manager.outdir = self._output_folder
        manager.setConcurrency(self._concurrency)
        manager.set_translator(self._translator())
        manager.setCookies(self._build_cookies_arg())
        manager.setLimitRate(self._limit_rate_arg())
        manager.setFragments(self._fragments)
        manager.setFormatMode(self._format_mode)
        manager.setQuality(self._quality)
        manager.setContainer(self._container)
        manager.setCodec(self._codec)
        manager.setCompressLevel(self._compress_level)
        manager.setNamingMode(self._naming_mode)

        self.deps.check_all()

    # ------------------------------------------------------------- utilidades
    @staticmethod
    def _clamp(value: int, low: int, high: int) -> int:
        return max(low, min(high, value))

    def _save(self, key: str, value) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    def _tr(self, key: str, **kw) -> str:
        return tr(self._lang, key, **kw)

    def _translator(self):
        return lambda key, **kw: tr(self._lang, key, **kw)

    # ------------------------------------------------------------- atributos
    @Property(str, constant=True)
    def appVersion(self) -> str:
        return __version__

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

    @Property(bool, notify=queueActiveChanged)
    def queueActive(self) -> bool:
        return self._queue_active

    @Property(bool, notify=queuePausedChanged)
    def queuePaused(self) -> bool:
        return self._queue_paused

    def _on_queue_state(self, active: bool, paused: bool) -> None:
        if active != self._queue_active:
            self._queue_active = active
            self.queueActiveChanged.emit(active)
        if paused != self._queue_paused:
            self._queue_paused = paused
            self.queuePausedChanged.emit(paused)

    def _ytdlp_available(self) -> bool:
        return any(d["key"] == "ytdlp" and d["found"] for d in self._deps_list)

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

    @Property("QVariantMap", notify=lastItemChanged)
    def lastItem(self) -> dict:
        return self._last_item

    def _on_item_updated(self, item: dict) -> None:
        # A aba Individual só reflete o item iniciado por downloadSingle().
        if self._single_item_id is None or item.get("id") != self._single_item_id:
            return
        status = item.get("status")
        self._last_item = {
            "url": item.get("url", ""),
            "title": item.get("title") or item.get("url", ""),
            "status": getattr(status, "value", str(status)),
            "progress": round(float(item.get("progress", 0.0)), 1),
            "speed": item.get("speed", "—"),
            "size": item.get("size", "—"),
            "error": item.get("error", ""),
            "path": item.get("path", ""),
            "thumbnail": item.get("thumb", ""),
        }
        self.lastItemChanged.emit()

    def _sync_single_item(self) -> None:
        """Limpa o card individual se o item saiu da fila."""
        if self._single_item_id is None:
            return
        if any(i["id"] == self._single_item_id for i in self.manager.items):
            return
        self._single_item_id = None
        self._last_item = {}
        self.lastItemChanged.emit()

    # ----------------------------------------------------------- compressão
    @Property(str, notify=compressionConfigChanged)
    def compressionEncoder(self) -> str:
        return self._comp_settings.encoder

    @Slot(str)
    def setCompressionEncoder(self, key: str) -> None:
        key = key if key in ("auto", *ENCODER_ORDER) else "auto"
        if key == self._comp_settings.encoder:
            return
        self._comp_settings.encoder = key
        self._save("compress/encoder", key)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(list, constant=True)
    def compressionCodecs(self) -> list:
        return [{"key": key, "name": CODEC_NAMES[key]} for key in COMPRESSION_CODECS]

    @Property(str, notify=compressionConfigChanged)
    def compressionCodec(self) -> str:
        return self._comp_settings.codec

    @Slot(str)
    def setCompressionCodec(self, codec: str) -> None:
        codec = codec if codec in COMPRESSION_CODECS else "hevc"
        if codec == self._comp_settings.codec:
            return
        self._comp_settings.codec = codec
        if self._comp_settings.container not in CONTAINERS[codec]:
            self._comp_settings.container = DEFAULT_CONTAINERS[codec]
            self._save("compress/container", self._comp_settings.container)
        self._save("compress/codec", codec)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()
        self.compressionEncodersChanged.emit()

    @Property(list, notify=compressionConfigChanged)
    def compressionContainers(self) -> list:
        return list(CONTAINERS[self._comp_settings.codec])

    @Property(str, notify=compressionConfigChanged)
    def compressionContainer(self) -> str:
        return self._comp_settings.container

    @Slot(str)
    def setCompressionContainer(self, container: str) -> None:
        allowed = CONTAINERS[self._comp_settings.codec]
        container = container if container in allowed else allowed[0]
        if container == self._comp_settings.container:
            return
        self._comp_settings.container = container
        self._save("compress/container", container)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionEstimate(self) -> int:
        return estimate_saving(self._comp_settings.codec,
                               self._comp_settings.quality)

    @Property(int, notify=compressionConfigChanged)
    def compressionQuality(self) -> int:
        return self._comp_settings.quality

    @Slot(int)
    def setCompressionQuality(self, value: int) -> None:
        value = self._clamp(int(value), 1, 51)
        if value == self._comp_settings.quality:
            return
        self._comp_settings.quality = value
        self._save("compress/quality", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(str, notify=compressionConfigChanged)
    def compressionSpeed(self) -> str:
        return self._comp_settings.speed

    @Slot(str)
    def setCompressionSpeed(self, speed: str) -> None:
        speed = speed if speed in SPEEDS else "balanced"
        if speed == self._comp_settings.speed:
            return
        self._comp_settings.speed = speed
        self._save("compress/speed", speed)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionParallel(self) -> int:
        return self._comp_settings.parallel

    @Slot(int)
    def setCompressionParallel(self, value: int) -> None:
        value = self._clamp(int(value), 1, 8)
        if value == self._comp_settings.parallel:
            return
        self._comp_settings.parallel = value
        self._save("compress/parallel", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionMinSizeMB(self) -> int:
        return self._comp_settings.min_size_mb

    @Slot(int)
    def setCompressionMinSizeMB(self, value: int) -> None:
        value = self._clamp(int(value), 0, 100000)
        if value == self._comp_settings.min_size_mb:
            return
        self._comp_settings.min_size_mb = value
        self._save("compress/min_size_mb", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    def _set_comp_bool(self, attr: str, value: bool, key: str) -> None:
        value = bool(value)
        if getattr(self._comp_settings, attr) == value:
            return
        setattr(self._comp_settings, attr, value)
        self._save(f"compress/{key}", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(bool, notify=compressionConfigChanged)
    def compressionOnlyIfSmaller(self) -> bool:
        return self._comp_settings.only_if_smaller

    @Slot(bool)
    def setCompressionOnlyIfSmaller(self, value: bool) -> None:
        self._set_comp_bool("only_if_smaller", value, "only_if_smaller")

    @Property(bool, notify=compressionConfigChanged)
    def compressionReplaceOriginal(self) -> bool:
        return self._comp_settings.replace_original

    @Slot(bool)
    def setCompressionReplaceOriginal(self, value: bool) -> None:
        self._set_comp_bool("replace_original", value, "replace_original")

    @Property(bool, notify=compressionConfigChanged)
    def compressionReencodeHevc(self) -> bool:
        return self._comp_settings.reencode_hevc

    @Slot(bool)
    def setCompressionReencodeHevc(self, value: bool) -> None:
        self._set_comp_bool("reencode_hevc", value, "reencode_hevc")

    @Property(bool, notify=compressionConfigChanged)
    def compressionSkipHdr(self) -> bool:
        return self._comp_settings.skip_hdr

    @Slot(bool)
    def setCompressionSkipHdr(self, value: bool) -> None:
        self._set_comp_bool("skip_hdr", value, "skip_hdr")

    @Property(bool, notify=compressionConfigChanged)
    def compressionTenBit(self) -> bool:
        return self._comp_settings.ten_bit

    @Slot(bool)
    def setCompressionTenBit(self, value: bool) -> None:
        self._set_comp_bool("ten_bit", value, "ten_bit")

    @Property(bool, notify=compressionConfigChanged)
    def compressionX265Tuning(self) -> bool:
        return self._comp_settings.x265_tuning

    @Slot(bool)
    def setCompressionX265Tuning(self, value: bool) -> None:
        self._set_comp_bool("x265_tuning", value, "x265_tuning")

    @Property(list, notify=compressionEncodersChanged)
    def compressionEncoders(self) -> list:
        availability = available_vendors(
            self._comp_settings.codec, self.compression.available
        )
        items = [{"key": "auto", "name": "Auto", "available": True}]
        for key in ENCODER_ORDER:
            name = ENCODER_NAMES[key]
            if not availability.get(key):
                name += " (n/d)"
            items.append({
                "key": key,
                "name": name,
                "available": bool(availability.get(key)),
            })
        return items

    @Property(list, notify=compressionQsvDevicesChanged)
    def compressionQsvDevices(self) -> list:
        items = [{"index": -1, "name": "Auto (dedicada)"}]
        for device in self.compression.qsv_devices:
            items.append({
                "index": int(device["index"]),
                "name": f"{device['name']} ({device['index']})",
            })
        return items

    @Property(int, notify=compressionConfigChanged)
    def compressionQsvDevice(self) -> int:
        return self._comp_settings.qsv_device

    @Slot(int)
    def setCompressionQsvDevice(self, index: int) -> None:
        index = self._clamp(int(index), -1, 15)
        if index == self._comp_settings.qsv_device:
            return
        self._comp_settings.qsv_device = index
        self._save("compress/qsv_device", index)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Slot()
    def refreshCompressionEncoders(self) -> None:
        self.compression.refresh_encoders()
        self.compressionEncodersChanged.emit()

    @Property(bool, notify=compressionStateChanged)
    def compressionActive(self) -> bool:
        return self._comp_active

    @Property(bool, notify=compressionStateChanged)
    def compressionPaused(self) -> bool:
        return self._comp_paused

    def _on_comp_state(self, active: bool, paused: bool) -> None:
        self._comp_active = active
        self._comp_paused = paused
        self.compressionStateChanged.emit(active, paused)

    def _on_comp_finished(self, done: int, errors: int, skipped: int) -> None:
        message = self._tr(
            "compress_finished", done=done, errors=errors, skipped=skipped
        )
        self.notifyText.emit(message)
        if errors:
            QMessageBox.warning(
                None, self._tr("compress_finished_title"), message
            )

    @Slot()
    def addCompressionFiles(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            None,
            self._tr("compress_add_files"),
            "",
            "Vídeos (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;Todos os arquivos (*.*)",
        )
        if paths:
            added = self.compression.add_paths(paths, recursive=False)
            if added:
                self.notifyText.emit(self._tr("compress_files_added", n=added))

    @Slot()
    def addCompressionFolder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            None, self._tr("compress_add_folder"), ""
        )
        if path:
            added = self.compression.add_paths([path], recursive=True)
            if added:
                self.notifyText.emit(self._tr("compress_files_added", n=added))

    @Slot(list)
    def addCompressionPaths(self, paths: list) -> None:
        added = self.compression.add_paths([str(p) for p in paths], recursive=True)
        if added:
            self.notifyText.emit(self._tr("compress_files_added", n=added))

    @Slot()
    def startCompression(self) -> None:
        if not self.compression.items:
            self.notifyText.emit(self._tr("compress_no_items"))
            return
        self.compression.start()
        self.notifyText.emit(self._tr("compress_started"))

    @Slot()
    def pauseCompression(self) -> None:
        self.compression.pause()
        self.notifyText.emit(self._tr("compress_paused"))

    @Slot()
    def resumeCompression(self) -> None:
        self.compression.resume()
        self.notifyText.emit(self._tr("compress_resumed"))

    @Slot()
    def cancelCompression(self) -> None:
        self.compression.cancelAll()
        self.notifyText.emit(self._tr("compress_cancelled"))

    @Slot(int)
    def cancelCompressionItem(self, row: int) -> None:
        self.compression.cancelItem(row)

    @Slot(int)
    def removeCompressionItem(self, row: int) -> None:
        self.compression.removeItem(row)
        self.notifyText.emit(self._tr("item_removed"))

    @Slot()
    def clearCompressionFinished(self) -> None:
        self.compression.clearFinished()

    @Slot(str)
    def openCompressionOutput(self, path: str) -> None:
        self.openDownloadPath(path)

    # ---------------------------------------------------------- atualizações
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

    # ------------------------------------------------------------ playlists
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
    def clearPlaylist(self) -> None:
        self._playlist_items = []
        self.playlistChanged.emit()

    @Slot(str)
    def addLinksAndStart(self, text: str) -> None:
        """Adiciona links (ex.: selecionados de uma playlist) e inicia a fila."""
        added, skipped = self.manager.addText(text)
        if added:
            self.notifyText.emit(self._tr("links_added", a=added))
        elif skipped:
            self.notifyText.emit(self._tr("links_skipped", s=skipped))
        self.manager.start()
        # O estado (ativo/pausado) vem de manager.queueStateChanged.

    def _on_playlist_loading(self, loading: bool) -> None:
        self._playlist_loading = loading
        self.playlistLoadingChanged.emit(loading)

    def _on_playlist_loaded(self, items: list) -> None:
        self._playlist_items = items
        self.playlistChanged.emit()

    def _on_playlist_failed(self, message: str) -> None:
        self.notifyText.emit(message)

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
        """Não volta a perguntar sobre dependências nesta máquina."""
        if not self._deps_prompt_dismissed:
            self._deps_prompt_dismissed = True
            self._save("deps/prompt_dismissed", True)
            self.depsChanged.emit()

    # ---------------------------------------------------------------- slots
    @Slot(str)
    def addLinks(self, text: str) -> None:
        added, skipped = self.manager.addText(text)
        if added and skipped:
            self.notifyText.emit(self._tr("links_added_skipped", a=added, s=skipped))
        elif added:
            self.notifyText.emit(self._tr("links_added", a=added))
        elif skipped:
            self.notifyText.emit(self._tr("links_skipped", s=skipped))
        else:
            self.notifyText.emit(self._tr("no_links"))

    @Slot()
    def pasteFromClipboard(self) -> None:
        text = QApplication.clipboard().text()
        if text.strip():
            self.addLinks(text)
        else:
            self.notifyText.emit(self._tr("clipboard_empty"))

    @Slot()
    def importTxt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            self._tr("dlg_links"),
            "",
            "Arquivos de texto (*.txt);;Todos os arquivos (*.*)",
        )
        if path:
            self.importTxtPath(path)

    @Slot(str)
    def importTxtPath(self, path: str) -> None:
        """Lê um .txt (usado pelo botão e pelo arrastar-e-soltar)."""
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except OSError as exc:
            self.notifyText.emit(self._tr("read_failed", err=exc))
            return
        self.addLinks(content)

    @Slot()
    def chooseOutputFolder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            None, self._tr("dlg_outdir"), self._output_folder
        )
        if path:
            self._output_folder = path
            self.manager.setOutdir(path)
            self._save("download/folder", path)
            self.outputFolderChanged.emit(path)
            self.notifyText.emit(self._tr("output_folder", path=path))

    @Slot(int)
    def setConcurrency(self, n: int) -> None:
        n = self._clamp(int(n), 1, 8)
        if n == self._concurrency:
            return
        self._concurrency = n
        self.manager.setConcurrency(n)
        self._save("download/concurrency", n)
        self.concurrencyChanged.emit(n)

    # -------------------------------------------------------------- rede
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
        self._save("download/limit_rate", mb)
        self.limitRateChanged.emit(mb)

    @Slot(int)
    def setFragments(self, n: int) -> None:
        n = self._clamp(int(n), 1, 8)
        if n == self._fragments:
            return
        self._fragments = n
        self.manager.setFragments(n)
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

    # -------------------------------------------------------------- cookies
    def _build_cookies_arg(self) -> str:
        if not self._cookies_enabled:
            return ""
        if self._cookies_file.strip():
            return "file:" + self._cookies_file.strip()
        if 0 <= self._cookies_browser_index < len(BROWSERS):
            return "browser:" + BROWSERS[self._cookies_browser_index]
        return ""

    def _push_cookies(self) -> None:
        self.manager.setCookies(self._build_cookies_arg())

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
        self.cookiesFileChanged.emit(path)

    @Slot()
    def chooseCookiesFile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            self._tr("dlg_cookies"),
            "",
            "Arquivos de cookie (*.txt);;Todos os arquivos (*.*)",
        )
        if path:
            self.setCookiesFile(path)

    # -------------------------------------------------------- janela/geometria
    @Slot(int, int, int, int, bool)
    def saveGeometry(self, x: int, y: int, w: int, h: int, maximized: bool) -> None:
        self._save("window/geometry", f"{x},{y},{w},{h}")
        self._save("window/maximized", maximized)

    # ------------------------------------------------------------ fila
    @Slot(str)
    def downloadSingle(self, url: str) -> None:
        """Adiciona um único link e inicia a fila (aba Download Individual)."""
        url = (url or "").strip()
        if not url:
            self.notifyText.emit(self._tr("no_links"))
            return
        before = len(self.manager.items)
        added, _skipped = self.manager.addText(url)
        if added:
            item = self.manager.items[before]
            self._single_item_id = item["id"]
            self._on_item_updated(item)
        else:
            # Duplicado: foca o item existente com a mesma URL.
            normalized = normalize_url(url)
            match = next(
                (i for i in reversed(self.manager.items)
                 if normalize_url(i["url"]) == normalized),
                None,
            )
            if match is not None:
                self._single_item_id = match["id"]
                self._on_item_updated(match)
        self.manager.start()

    @Slot()
    def startQueue(self) -> None:
        self.manager.start()
        self.notifyText.emit(self._tr("queue_started"))

    @Slot()
    def pauseQueue(self) -> None:
        self.manager.pause()
        self.notifyText.emit(self._tr("queue_paused"))

    @Slot()
    def resumeQueue(self) -> None:
        self.manager.resume()
        self.notifyText.emit(self._tr("queue_resumed"))

    @Slot()
    def cancelAll(self) -> None:
        self.manager.cancelAll()
        self.notifyText.emit(self._tr("downloads_cancelled"))

    @Slot(int)
    def cancelItem(self, row: int) -> None:
        self.manager.cancelItem(row)
        self.notifyText.emit(self._tr("item_cancelled"))

    @Slot(int)
    def removeItem(self, row: int) -> None:
        self.manager.removeItem(row)
        self._sync_single_item()
        self.notifyText.emit(self._tr("item_removed"))

    @Slot(int)
    def retryItem(self, row: int) -> None:
        self.manager.retryItem(row)

    @Slot(int, str)
    def editUrl(self, row: int, new_url: str) -> bool:
        ok = self.manager.editUrl(row, new_url)
        self.notifyText.emit(self._tr("link_updated" if ok else "link_update_failed"))
        return ok

    @Slot(str)
    def copyLink(self, url: str) -> None:
        QGuiApplication.clipboard().setText(url)
        self.notifyText.emit(self._tr("link_copied"))

    @Slot()
    def clearFinished(self) -> None:
        self.manager.clearFinished()
        self._sync_single_item()

    @Slot()
    def clearAll(self) -> None:
        self.manager.clearAll()
        self._single_item_id = None
        self._last_item = {}
        self.lastItemChanged.emit()

    def shutdown(self) -> None:
        """Encerra download/playlist/instalação/compressão ao fechar."""
        try:
            self._playlist.cancel()
        except Exception:
            pass
        cancel = getattr(self.deps, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass
        self.compression.shutdown()
        self.manager.shutdown()

    @Slot(str)
    def openDownloadPath(self, path: str) -> None:
        """Abre o gerenciador de arquivos na pasta onde o arquivo foi salvo."""
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            return
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys_platform_darwin():
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            pass

    @Slot()
    def openLogFolder(self) -> None:
        """Abre a pasta onde ficam logs e settings."""
        folder = user_config_dir()
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys_platform_darwin():
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            pass

    # ---------------------------------------------------- dependências (slots)
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
        self.depsChanged.emit()

    @Slot()
    def refreshDependencies(self) -> None:
        self.deps.check_all()

    @Slot()
    def installMissingDependencies(self) -> None:
        self.deps.install_missing_required()

    @Slot(str)
    def installDependency(self, key: str) -> None:
        if not self.deps.install(key):
            if not self._deps_busy:
                self.notifyText.emit(self._tr("dep_not_applicable", name=key))

    @Slot()
    def updateDependencies(self) -> None:
        self.deps.update_all()

    def set_dependencies(self, items: list[dict]) -> None:
        """Permite injetar o estado (usado em testes)."""
        self._on_deps_checked(items)


def sys_platform_darwin() -> bool:
    import sys

    return sys.platform == "darwin"
