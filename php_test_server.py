"""Servidor local de teste: /video.php (MP4 real) e /page.php (HTML com m3u8).

Para reproduzir o caso "extensão php incomum" do yt-dlp 2026+.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:6.0,
seg0.ts
#EXTINF:6.0,
seg1.ts
#EXT-X-ENDLIST
"""

SEG0 = b"\x47\x00\x00\x00" + b"A" * 1024
SEG1 = b"\x47\x00\x00\x00" + b"B" * 1024


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/page.php":
            body = (
                b"<html><body><video src=\"/media.php?file=stream.m3u8\"></video>"
                b"<a href=\"/media.php?file=stream.m3u8\">m3u8</a></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
        elif self.path == "/video.php":
            # MP4 mínimo (ftyp + moov vazio) — suficiente para o teste de
            # aceitação de extensão; não precisa ser decodificável.
            mp4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isomiso2"
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(mp4)))
            self.end_headers()
            self.wfile.write(mp4)
        else:
            self.send_response(404)
            self.end_headers()


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    print(f"SERVIDOR em {base}", flush=True)

    outdir = os.path.abspath("php_test_out")
    os.makedirs(outdir, exist_ok=True)

    # Teste 1: yt-dlp direto numa URL terminada em .php
    print("\n--- TESTE 1: yt-dlp em /video.php ---", flush=True)
    cmd = [
        "yt-dlp", "--newline", "--no-playlist", "--no-mtime", "--no-overwrites",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "-o", os.path.join(outdir, "%(title)s [%(id)s].%(ext)s"),
        "--print", "after_move:filepath",
        f"{base}/video.php",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    tail = (r.stderr or "").strip().splitlines()[-2:]
    print("rc:", r.returncode, flush=True)
    print("stderr:", tail, flush=True)

    # Teste 2: yt-dlp na URL .php com outtmpl forçando .mp4
    print("\n--- TESTE 2: yt-dlp em /video.php com -o ....mp4 ---", flush=True)
    cmd2 = [
        "yt-dlp", "--newline", "--no-playlist", "--no-mtime", "--no-overwrites",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "-o", os.path.join(outdir, "%(title)s [%(id)s].mp4"),
        "--print", "after_move:filepath",
        f"{base}/video.php",
    ]
    r2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    tail2 = (r2.stderr or "").strip().splitlines()[-2:]
    print("rc:", r2.returncode, flush=True)
    print("stderr:", tail2, flush=True)

    # Teste 3: URL .php que é uma PÁGINA HTML com m3u8 — fluxo do scraper
    print("\n--- TESTE 3: yt-dlp em /page.php (HTML) ---", flush=True)
    cmd3 = [
        "yt-dlp", "--newline", "--no-playlist", "--no-mtime", "--no-overwrites",
        "-f", "b", "-o", os.path.join(outdir, "%(title)s [%(id)s].%(ext)s"),
        "--print", "after_move:filepath",
        f"{base}/page.php",
    ]
    r3 = subprocess.run(cmd3, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    tail3 = (r3.stderr or "").strip().splitlines()[-2:]
    print("rc:", r3.returncode, flush=True)
    print("stderr:", tail3, flush=True)

    srv.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
