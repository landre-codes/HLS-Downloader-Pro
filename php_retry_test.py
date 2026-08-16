"""Valida o retry: yt-dlp com --compat-options allow-unsafe-ext + -o ...mp4
consegue baixar uma URL .php (o fallback do app)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2" + b"\x00" * 64


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/video.php":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(MP4)))
            self.end_headers()
            self.wfile.write(MP4)
        else:
            self.send_response(404)
            self.end_headers()


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    outdir = os.path.abspath("php_test_out")
    os.makedirs(outdir, exist_ok=True)

    cmd = [
        "yt-dlp", "--newline", "--no-playlist", "--no-mtime", "--no-overwrites",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "--compat-options", "allow-unsafe-ext",
        "-o", os.path.join(outdir, "%(title)s [%(id)s].mp4"),
        "--print", "after_move:filepath",
        f"{base}/video.php",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    print("rc:", r.returncode, flush=True)
    tail = (r.stderr or "").strip().splitlines()[-3:]
    print("stderr:", tail, flush=True)
    out = r.stdout.strip().splitlines()
    print("stdout final:", out[-2:] if out else "(vazio)", flush=True)
    print("ARQUIVOS:", os.listdir(outdir), flush=True)
    srv.shutdown()
    sys.exit(0 if r.returncode == 0 and os.listdir(outdir) else 1)


if __name__ == "__main__":
    main()
