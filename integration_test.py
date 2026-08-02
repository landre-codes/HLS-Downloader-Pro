"""Integração: exatamente o que o app faz (QueueManager) com streams reais,
usando um worker que limita o download a 12s. Mostra o estado final de cada
item da tabela (status, erro, arquivo)."""

import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

import worker as worker_mod
from worker import DownloadModel, DownloadWorker, QueueManager, Status

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")


class FastWorker(DownloadWorker):
    """Igual ao worker real, mas baixa só 12s para o teste ser rápido."""

    def _run_process(self, cmd, **kw):
        cmd = list(cmd)
        idx = cmd.index("-o")
        cmd[idx:idx] = ["--download-sections", "*0-12", "--force-overwrites"]
        return super()._run_process(cmd, **kw)


worker_mod.DownloadWorker = FastWorker

app = QApplication(sys.argv)
model = DownloadModel([])
mgr = QueueManager(model, outdir=OUTDIR)

URLS = [
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8",
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8",
]
for u in URLS:
    mgr.addText(u)

mgr.start()
print("fila iniciada,", len(mgr.items), "itens")

deadline = time.time() + 240
while any(it["status"] not in Status.FINAL for it in mgr.items) and time.time() < deadline:
    app.processEvents()
    time.sleep(0.02)

for it in mgr.items:
    print("=" * 70)
    print("URL:", it["url"])
    print("STATUS:", it["status"])
    if it.get("error"):
        print("ERRO:", it["error"][:300])
    path = it.get("path")
    print("PATH:", path)
    print("EXISTE:", bool(path) and os.path.exists(path))

fails = [it for it in mgr.items if it["status"] == Status.ERROR]
print("=" * 70)
if fails:
    print("FALHOU: itens em erro:", len(fails))
    sys.exit(1)
print("INTEGRACAO OK")
