import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine

from worker import extract_urls, DownloadModel, QueueManager, Status
from main import Bridge

# 1) extração de URLs
urls = extract_urls(
    "texto https://a.com/v1 mais https://b.com/p?q=1.\nhttps://c.com/m.m3u8"
)
assert urls == ["https://a.com/v1", "https://b.com/p?q=1", "https://c.com/m.m3u8"], urls
print("extract_urls OK ->", urls)

# 2) modelo + gerenciador + ponte
app = QApplication(sys.argv)
model = DownloadModel([])
manager = QueueManager(model, outdir=os.path.expanduser("~/Downloads/VideoDownloader"))
bridge = Bridge(manager, manager.outdir)

assert model.rowCount() == 0
added, skipped = manager.addText("https://x.com/1\nhttps://y.com/2\nnot-a-url")
assert added == 2 and skipped == 0 and model.rowCount() == 2, (added, skipped, model.rowCount())
assert model.data(model.index(0, 0), DownloadModel.STATUS) == Status.WAITING
assert model.data(model.index(0, 0), DownloadModel.URL) == "https://x.com/1"
print("model+manager OK ->", model.rowCount(), "itens")

# dedup: repetir links (com barra final/fragmento) nao duplica
a2, s2 = manager.addText("https://x.com/1/\nhttps://y.com/2#frag")
assert a2 == 0 and s2 == 2, (a2, s2)
a3, s3 = manager.addText("https://NOVO.com/video\nhttps://x.com/1")
assert a3 == 1 and s3 == 1, (a3, s3)
assert model.rowCount() == 3
print("dedup OK ->", a3, "adicionado,", s3, "ignorado")

# editar link (e reenfileirar) + bloquear duplicado
assert manager.editUrl(2, "https://editado.com/x")
assert model.data(model.index(2, 0), DownloadModel.URL) == "https://editado.com/x"
assert not manager.editUrl(2, "https://x.com/1")  # vira duplicado ativo
print("editUrl OK")

# cancelamento individual
manager.cancelItem(2)
assert model.data(model.index(2, 0), DownloadModel.STATUS) == Status.CANCELLED
print("cancelItem OK")

manager.setConcurrency(4)
assert manager._concurrency == 4
print("concurrency OK")

# 3) cookies: argumentos do yt-dlp montados corretamente
from worker import DownloadWorker
cases = [
    ("browser:chrome", ["--cookies-from-browser", "chrome"]),
    ("browser:Firefox", ["--cookies-from-browser", "firefox"]),
    ("file:nao_existe.txt", []),
    ("", []),
    ("algo estranho", []),
]
for cfg, expected in cases:
    w = DownloadWorker("https://x.com", "out", cookies=cfg)
    got = w._build_cookies_args()
    assert got == expected, (cfg, got, expected)
print("cookies args OK")

# 4) persistência (settings.ini temporário)
import tempfile
tmp = tempfile.mktemp(suffix=".ini")
b2 = Bridge(manager, manager.outdir, settings_path=tmp)
assert b2.dark is True
b2.setDark(False)
b2.setConcurrency(5)
b2.setLimitRateMB(7)
b2.setFragments(2)
b2.setCookiesEnabled(True)
b2.setCookiesBrowserIndex(3)  # firefox
b3 = Bridge(manager, manager.outdir, settings_path=tmp)
assert b3.dark is False, b3.dark
assert b3.concurrency == 5, b3.concurrency
assert b3.limitRateMB == 7, b3.limitRateMB
assert b3.fragments == 2, b3.fragments
assert b3._limit_rate_arg() == "7M"
b3.setLimitRateMB(0)
assert b3._limit_rate_arg() == ""
assert b3.cookiesEnabled is True
assert b3.cookiesBrowserIndex == 3
assert b3._build_cookies_arg() == "browser:firefox"
b3.setCookiesFile("C:/x/cookies.txt")
assert b3._build_cookies_arg() == "file:C:/x/cookies.txt"
os.remove(tmp)
print("persistência OK")

# 3) carrega a interface QML
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("downloadModel", model)
engine.rootContext().setContextProperty("bridge", bridge)
engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.qml")))
assert engine.rootObjects(), "ui.qml NAO carregou"
print("QML loaded OK ->", len(engine.rootObjects()), "root object(s)")

# 5) slots da ponte existem
for name in ("addLinks", "pasteFromClipboard", "importTxt", "chooseOutputFolder",
             "setConcurrency", "setLimitRateMB", "setFragments", "startQueue",
             "cancelAll", "clearFinished", "clearAll",
             "setDark", "setCookiesEnabled", "setCookiesBrowserIndex", "setCookiesFile",
             "chooseCookiesFile", "saveGeometry"):
    assert getattr(bridge, name), name
print("bridge slots OK")

QTimer.singleShot(300, app.quit)
app.exec()
print("SMOKE TEST OK")
