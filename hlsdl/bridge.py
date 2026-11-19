"""Ponte entre o QML e o backend.

O QML chama os ``@Slot`` e reage aos sinais. Também persiste as
preferências em ``settings.ini`` e expõe o estado das dependências externas.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time

from PySide6.QtCore import (
    Property,
    QObject,
    QSettings,
    Qt,
    QTimer,
    Slot,
)
from PySide6.QtGui import QGuiApplication

from . import __version__, config, persistence
from .bridge_parts.compression import CompressionMixin
from .bridge_parts.dependencies import DependenciesMixin
from .bridge_parts.downloads import DownloadsMixin
from .bridge_parts.playlist import PlaylistMixin
from .bridge_parts.settings import SettingsMixin
from .bridge_parts.similarity import SimilarityMixin
from .bridge_parts.updates import UpdatesMixin
from .compress import (
    CODECS as COMPRESSION_CODECS,
)
from .compress import (
    CONTAINERS,
    DEFAULT_CONTAINERS,
    ENCODER_ORDER,
    SPEEDS,
    CompressionManager,
    CompressionModel,
    CompressionSettings,
)
from .config import BROWSERS, journals_dir, queue_state_path, user_config_dir
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
from .i18n import detect_language, tr
from .integrity import recover_journals, set_sidecars_enabled, verify_completion
from .model import DownloadFilterProxyModel, DownloadModel
from .playlist import PlaylistLoader
from .queue import QueueManager
from .similarity import SimilarityScanner
from .updater import Updater


class Bridge(
    SettingsMixin,
    DownloadsMixin,
    CompressionMixin,
    SimilarityMixin,
    UpdatesMixin,
    PlaylistMixin,
    DependenciesMixin,
    QObject,
):
    """Ponte entre o QML e o backend (``QueueManager``/``DependencyManager``)."""


    def __init__(
        self,
        manager: QueueManager,
        default_outdir: str,
        parent: QObject | None = None,
        settings_path: str | None = None,
        deps: DependencyManager | None = None,
        defer_detection: bool = False,
        state_path: str | None = None,
    ):
        super().__init__(parent)
        self.manager = manager
        self.batch_proxy = DownloadFilterProxyModel(self)
        self.batch_proxy.setSourceModel(manager.model)
        self._settings = QSettings(
            settings_path or default_settings_path(), QSettings.Format.IniFormat
        )
        self._sidecars_enabled = self._setting_bool("integrity/sidecars", False)
        set_sidecars_enabled(self._sidecars_enabled)

        # -------------------------------------------------- carrega o estado
        dark_default = True
        try:
            scheme = QGuiApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                dark_default = False
        except Exception:
            pass
        self._dark = self._setting_bool("theme/dark", dark_default)
        self._concurrency = self._setting_int("download/concurrency", 3, 1, 8)
        self._limit_rate_mb = self._setting_int("download/limit_rate", 0, 0, 1000)
        self._fragments = self._setting_int("download/fragments", 1, 1, 8)
        folder = str(self._settings.value("download/folder", default_outdir) or "").strip()
        self._output_folder = os.path.abspath(
            os.path.expanduser(folder or default_outdir)
        )
        self._cookies_enabled = self._setting_bool("cookies/enabled", False)
        self._cookies_browser_index = self._setting_int(
            "cookies/browser_index", 0, 0, len(BROWSERS) - 1
        )
        self._cookies_file = str(self._settings.value("cookies/file", "") or "").strip()
        self._deps_prompt_dismissed = self._setting_bool(
            "deps/prompt_dismissed", False
        )
        stored_lang = str(self._settings.value("i18n/language", "") or "").strip()
        self._lang = detect_language(stored_lang)
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
        self._comp_scan_busy = False
        self._comp_scan_cancel: threading.Event | None = None
        self.compressionScanFinished.connect(
            self._finishCompressionScan, Qt.ConnectionType.QueuedConnection
        )
        self._similar_groups: list = []
        self._similar_busy = False
        self._similar_progress = 0
        self._similar_total = 0
        self._similar_status = ""
        self._similar_threshold = 85
        self._recovery_messages: list = []
        self._encoder_refresh_busy = False
        self._aux_threads: list[threading.Thread] = []
        if state_path:
            self._queue_state_path = state_path
        else:
            # Keep tests/custom settings isolated: only the default app
            # settings use the global queue snapshot.
            effective = settings_path or default_settings_path()
            try:
                is_default = os.path.normcase(os.path.abspath(effective)) == os.path.normcase(
                    os.path.abspath(default_settings_path())
                )
            except OSError:
                is_default = False
            self._queue_state_path = (
                queue_state_path() if is_default
                else os.path.join(os.path.dirname(os.path.abspath(effective)), "queue.json")
            )
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(800)
        self._persist_timer.timeout.connect(self._persist_state)

        # Fila própria do Download Individual. Antes, um clique em "Baixar
        # agora" iniciava também todos os itens pendentes do lote.
        self.single_manager = QueueManager(
            DownloadModel([]),
            outdir=self._output_folder,
            concurrency=1,
            worker_factory=manager.worker_factory,
            catalog_path=getattr(manager, "catalog_path", None),
        )

        # ------------------------------------------------------ compressão
        self.compression = CompressionManager(
            CompressionModel([]), self, defer_detection=defer_detection,
            catalog_path=config.catalog_path(),
        )
        self.compression.set_translator(self._translator())
        self.compression.statsChanged.connect(self.compressionStatsChanged.emit)
        self.compression.stateChanged.connect(self._on_comp_state)
        self.compression.qsvDevicesChanged.connect(self.compressionQsvDevicesChanged.emit)
        self.compression.qualityPromptChanged.connect(
            self.compressionQualityPromptChanged.emit
        )
        self._comp_settings = CompressionSettings(
            encoder=str(self._settings.value("compress/encoder", "auto")),
            codec=str(self._settings.value("compress/codec", "hevc")),
            container=str(self._settings.value("compress/container", "mp4")),
            quality=self._setting_int("compress/quality", 24, 1, 51),
            min_bitrate_percent=self._setting_int(
                "compress/min_bitrate_percent", 0, 0, 90
            ),
            speed=str(self._settings.value("compress/speed", "balanced")),
            parallel=self._setting_int("compress/parallel", 1, 1, 8),
            min_size_mb=self._setting_int("compress/min_size_mb", 0, 0, 100000),
            only_if_smaller=self._setting_bool("compress/only_if_smaller", True),
            replace_original=self._setting_bool("compress/replace_original", False),
            reencode_hevc=self._setting_bool("compress/reencode_hevc", False),
            skip_hdr=self._setting_bool("compress/skip_hdr", True),
            qsv_device=self._setting_int("compress/qsv_device", -1, -1, 15),
            ten_bit=self._setting_bool("compress/ten_bit", False),
            x265_tuning=self._setting_bool("compress/x265_tuning", False),
            hw_decode=self._setting_bool("compress/hw_decode", False),
            crop=str(self._settings.value("compress/crop", "") or ""),
            scale_width=self._setting_int("compress/scale_width", 0, 0, 7680),
            scale_height=self._setting_int("compress/scale_height", 0, 0, 4320),
            rotate=self._setting_int("compress/rotate", 0, 0, 270),
            fps=self._setting_float("compress/fps", 0.0, 0.0, 240.0),
            preset=str(self._settings.value("compress/preset", "custom")),
            hdr_tonemap=self._setting_bool("compress/hdr_tonemap", False),
            deinterlace=str(self._settings.value("compress/deinterlace", "auto")),
            denoise=str(self._settings.value("compress/denoise", "off")),
            audio_mode=str(self._settings.value("compress/audio_mode", "auto")),
            subtitle_mode=str(self._settings.value("compress/subtitle_mode", "auto")),
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

        # ------------------------------------------------ similaridade local
        self.similarity = SimilarityScanner(self)
        self.similarity.stateChanged.connect(self._on_similar_state)
        self.similarity.progress.connect(self._on_similar_progress)
        self.similarity.finished.connect(self._on_similar_finished)
        self.similarity.failed.connect(self._on_similar_failed)

        self._start_aux(self._recover_interrupted_jobs, "hlsdl-recovery")

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
        manager.queueStateChanged.connect(self._on_queue_state)
        # Só a fila individual alimenta o card "Último download".
        self.single_manager.itemUpdated.connect(self._on_item_updated)

        manager.setConcurrency(self._concurrency)
        for target in (manager, self.single_manager):
            target.outdir = self._output_folder
            target.set_translator(self._translator())
            target.setCookies(self._build_cookies_arg())
            target.setLimitRate(self._limit_rate_arg())
            target.setFragments(self._fragments)
            target.setFormatMode(self._format_mode)
            target.setQuality(self._quality)
            target.setContainer(self._container)
            target.setCodec(self._codec)
            target.setCompressLevel(self._compress_level)
            target.setNamingMode(self._naming_mode)

        # Restore only after every stats/state signal is connected.
        self._restore_queue_state()
        manager.itemsChanged.connect(self._schedule_persist)
        self.compression.itemsChanged.connect(self._schedule_persist)

        if defer_detection:
            self._start_aux(
                self._detect_initial_environment, "hlsdl-detect-env"
            )
        else:
            self.deps.check_all()

    def _start_aux(self, target, name: str) -> None:
        """Inicia uma thread auxiliar rastreável pelo shutdown do Bridge."""
        if getattr(self, "_shutting_down", False):
            return
        thread = threading.Thread(target=target, name=name, daemon=True)
        self._aux_threads.append(thread)
        thread.start()

    def _detect_initial_environment(self) -> None:
        """Detecta encoders/dependências fora da thread da GUI no startup."""
        try:
            self.compression.refresh_encoders()
            if not getattr(self, "_shutting_down", False):
                self.compressionEncodersChanged.emit()
                self.compressionEffectiveEncoderChanged.emit()
        except Exception:
            logging.getLogger("hlsdl").exception("falha ao detectar encoders")
        try:
            if not getattr(self, "_shutting_down", False):
                self.deps.check_all()
        except Exception:
            logging.getLogger("hlsdl").exception("falha ao detectar dependências")

    def _recover_interrupted_jobs(self) -> None:
        """Replay compression journals after a crash/power loss."""
        try:
            results = recover_journals(
                journals_dir(),
                verify_cb=lambda path: verify_completion(path, full_hash=True),
            )
        except Exception:
            logging.getLogger("hlsdl").exception("falha ao recuperar jobs interrompidos")
            return
        messages = []
        for result in results:
            action = result.get("action")
            final = result.get("final") or result.get("source") or ""
            if action in ("kept_installed", "completed"):
                messages.append(self._tr("recovery_kept", path=final))
            elif action in ("restored_backup", "rolled_back", "discarded_partial"):
                messages.append(self._tr("recovery_restored", path=result.get("source") or final))
            else:
                messages.append(self._tr("recovery_error", path=final))
        self._recovery_messages = messages
        if messages and not getattr(self, "_shutting_down", False):
            self.recoveryChanged.emit()

    def _restore_queue_state(self) -> None:
        data = persistence.load(self._queue_state_path)
        downloads = [
            item for item in data.get("downloads") or []
            if str(item.get("status") or "") != "done"
        ]
        if downloads:
            self.manager.restore_items(downloads)
        paths = [
            str(item.get("input") or "")
            for item in data.get("compression") or []
        ]
        paths = [path for path in paths if path and os.path.isfile(path)]
        if paths:
            self.compression.add_paths(paths, recursive=False)

    def _schedule_persist(self) -> None:
        if self._persist_timer is not None:
            self._persist_timer.start()

    def _persist_state(self) -> None:
        persistence.save(
            self._queue_state_path,
            self.manager.items,
            self.compression.items,
        )

    # ------------------------------------------------------------- utilidades
    @staticmethod
    def _clamp(value: int, low: int, high: int) -> int:
        return max(low, min(high, value))

    def _setting_int(self, key: str, default: int, low: int, high: int) -> int:
        """Lê um inteiro do QSettings sem deixar um INI corrompido derrubar o app."""
        raw = self._settings.value(key, default)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default
        return self._clamp(value, low, high)

    def _setting_float(self, key: str, default: float,
                       low: float, high: float) -> float:
        raw = self._settings.value(key, default)
        try:
            value = float(str(raw).replace(",", "."))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    def _setting_bool(self, key: str, default: bool) -> bool:
        raw = self._settings.value(key, default)
        if isinstance(raw, bool):
            return raw
        if raw is None:
            return default
        return str(raw).strip().lower() in ("1", "true", "yes", "on")

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














    @Slot()
    def refreshStats(self) -> None:
        """Push initial counters to QML after restored items are in place."""
        try:
            self.manager._emit_stats()
            self.single_manager._emit_stats()
            self.compression._emit_stats()
        except Exception:
            pass





















    # ----------------------------------------------------------- compressão

















































































    # ------------------------------------------------------- similaridade local



















    # ---------------------------------------------------------- atualizações















    # ------------------------------------------------------------ playlists





    def _jobs_active(self) -> bool:
        return bool(
            self.manager.isActive
            or self.single_manager.isActive
            or self.compressionActive
        )


        # O estado (ativo/pausado) vem de manager.queueStateChanged.












    # ---------------------------------------------------------------- slots







    # -------------------------------------------------------------- rede




    # -------------------------------------------------------------- cookies







    # -------------------------------------------------------- janela/geometria

    # ------------------------------------------------------------ fila














    def shutdown(self) -> None:
        """Encerra download/playlist/instalação/compressão ao fechar."""
        self._shutting_down = True
        try:
            self._persist_state()
        except Exception:
            pass
        try:
            self._playlist.cancel()
        except Exception:
            pass
        try:
            self.similarity.shutdown()
        except Exception:
            pass
        try:
            self.updater.shutdown()
        except Exception:
            pass
        cancel = getattr(self.deps, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass
        shutdown = getattr(self.deps, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown(timeout=3.0)
            except TypeError:
                shutdown()
            except Exception:
                pass
        cancel_scan = getattr(self, "_comp_scan_cancel", None)
        if cancel_scan is not None:
            cancel_scan.set()
        self.compression.shutdown()
        self.single_manager.shutdown()
        self.manager.shutdown()
        deadline = time.monotonic() + 3.0
        for thread in list(self._aux_threads):
            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=max(0.0, deadline - time.monotonic()))
            if thread.is_alive():
                logging.getLogger("hlsdl").warning(
                    "thread auxiliar %s ainda ativa após o shutdown",
                    thread.name,
                )
        self._aux_threads.clear()

    def _open_directory(self, folder: str) -> bool:
        """Abre uma pasta e informa erro acionável em vez de silenciar."""
        if not folder or not os.path.isdir(folder):
            self.notifyText.emit(self._tr("folder_missing"))
            return False
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys_platform_darwin():
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError as exc:
            self.notifyText.emit(self._tr("open_folder_failed", err=exc))
            return False
        return True

    @Slot(str)
    def openDownloadPath(self, path: str) -> None:
        """Abre o gerenciador de arquivos na pasta onde o arquivo foi salvo."""
        self._open_directory(os.path.dirname(path))

    @Slot()
    def openLogFolder(self) -> None:
        """Abre a pasta onde ficam logs e settings (portátil/dev incluídos)."""
        from .config import log_path

        self._open_directory(os.path.dirname(log_path()) or user_config_dir())

    # ---------------------------------------------------- dependências (slots)









def sys_platform_darwin() -> bool:
    import sys

    return sys.platform == "darwin"
