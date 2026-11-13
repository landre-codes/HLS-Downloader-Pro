# ruff: noqa: F401, F403, F405
from PySide6.QtCore import Signal


class BridgeSignals:
    statsChanged = Signal(int, int, int, int, int)  # aguardando, baixando, ok, erro, cancelado
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
    compressionEffectiveEncoderChanged = Signal()
    compressionQsvDevicesChanged = Signal()
    updateChanged = Signal()
    updateProgressChanged = Signal(int)
    depsChanged = Signal()
    depsOutput = Signal(str)
    depsInstallFinished = Signal(str, bool, str)
    similarityChanged = Signal()
    recoveryChanged = Signal()


statsChanged = BridgeSignals.statsChanged
notifyText = BridgeSignals.notifyText
outputFolderChanged = BridgeSignals.outputFolderChanged
darkChanged = BridgeSignals.darkChanged
concurrencyChanged = BridgeSignals.concurrencyChanged
limitRateChanged = BridgeSignals.limitRateChanged
fragmentsChanged = BridgeSignals.fragmentsChanged
cookiesEnabledChanged = BridgeSignals.cookiesEnabledChanged
cookiesBrowserIndexChanged = BridgeSignals.cookiesBrowserIndexChanged
cookiesFileChanged = BridgeSignals.cookiesFileChanged
languageChanged = BridgeSignals.languageChanged
queueActiveChanged = BridgeSignals.queueActiveChanged
queuePausedChanged = BridgeSignals.queuePausedChanged
formatModeChanged = BridgeSignals.formatModeChanged
qualityChanged = BridgeSignals.qualityChanged
containerChanged = BridgeSignals.containerChanged
codecChanged = BridgeSignals.codecChanged
compressLevelChanged = BridgeSignals.compressLevelChanged
namingModeChanged = BridgeSignals.namingModeChanged
ytdlpVariantChanged = BridgeSignals.ytdlpVariantChanged
lastItemChanged = BridgeSignals.lastItemChanged
playlistChanged = BridgeSignals.playlistChanged
playlistLoadingChanged = BridgeSignals.playlistLoadingChanged
compressionStatsChanged = BridgeSignals.compressionStatsChanged
compressionStateChanged = BridgeSignals.compressionStateChanged
compressionConfigChanged = BridgeSignals.compressionConfigChanged
compressionEncodersChanged = BridgeSignals.compressionEncodersChanged
compressionEffectiveEncoderChanged = BridgeSignals.compressionEffectiveEncoderChanged
compressionQsvDevicesChanged = BridgeSignals.compressionQsvDevicesChanged
updateChanged = BridgeSignals.updateChanged
updateProgressChanged = BridgeSignals.updateProgressChanged
depsChanged = BridgeSignals.depsChanged
depsOutput = BridgeSignals.depsOutput
depsInstallFinished = BridgeSignals.depsInstallFinished
similarityChanged = BridgeSignals.similarityChanged
recoveryChanged = BridgeSignals.recoveryChanged

__all__ = ["BridgeSignals"] + ['statsChanged', 'notifyText', 'outputFolderChanged', 'darkChanged', 'concurrencyChanged', 'limitRateChanged', 'fragmentsChanged', 'cookiesEnabledChanged', 'cookiesBrowserIndexChanged', 'cookiesFileChanged', 'languageChanged', 'queueActiveChanged', 'queuePausedChanged', 'formatModeChanged', 'qualityChanged', 'containerChanged', 'codecChanged', 'compressLevelChanged', 'namingModeChanged', 'ytdlpVariantChanged', 'lastItemChanged', 'playlistChanged', 'playlistLoadingChanged', 'compressionStatsChanged', 'compressionStateChanged', 'compressionConfigChanged', 'compressionEncodersChanged', 'compressionEffectiveEncoderChanged', 'compressionQsvDevicesChanged', 'updateChanged', 'updateProgressChanged', 'depsChanged', 'depsOutput', 'depsInstallFinished', 'similarityChanged', 'recoveryChanged']

