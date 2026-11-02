"""E2E do fluxo .php: página php → yt-dlp bloqueia → scraper acha media.php
(m3u8) → yt-dlp bloqueia de novo → retry allow-unsafe-ext + .mp4 → sucesso.
Usa o mesmo padrão do integration_test (FastWorker)."""

import os
import shutil
import subprocess
import sys
import threading
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtWidgets import QApplication

import worker as worker_mod
from worker import DownloadModel, QueueManager, Status

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "php_test_out")

M3U8 = (
    "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:0\n"
    "#EXTINF:6.0,\nseg0.ts\n#EXTINF:6.0,\nseg1.ts\n#EXT-X-ENDLIST\n"
)
PAGE = (
    b'<html><body><video src="media.php?file=stream.m3u8"></video>'
    b'<a href="media.php?file=stream.m3u8">m3u8</a></body></html>'
)
SEG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "php_test_seg.ts")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/page.php":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path.startswith("/media.php"):
            body = M3U8.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/seg0.ts":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(os.path.getsize(SEG_FILE)))
            self.end_headers()
            with open(SEG_FILE, "rb") as fh:
                shutil.copyfileobj(fh, self.wfile)
        elif self.path == "/seg1.ts":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(os.path.getsize(SEG_FILE)))
            self.end_headers()
            with open(SEG_FILE, "rb") as fh:
                shutil.copyfileobj(fh, self.wfile)
        else:
            self.send_response(404)
            self.end_headers()


class FastWorker(worker_mod.DownloadWorker):
    def _run_process(self, cmd, **kw):
        cmd = list(cmd)
        if "-o" in cmd and "--compat-options" not in cmd:
            idx = cmd.index("-o")
            cmd[idx:idx] = ["--download-sections", "*0-12", "--force-overwrites"]
        return super()._run_process(cmd, **kw)


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg não encontrado — abortando")
        return 1
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "testsrc=duration=1:size=160x90:rate=10",
         "-an", "-f", "mpegts", SEG_FILE],
        check=True,
    )
    shutil.rmtree(OUTDIR, ignore_errors=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    worker_mod.DownloadWorker = FastWorker  # (compat) mantido para clareza
    app = QApplication(sys.argv)
    model = DownloadModel([])
    mgr = QueueManager(model, outdir=OUTDIR, worker_factory=FastWorker)
    mgr.addText(f"{base}/page.php")
    mgr.start()
    print("fila iniciada,", len(mgr.items), "itens")

    deadline = time.time() + 240
    while any(it["status"] not in Status.FINAL for it in mgr.items) and time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)

    it = mgr.items[0]
    print("STATUS:", it["status"])
    if it.get("error"):
        print("ERRO:", it["error"][:400])
    print("PATH:", it.get("path"))
    print("EXISTE:", bool(it.get("path")) and os.path.exists(it["path"]))
    files = [f for f in os.listdir(OUTDIR) if not f.endswith(".part")]
    print("ARQUIVOS:", files)
    for f in files:
        p = os.path.join(OUTDIR, f)
        with open(p, "rb") as fh:
            head = fh.read(40)
        print("HEAD:", f, "size:", os.path.getsize(p), "head:", head, flush=True)

    srv.shutdown()
    ok = it["status"] == Status.DONE and bool(it.get("path")) and os.path.exists(it["path"])
    print("PHP FLUXO", "OK" if ok else "FALHOU")
    shutil.rmtree(OUTDIR, ignore_errors=True)
    os.remove(SEG_FILE)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
