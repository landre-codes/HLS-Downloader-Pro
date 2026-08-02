"""Verificação ponta a ponta do caso do usuário: stream real multi-formato
onde yt-dlp NÃO imprime `[download] Destination:` (visto no repro_real.py),
com DownloadWorker real — o item deve terminar como sucesso."""

import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from worker import DownloadWorker

app = QApplication(sys.argv)
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")


class FastWorker(DownloadWorker):
    """Igual ao worker real, mas limita o download a 12s para o teste."""

    def _run_process(self, cmd, **kw):
        cmd = list(cmd)
        idx = cmd.index("-o")
        cmd[idx:idx] = ["--download-sections", "*0-12", "--force-overwrites"]
        return super()._run_process(cmd, **kw)


URL = "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8"

events = []
done = {"flag": False}

w = FastWorker(URL, outdir=OUTDIR, use_ffmpeg_hls=True)
t = QThread()
w.moveToThread(t)
t.started.connect(w.run)
w.succeeded.connect(lambda u, p: (events.append(("success", p)), done.__setitem__("flag", True)))
w.failed.connect(lambda u, e: (events.append(("fail", e)), done.__setitem__("flag", True)))
w.progressChanged.connect(lambda pct, sp, sz: events.append(("prog", pct)))
w.statusChanged.connect(lambda st: events.append(("status", st)))
w.finished.connect(t.quit)
w.finished.connect(lambda: done.__setitem__("flag", True))

t.start()
deadline = time.time() + 180
while not done["flag"] and time.time() < deadline:
    app.processEvents()
    time.sleep(0.02)
t.wait(10000)

print("EVENTOS:")
for e in events:
    print("  ", e)
assert any(e[0] == "success" for e in events), "FALHOU: esperava success!"
succ = [e[1] for e in events if e[0] == "success"][0]
assert os.path.exists(succ), f"arquivo não existe: {succ}"
print("ARQUIVO:", succ, os.path.getsize(succ), "bytes")
print("PONTA A PONTA OK")
