"""Smoke test do backend + carregamento do QML (sem aba de interface).

Rápido, offscreen e sem rede. A suíte completa de testes vive em ``tests/``
(``python -m pytest``).
"""

import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.deps import DependencyManager
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from hlsdl.status import Status
from hlsdl.urlutils import extract_urls

# 1) extração de URLs
urls = extract_urls("texto https://a.com/v1 mais https://b.com/p?q=1.\nhttps://c.com/m.m3u8")
assert urls == ["https://a.com/v1", "https://b.com/p?q=1", "https://c.com/m.m3u8"], urls
print("extract_urls OK ->", urls)

# 2) modelo + gerenciador (lista compartilhada)
app = QApplication(sys.argv)
model = DownloadModel([])
manager = QueueManager(model, outdir=os.path.expanduser("~/Downloads/VideoDownloader"))
bridge = Bridge(manager, manager.outdir)

assert model.rowCount() == 0
added, skipped = manager.addText("https://x.com/1\nhttps://y.com/2\nnot-a-url")
assert added == 2 and skipped == 0 and model.rowCount() == 2, (added, skipped, model.rowCount())
assert model.data(model.index(0, 0), DownloadModel.STATUS) == "waiting"
assert manager.items is model.items(), "modelo e fila devem compartilhar a lista"
print("model+manager OK ->", model.rowCount(), "itens (lista compartilhada)")

# dedup
a2, s2 = manager.addText("https://x.com/1/\nhttps://y.com/2#frag")
assert a2 == 0 and s2 == 2, (a2, s2)
print("dedup OK")

# regressão: clearFinished mantém modelo e fila sincronizados
manager.items[0]["status"] = Status.DONE
manager.clearFinished()
assert model.rowCount() == 1 and len(manager.items) == 1
assert model.data(model.index(0, 0), DownloadModel.URL) == "https://y.com/2"
print("clearFinished sincronizado OK")

# 3) cookies
from hlsdl.downloader import DownloadWorker

cases = [
    ("browser:chrome", ["--cookies-from-browser", "chrome"]),
    ("browser:Firefox", ["--cookies-from-browser", "firefox"]),
    ("file:nao_existe.txt", []),
    ("", []),
    ("algo estranho", []),
]
for cfg, expected in cases:
    w = DownloadWorker("https://x.com", "out", cookies=cfg)
    assert w._build_cookies_args() == expected, (cfg, w._build_cookies_args(), expected)
print("cookies args OK")

# 4) persistência (settings.ini temporário)
tmp = tempfile.mktemp(suffix=".ini")
b2 = Bridge(manager, manager.outdir, settings_path=tmp)
b2.setDark(False)
b2.setConcurrency(5)
b2.setLimitRateMB(7)
b2.setFragments(2)
b2.setCookiesEnabled(True)
b2.setCookiesBrowserIndex(3)  # firefox
b3 = Bridge(manager, manager.outdir, settings_path=tmp)
assert b3.dark is False and b3.concurrency == 5 and b3.limitRateMB == 7
assert b3.fragments == 2 and b3._build_cookies_arg() == "browser:firefox"
os.remove(tmp)
print("persistência OK")

# 5) dependências detectadas
deps = DependencyManager().check_all()
assert any(d["key"] == "pyside6" and d["found"] for d in deps)
print("dependências OK ->", [(d["key"], d["found"]) for d in deps])

# 6) carrega a interface QML
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("downloadModel", model)
engine.rootContext().setContextProperty("compressionModel", bridge.compression.model)
engine.rootContext().setContextProperty("bridge", bridge)
engine.load(QUrl.fromLocalFile(qml_path()))
assert engine.rootObjects(), "main.qml NAO carregou"
print("QML loaded OK ->", len(engine.rootObjects()), "root object(s)")

# 7) slots da ponte existem
for name in (
    "addLinks", "pasteFromClipboard", "importTxt", "importTxtPath", "chooseOutputFolder",
    "setConcurrency", "setLimitRateMB", "setFragments", "startQueue", "pauseQueue",
    "resumeQueue", "cancelAll", "cancelItem", "removeItem", "retryItem", "clearFinished",
    "clearAll", "setDark", "setCookiesEnabled", "setCookiesBrowserIndex", "setCookiesFile",
    "chooseCookiesFile", "saveGeometry", "refreshDependencies", "installDependency",
    "installMissingDependencies", "downloadSingle", "setFormatMode", "setQuality",
    "setContainer", "setCodec", "setCompressLevel", "setNamingMode",
    "setYtdlpVariant", "loadPlaylist", "clearPlaylist", "addLinksAndStart",
    "addCompressionFiles", "addCompressionFolder", "addCompressionPaths",
    "startCompression", "pauseCompression", "resumeCompression", "cancelCompression",
    "cancelCompressionItem", "removeCompressionItem", "clearCompressionFinished",
    "setCompressionEncoder", "setCompressionCodec", "setCompressionContainer",
    "setCompressionQuality", "setCompressionSpeed",
    "setCompressionParallel", "setCompressionMinSizeMB",
    "setCompressionOnlyIfSmaller", "setCompressionReplaceOriginal",
    "setCompressionReencodeHevc", "setCompressionSkipHdr",
    "setCompressionTenBit", "setCompressionX265Tuning",
    "setCompressionQsvDevice", "refreshCompressionEncoders",
    "checkForUpdates", "downloadUpdate", "openReleasePage",
):
    assert getattr(bridge, name), name
print("bridge slots OK")

QTimer.singleShot(300, app.quit)
app.exec()
print("SMOKE TEST OK")
