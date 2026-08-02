import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from worker import DownloadWorker
from hls_test_server import HLSFixture

app = QApplication(sys.argv)
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")

# limpa saídas de execuções anteriores
for f in os.listdir(OUTDIR) if os.path.isdir(OUTDIR) else []:
    try:
        os.remove(os.path.join(OUTDIR, f))
    except OSError:
        pass

fixture = HLSFixture(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out"))
LOCAL_HLS = fixture.url()
print("HLS local:", LOCAL_HLS)


def run_worker(url, cancel_after=None, use_ffmpeg=True, direct_ffmpeg=False):
    """Roda um DownloadWorker em thread própria e coleta os eventos."""
    events = []
    done = {"flag": False}

    def on_prog(pct, sp, sz):
        events.append(("prog", round(pct, 1), sp, sz))

    def on_status(st):
        events.append(("status", st))

    def on_fail(url, err):
        events.append(("fail", err))

    def on_cancel(url):
        events.append(("cancel",))

    def on_success(url, path):
        events.append(("success", path))

    def on_finished():
        done["flag"] = True

    if direct_ffmpeg:
        # testa apenas o caminho _run_ffmpeg dentro de uma thread
        w = DownloadWorker(url, outdir=OUTDIR, use_ffmpeg_hls=True)
        t = QThread()
        w.moveToThread(t)

        def ffmpeg_job():
            ok, res = w._run_ffmpeg(url)
            (w.succeeded if ok else w.failed).emit(url, res)
            w.finished.emit()

        t.started.connect(ffmpeg_job)
        w.finished.connect(t.quit)
        w.failed.connect(lambda u, e: (events.append(("fail", e)), done.__setitem__("flag", True)))
        w.succeeded.connect(lambda u, p: (events.append(("success", p)), done.__setitem__("flag", True)))
        w.cancelled.connect(lambda u: (events.append(("cancel",)), done.__setitem__("flag", True)))
    else:
        w = DownloadWorker(url, outdir=OUTDIR, use_ffmpeg_hls=use_ffmpeg)
        t = QThread()
        w.moveToThread(t)
        t.started.connect(w.run)
        w.progressChanged.connect(on_prog)
        w.statusChanged.connect(on_status)
        w.failed.connect(on_fail)
        w.cancelled.connect(on_cancel)
        w.succeeded.connect(on_success)
        w.finished.connect(on_finished)
        w.finished.connect(t.quit)

    t.start()
    start = time.time()
    deadline = start + 90
    while not done["flag"]:
        app.processEvents()
        if cancel_after is not None and time.time() - start > cancel_after:
            w.cancel()
            cancel_after = None
        if time.time() > deadline:
            w.cancel()
            t.wait(3000)
            events.append(("timeout",))
            break
        time.sleep(0.02)
    t.wait(8000)
    for _ in range(30):
        app.processEvents()
        time.sleep(0.01)
    return events


print("=== Teste 1: URL inválida (fallback falha -> evento failed) ===")
events = run_worker("https://invalid-url-xyz-99999.com.br/")
fails = [e[1] for e in events if e[0] == "fail"]
assert fails, f"esperava failed, eventos={events}"
print("Erro:", fails[-1][:110], "...")
print("OK\n")

print("=== Teste 2: HLS local completo via yt-dlp (sucesso + progresso) ===")
events = run_worker(LOCAL_HLS)
progs = [e for e in events if e[0] == "prog"]
successes = [e for e in events if e[0] == "success"]
statuses = [e[1] for e in events if e[0] == "status"]
print("Statuses:", set(statuses))
print("Atualizações de progresso:", len(progs))
print("Sucessos:", successes)
assert successes, f"esperava sucesso, eventos={events}"
assert os.path.exists(successes[0][1]), "arquivo de saída não existe"
assert any(e[1] == 100.0 for e in progs), "esperava chegar a 100%"
assert "Baixando" in statuses, "esperava status Baixando"
print("Arquivo:", successes[0][1], f"({os.path.getsize(successes[0][1])} bytes)")
print("OK\n")

print("=== Teste 3: caminho ffmpeg direto (fallback final) ===")
events = run_worker(LOCAL_HLS, direct_ffmpeg=True)
successes = [e for e in events if e[0] == "success"]
fails = [e[1] for e in events if e[0] == "fail"]
print("Sucessos:", successes)
print("Falhas:", [f[:110] for f in fails])
assert successes, f"esperava sucesso do ffmpeg, eventos={events}"
assert os.path.exists(successes[0][1]) and os.path.getsize(successes[0][1]) > 1000
print("Arquivo ffmpeg:", successes[0][1], f"({os.path.getsize(successes[0][1])} bytes)")
print("OK\n")

print("=== Teste 4: scraper de HTML (fallback BS4) ===")
# Página cujo HTML embute o m3u8 em JSON-LD e em <source>.
page = os.path.join(fixture.hls_dir, "player.html")
with open(page, "w", encoding="utf-8") as f:
    f.write(
        '<html><head><script type="application/ld+json">'
        '{"video": {"contentUrl": "%s"}}</script></head>'
        '<body><video><source src="%s"></video></body></html>'
        % (fixture.url(), fixture.url())
    )
found = DownloadWorker(fixture.url("player.html"), OUTDIR)._find_media_in_html()
print("Stream encontrado pelo scraper:", found)
assert found == fixture.url(), f"scraper retornou {found}"
print("OK\n")

print("=== Teste 5: fluxo completo de uma página HTML com <source> ===")
events = run_worker(fixture.url("player.html"))
successes = [e for e in events if e[0] == "success"]
fails = [e[1] for e in events if e[0] == "fail"]
print("Sucessos:", [s[1] for s in successes])
print("Falhas:", [f[:120] for f in fails])
assert successes, f"esperava sucesso via página HTML, eventos={events}"
print("OK\n")

print("TODOS OS TESTES FUNCIONAIS PASSARAM")
fixture.close()
