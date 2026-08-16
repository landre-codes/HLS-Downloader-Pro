"""Testa o retry em m3u8 servido via .php SEM a injeção do FastWorker
(--download-sections) — cenário idêntico ao da produção."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

M3U8 = (
    "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:0\n"
    "#EXTINF:6.0,\nseg0.ts\n#EXTINF:6.0,\nseg1.ts\n#EXT-X-ENDLIST\n"
)
SEG0 = b"\x47\x00\x00\x00" + b"A" * 1024
SEG1 = b"\x47\x00\x00\x00" + b"B" * 1024
PAGE = (
    '<html><body><video src="media.php?file=stream.m3u8"></video>'
    '<a href="media.php?file=stream.m3u8">m3u8</a></body></html>'
).encode()


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
            self.send_header("Content-Length", str(len(SEG0)))
            self.end_headers()
            self.wfile.write(SEG0)
        elif self.path == "/seg1.ts":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp2t")
            self.send_header("Content-Length", str(len(SEG1)))
            self.end_headers()
            self.wfile.write(SEG1)
        else:
            self.send_response(404)
            self.end_headers()


def main() -> int:
    import shutil

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    outdir = os.path.abspath("php_test_out")
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)

    # Fluxo do app: candidato raspado = media.php?file=stream.m3u8
    cmd = [
        "yt-dlp", "--newline", "--no-playlist", "--no-mtime", "--no-overwrites",
        "--retries", "3", "--fragment-retries", "5", "--socket-timeout", "20",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "--print", "after_move:filepath",
        "-o", os.path.join(outdir, "%(title)s [%(id)s].mp4"),
        "--compat-options", "allow-unsafe-ext",
        "--add-header", f"Referer:{base}/page.php",
        f"{base}/media.php?file=stream.m3u8",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    print("rc:", r.returncode, flush=True)
    tail = (r.stderr or "").strip().splitlines()[-6:]
    print("stderr:", tail, flush=True)
    print("stdout final:", r.stdout.strip().splitlines()[-2:] or "(vazio)", flush=True)
    print("ARQUIVOS:", os.listdir(outdir), flush=True)
    srv.shutdown()
    ok = r.returncode == 0 and any(f.endswith(".mp4") for f in os.listdir(outdir))
    shutil.rmtree(outdir, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
