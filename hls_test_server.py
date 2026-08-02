"""
hls_test_server.py
==================
Gera um HLS minúsculo (4s) com ffmpeg e o serve via HTTP local, para que os
testes funcionais sejam rápidos, determinísticos e não dependam da internet.
"""

import http.server
import os
import shutil
import socketserver
import subprocess
import threading


def _which(name: str):
    for exe in (name, name + ".exe"):
        found = shutil.which(exe)
        if found:
            return found
    return None


class HLSFixture:
    """Gera um .m3u8 de 4 segundos e o expõe em http://127.0.0.1:<porta>/"""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.hls_dir = os.path.join(base_dir, "hls")
        self._ensure_hls()
        self._httpd = None
        self.port = None
        self._start_server()

    # ------------------------------------------------------------ setup HLS
    def _ensure_hls(self) -> None:
        ffmpeg = _which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg não encontrado para os testes")

        os.makedirs(self.hls_dir, exist_ok=True)
        manifest = os.path.join(self.hls_dir, "out.m3u8")
        if os.path.exists(manifest) and os.path.getsize(manifest) > 0:
            return

        # 1) vídeo de teste de 4 segundos
        src = os.path.join(self.hls_dir, "src.mp4")
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=size=320x180:rate=24",
                "-t", "4", "-c:v", "libx264", "-preset", "veryfast",
                "-pix_fmt", "yuv420p", src,
            ],
            check=True,
        )

        # 2) segmenta em HLS (1s por segmento -> 4 segmentos)
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-i", src,
                "-c:v", "libx264", "-preset", "veryfast",
                "-hls_time", "1", "-hls_list_size", "0",
                "-f", "hls", manifest,
            ],
            check=True,
        )
        try:
            os.remove(src)
        except OSError:
            pass

    # ------------------------------------------------------------ servidor HTTP
    def _start_server(self) -> None:
        directory = self.hls_dir

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

            def log_message(self, *args):
                pass

        self._httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), QuietHandler)
        self.port = self._httpd.server_address[1]
        t = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        t.start()

    def url(self, name: str = "out.m3u8") -> str:
        return f"http://127.0.0.1:{self.port}/{name}"

    def close(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
