"""Repro: roda yt-dlp num stream real multi-formato e mostra TODAS as linhas
não-progresso, para ver qual padrão o worker perde. Usa --download-sections
para baixar só os primeiros 12s (rápido) mantendo o fluxo de merge real."""

import os
import re
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker import PROGRESS_RE, _which, USER_AGENT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith((".mp4", ".m4a", ".webm", ".mkv", ".part")):
        try:
            os.remove(os.path.join(OUT, f))
        except OSError:
            pass
tmpl = os.path.join(OUT, "%(title).120B [%(id)s].%(ext)s")

URLS = [
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8",
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8",
]

for url in URLS:
    print("=" * 80)
    print("URL:", url)
    cmd = [
        _which("yt-dlp"),
        "--newline", "--progress", "--no-playlist", "--no-mtime",
        "--windows-filenames", "--retries", "2", "--fragment-retries", "2",
        "--socket-timeout", "20",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--download-sections", "*0-12",
        "--force-overwrites",
        "--print", "after_move:filepath",
        "-o", tmpl,
        "--user-agent", USER_AGENT,
        url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    errs = []

    def drain():
        for line in proc.stderr:
            errs.append(line.rstrip())

    threading.Thread(target=drain, daemon=True).start()

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        if PROGRESS_RE.search(line):
            continue
        print("LINHA>", repr(line[:220]))

    rc = proc.wait()
    print("rc =", rc)
    print("stderr (ultimas 6):")
    for l in errs[-6:]:
        print("  ERR>", l[:220])
    print()
