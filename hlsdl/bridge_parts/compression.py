# ruff: noqa: F401, F403, F405

from __future__ import annotations

import threading

from PySide6.QtCore import Property, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..compress import (
    AUDIO_MODES,
    CODEC_NAMES,
    COMPRESSION_PRESETS,
    CONTAINERS,
    DEFAULT_CONTAINERS,
    DEINTERLACE_MODES,
    DENOISE_MODES,
    ENCODER_NAMES,
    ENCODER_ORDER,
    SPEEDS,
    SUBTITLE_MODES,
    available_vendors,
    estimate_saving,
    quality_max_for_codec,
    resolve_encoder,
)
from ..compress import (
    CODECS as COMPRESSION_CODECS,
)
from ..nativeui import show_message
from .signals import *


class CompressionMixin(BridgeSignals):

    @Property(str, notify=compressionConfigChanged)
    def compressionPreset(self) -> str:
        return self._comp_settings.preset

    def _mark_comp_custom(self) -> None:
        if self._comp_settings.preset != "custom":
            self._comp_settings.preset = "custom"
            self._save("compress/preset", "custom")

    @Property(str, notify=compressionConfigChanged)
    def compressionEncoder(self) -> str:
        return self._comp_settings.encoder

    @Slot(str)
    def setCompressionEncoder(self, key: str) -> None:
        key = key if key in ("auto", *ENCODER_ORDER) else "auto"
        if key == self._comp_settings.encoder:
            return
        self._mark_comp_custom()
        self._comp_settings.encoder = key
        self._save("compress/encoder", key)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()
        self.compressionEffectiveEncoderChanged.emit()

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
        self._mark_comp_custom()
        self._comp_settings.codec = codec
        if self._comp_settings.container not in CONTAINERS[codec]:
            self._comp_settings.container = DEFAULT_CONTAINERS[codec]
            self._save("compress/container", self._comp_settings.container)
        self._save("compress/codec", codec)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()
        self.compressionEncodersChanged.emit()
        self.compressionEffectiveEncoderChanged.emit()

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
        self._mark_comp_custom()
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

    @Property(int, notify=compressionConfigChanged)
    def compressionQualityMax(self) -> int:
        """Limite de RF do codec atual (AV1 vai atÃ© 63)."""
        return quality_max_for_codec(self._comp_settings.codec)

    @Slot(int)
    def setCompressionQuality(self, value: int) -> None:
        value = self._clamp(
            int(value), 1, quality_max_for_codec(self._comp_settings.codec)
        )
        if value == self._comp_settings.quality:
            return
        self._mark_comp_custom()
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
        self._mark_comp_custom()
        self._comp_settings.speed = speed
        self._save("compress/speed", speed)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Property(bool, notify=compressionConfigChanged)
    def compressionHdrTonemap(self) -> bool:
        return bool(self._comp_settings.hdr_tonemap)

    @Slot(bool)
    def setCompressionHdrTonemap(self, value: bool) -> None:
        self._set_comp_bool("hdr_tonemap", value, "hdr_tonemap")

    @Property(str, notify=compressionConfigChanged)
    def compressionDeinterlace(self) -> str:
        return self._comp_settings.deinterlace

    @Slot(str)
    def setCompressionDeinterlace(self, value: str) -> None:
        self._set_comp_choice(
            "deinterlace", value, DEINTERLACE_MODES, "deinterlace"
        )

    @Property(str, notify=compressionConfigChanged)
    def compressionDenoise(self) -> str:
        return self._comp_settings.denoise

    @Slot(str)
    def setCompressionDenoise(self, value: str) -> None:
        self._set_comp_choice("denoise", value, DENOISE_MODES, "denoise")

    @Property(str, notify=compressionConfigChanged)
    def compressionAudioMode(self) -> str:
        return self._comp_settings.audio_mode

    @Slot(str)
    def setCompressionAudioMode(self, value: str) -> None:
        self._set_comp_choice("audio_mode", value, AUDIO_MODES, "audio_mode")

    @Property(str, notify=compressionConfigChanged)
    def compressionSubtitleMode(self) -> str:
        return self._comp_settings.subtitle_mode

    @Slot(str)
    def setCompressionSubtitleMode(self, value: str) -> None:
        self._set_comp_choice(
            "subtitle_mode", value, SUBTITLE_MODES, "subtitle_mode"
        )

    @Property(list, constant=True)
    def compressionPresets(self) -> list:
        return list(COMPRESSION_PRESETS)

    @Slot(str)
    def applyCompressionPreset(self, key: str) -> None:
        """Aplica um preset no estilo HandBrake aos ajustes atuais."""
        presets = {
            "fast_h264": {
                "encoder": "auto", "codec": "h264", "container": "mp4",
                "quality": 23, "speed": "fast", "ten_bit": False,
                "x265_tuning": False,
            },
            "balanced_hevc": {
                "encoder": "auto", "codec": "hevc", "container": "mp4",
                "quality": 24, "speed": "balanced", "ten_bit": False,
                "x265_tuning": False,
            },
            "quality_hevc": {
                "encoder": "auto", "codec": "hevc", "container": "mp4",
                "quality": 20, "speed": "slow", "ten_bit": False,
                "x265_tuning": True,
            },
            "archive_hevc": {
                "encoder": "software", "codec": "hevc", "container": "mkv",
                "quality": 18, "speed": "slower", "ten_bit": True,
                "x265_tuning": True,
            },
            "av1_balanced": {
                "encoder": "software", "codec": "av1", "container": "mkv",
                "quality": 30, "speed": "slow", "ten_bit": False,
                "x265_tuning": False,
            },
        }
        values = presets.get(key)
        if values is None:
            return
        # A preset must be a complete, predictable profile: reset filters and
        # stream policies before applying its codec/quality choices.
        defaults = {
            "hdr_tonemap": False,
            "skip_hdr": True,
            "deinterlace": "auto",
            "denoise": "off",
            "audio_mode": "auto",
            "subtitle_mode": "auto",
            "crop": "",
            "scale_width": 0,
            "scale_height": 0,
            "rotate": 0,
            "fps": 0.0,
        }
        for attr, value in defaults.items():
            setattr(self._comp_settings, attr, value)
        for attr, value in values.items():
            setattr(self._comp_settings, attr, value)
        self._comp_settings.preset = key
        for attr in (
            "encoder", "codec", "container", "quality", "speed",
            "ten_bit", "x265_tuning", "preset", "hdr_tonemap",
            "skip_hdr", "deinterlace", "denoise", "audio_mode",
            "subtitle_mode", "crop", "scale_width", "scale_height",
            "rotate", "fps",
        ):
            self._save(f"compress/{attr}", getattr(self._comp_settings, attr))
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()
        self.compressionEncodersChanged.emit()
        self.compressionEffectiveEncoderChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionParallel(self) -> int:
        return self._comp_settings.parallel

    @Slot(int)
    def setCompressionParallel(self, value: int) -> None:
        value = self._clamp(int(value), 1, 8)
        if value == self._comp_settings.parallel:
            return
        self._mark_comp_custom()
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
        self._mark_comp_custom()
        self._comp_settings.min_size_mb = value
        self._save("compress/min_size_mb", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    def _set_comp_bool(self, attr: str, value: bool, key: str) -> None:
        value = bool(value)
        if getattr(self._comp_settings, attr) == value:
            return
        self._mark_comp_custom()
        setattr(self._comp_settings, attr, value)
        self._save(f"compress/{key}", value)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    def _set_comp_choice(self, attr: str, value: str, allowed: tuple,
                         key: str) -> None:
        value = value if value in allowed else allowed[0]
        if getattr(self._comp_settings, attr) == value:
            return
        self._mark_comp_custom()
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
    def compressionHwDecode(self) -> bool:
        return self._comp_settings.hw_decode

    @Slot(bool)
    def setCompressionHwDecode(self, value: bool) -> None:
        self._set_comp_bool("hw_decode", value, "hw_decode")

    @Property(str, notify=compressionConfigChanged)
    def compressionCrop(self) -> str:
        return self._comp_settings.crop

    @Slot(str)
    def setCompressionCrop(self, value: str) -> None:
        value = (value or "").strip()
        if value == self._comp_settings.crop:
            return
        self._mark_comp_custom()
        self._comp_settings.crop = value
        self._save("compress/crop", value)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionScaleWidth(self) -> int:
        return int(self._comp_settings.scale_width)

    @Slot(int)
    def setCompressionScaleWidth(self, value: int) -> None:
        value = self._clamp(int(value), 0, 7680)
        if value == self._comp_settings.scale_width:
            return
        self._mark_comp_custom()
        self._comp_settings.scale_width = value
        self._save("compress/scale_width", value)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionScaleHeight(self) -> int:
        return int(self._comp_settings.scale_height)

    @Slot(int)
    def setCompressionScaleHeight(self, value: int) -> None:
        value = self._clamp(int(value), 0, 4320)
        if value == self._comp_settings.scale_height:
            return
        self._mark_comp_custom()
        self._comp_settings.scale_height = value
        self._save("compress/scale_height", value)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionRotate(self) -> int:
        return int(self._comp_settings.rotate)

    @Slot(int)
    def setCompressionRotate(self, value: int) -> None:
        value = int(value) if int(value) in (0, 90, 180, 270) else 0
        if value == self._comp_settings.rotate:
            return
        self._mark_comp_custom()
        self._comp_settings.rotate = value
        self._save("compress/rotate", value)
        self.compressionConfigChanged.emit()

    @Property(int, notify=compressionConfigChanged)
    def compressionFps(self) -> int:
        return int(round(float(self._comp_settings.fps or 0)))

    @Slot(int)
    def setCompressionFps(self, value: int) -> None:
        value = self._clamp(int(value), 0, 240)
        if value == int(round(float(self._comp_settings.fps or 0))):
            return
        self._mark_comp_custom()
        self._comp_settings.fps = float(value)
        self._save("compress/fps", value)
        self.compressionConfigChanged.emit()

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

    @Property(str, notify=compressionEffectiveEncoderChanged)
    def compressionEffectiveEncoder(self) -> str:
        """Encoder concreto que o modo Auto/fornecedor escolheria agora."""
        return resolve_encoder(self._comp_settings, self.compression.available)

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
        self._mark_comp_custom()
        self._comp_settings.qsv_device = index
        self._save("compress/qsv_device", index)
        self.compression.apply_settings(self._comp_settings)
        self.compressionConfigChanged.emit()

    @Slot()
    def refreshCompressionEncoders(self) -> None:
        """Refresh encoders off the GUI thread (ffmpeg/GPU probes are slow)."""
        if self._encoder_refresh_busy:
            return
        self._encoder_refresh_busy = True

        def work() -> None:
            try:
                self.compression.refresh_encoders()
            except Exception:
                logging.getLogger("hlsdl").exception("falha ao atualizar encoders")
            finally:
                self._encoder_refresh_busy = False
                self.compressionEncodersChanged.emit()
                self.compressionEffectiveEncoderChanged.emit()

        threading.Thread(target=work, daemon=True).start()

    @Property(bool, notify=compressionEncodersChanged)
    def compressionDetecting(self) -> bool:
        return not bool(self.compression.encoders_ready)

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
            details: list[str] = []
            for item in self.compression.items:
                status = item.get("status")
                if getattr(status, "value", status) != "error":
                    continue
                error = str(item.get("error") or "").strip()
                if not error:
                    continue
                name = item.get("name") or item.get("input") or ""
                details.append(f"â€¢ {name}: {error}")
            if details:
                message += "\n\n" + "\n".join(details[:3])
                if len(details) > 3:
                    message += f"\nâ€¦ (+{len(details) - 3})"
            show_message(
                None,
                QMessageBox.Icon.Warning,
                self._tr("compress_finished_title"),
                message,
                self._lang,
            )

    @Slot()
    def addCompressionFiles(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            None,
            self._tr("compress_add_files"),
            "",
            self._tr("filter_videos"),
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
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        if not self.compression.items:
            self.notifyText.emit(self._tr("compress_no_items"))
            return
        if not self.compression.encoders_ready:
            self.notifyText.emit(self._tr("compress_detecting"))
            self.refreshCompressionEncoders()
            return
        if not self.compression.start():
            reason = self.compression.last_error
            if reason in ("detecting", "detecting_gpu"):
                self.notifyText.emit(self._tr("compress_detecting"))
            elif reason == "no_encoder":
                self.notifyText.emit(
                    self._tr("compress_no_encoder", codec=self._comp_settings.codec.upper())
                )
            else:
                self.notifyText.emit(self._tr("compress_start_failed"))
            return
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

    @Slot(int)
    def retryCompressionItem(self, row: int) -> None:
        if self._deps_busy:
            self.notifyText.emit(self._tr("deps_busy_start"))
            return
        if self.compression.retryItem(row):
            self.notifyText.emit(self._tr("compress_retry_queued"))
        else:
            self.notifyText.emit(self._tr("compress_retry_wait"))


