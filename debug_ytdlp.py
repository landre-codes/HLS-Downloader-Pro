import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker import PROGRESS_RE, USER_AGENT, _which

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")
os.makedirs(OUT, exist_ok=True)
tmpl = os.path.join(OUT, "%(title).120B [%(id)s].%(ext)s")

cmd = [
    _which("yt-dlp"),
    "--newline", "--progress", "--no-playlist", "--no-mtime",
    "--windows-filenames", "--retries", "3", "--fragment-retries", "5",
    "--socket-timeout", "20",
    "-f", "bestvideo+bestaudio/best",
    "--merge-output-format", "mp4",
    "-o", tmpl,
    "--user-agent", USER_AGENT,
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8",
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, encoding="utf-8", errors="replace", bufsize=1)

stderr_lines = []
def drain():
    for line in proc.stderr:
        stderr_lines.append(line.rstrip())
import threading

threading.Thread(target=drain, daemon=True).start()

matched_prog = 0
matched_dest = 0
other = 0
out_path = None
first_lines = []
other_sample = []
for line in proc.stdout:
    line = line.strip()
    if not line:
        continue
    m = PROGRESS_RE.search(line)
    if m:
        matched_prog += 1
        if matched_prog <= 3 or matched_prog % 50 == 0:
            print("PROG:", m.groups())
        continue
    dm = re.search(r"\[download\] Destination: (.+)", line)
    if dm:
        matched_dest += 1
        out_path = dm.group(1).strip()
        print("DEST:", out_path)
        continue
    other += 1
    if len(first_lines) < 8:
        first_lines.append(line)
    if len(other_sample) < 8:
        other_sample.append(line)

rc = proc.wait()
print("rc =", rc)
print("linhas progresso:", matched_prog, "| dest:", matched_dest, "| outras:", other)
print("out_path existe?", out_path and os.path.exists(out_path))
print("stderr_lines:", len(stderr_lines))
for line in stderr_lines[-5:]:
    print("ERR>", line[:200])
print("=== as linhas 'outras' ===")
for line in first_lines:
    print("OUT>", repr(line[:200]))
print("=== amostra das linhas 'outras' posteriores ===")
for line in other_sample:
    print("SMP>", repr(line[:200]))
