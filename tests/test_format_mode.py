"""Testes do modo de extração (vídeo+áudio / só vídeo / só áudio)."""

from __future__ import annotations

import os

from hlsdl.bridge import Bridge
from hlsdl.downloader import DownloadWorker
from hlsdl.model import DownloadModel
from hlsdl.queue import FORMAT_MODES, QueueManager


def _worker(mode: str) -> DownloadWorker:
    return DownloadWorker("https://x.com/v", "out", format_mode=mode)


def test_format_args_video_audio():
    args = _worker("video_audio")._format_args()
    assert "bv*+ba/b" in args and "--merge-output-format" in args


def test_format_args_video_only():
    args = _worker("video_only")._format_args()
    # Não pode cair no formato combinado /b (que traz áudio).
    assert "bv*" in args and "+ba" not in " ".join(args) and "-x" not in args


def test_format_args_audio_only():
    args = _worker("audio_only")._format_args()
    assert "-x" in args and "mp3" in args and "bv*+ba/b" not in args


def test_format_modes_constant():
    assert FORMAT_MODES == ("video_audio", "video_only", "audio_only")


def test_quality_limits_height():
    w = DownloadWorker("https://x.com/v", "out", format_mode="video_audio",
                       quality="720", container="mkv")
    args = w._format_args()
    joined = " ".join(args)
    assert "height<=720" in joined
    # O fallback também precisa respeitar a altura escolhida.
    selector = args[args.index("-f") + 1]
    assert selector.count("height<=720") == 2
    assert "mkv" in args


def test_quality_limits_video_only_fallback():
    w = DownloadWorker("https://x.com/v", "out", format_mode="video_only",
                       quality="720")
    args = w._format_args()
    assert args[args.index("-f") + 1] == "bv*[height<=720]"


def test_quality_best_has_no_height_filter():
    w = DownloadWorker("https://x.com/v", "out", quality="best")
    assert "height<=" not in " ".join(w._format_args())


def test_audio_only_defaults_to_mp3_container():
    w = DownloadWorker("https://x.com/v", "out", format_mode="audio_only")
    assert "mp3" in w._format_args()


def test_bridge_quality_and_container_persist(qapp, tmp_path, fake_deps):
    settings = str(tmp_path / "s.ini")
    b = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
               settings_path=settings, deps=fake_deps)
    b.setQuality("1080")
    b.setContainer("mkv")
    b2 = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
                settings_path=settings, deps=fake_deps)
    assert b2.quality == "1080"
    assert b2.container == "mkv"


def test_switching_to_audio_adjusts_container(qapp, tmp_path, fake_deps):
    b = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
               settings_path=str(tmp_path / "s.ini"), deps=fake_deps)
    b.setContainer("mkv")
    b.setFormatMode("audio_only")
    assert b.container in ("mp3", "m4a", "wav", "flac", "opus")


# ---------------------------------------------------------------- nome do arquivo
def test_naming_mode_id_template():
    w = DownloadWorker("https://x.com/v", "out", naming_mode="id")
    base, template = w._output_template("https://x.com/v")
    assert base.startswith("vid_") and base in template
    assert "%(title)" not in template


def test_naming_mode_title_template():
    w = DownloadWorker("https://x.com/v", "out", naming_mode="title")
    _, template = w._output_template("https://x.com/v")
    assert "%(title)" in template
    # ID evita colisão entre vídeos diferentes com o mesmo título.
    assert "%(id)s" in template


# ---------------------------------------------------------------- compressão
def test_compress_noop_when_copy(tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    w = DownloadWorker("https://x.com/v", "out")
    assert w._maybe_compress(str(src)) == str(src)


def test_compress_runs_ffmpeg_h264(monkeypatch, tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"orig")
    w = DownloadWorker("https://x.com/v", "out", codec="h264",
                       compress_level="strong", container="mp4")
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda p: 10.0)
    monkeypatch.setattr(
        "hlsdl.downloader.probe_media",
        lambda p: {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
                {"codec_type": "subtitle", "codec_name": "subrip"},
            ],
            "format": {"duration": "1"},
        },
    )
    captured = {}

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        captured["cmd"] = list(cmd)
        with open(cmd[-1], "wb") as fh:
            fh.write(b"compressed")
        return True, cmd[-1]

    monkeypatch.setattr(w, "_run_process", fake_run)
    out = w._maybe_compress(str(src))
    assert out is not None and out.endswith("_h264.mp4")
    assert os.path.exists(out)
    assert src.exists()  # original preservado (sem perda de dados)
    cmd = captured["cmd"]
    assert "libx264" in cmd
    assert "-crf" in cmd and "28" in cmd
    # Todas as trilhas relevantes devem ser mapeadas, não só a padrão.
    assert "-map" in cmd and "0:a?" in cmd and "0:s:0" in cmd


def test_compress_keeps_original_on_failure(monkeypatch, tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"orig")
    w = DownloadWorker("https://x.com/v", "out", codec="h265", container="mkv")
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda p: 10.0)
    monkeypatch.setattr(w, "_run_process", lambda *a, **k: (False, "erro"))
    out = w._maybe_compress(str(src))
    assert out == str(src)
    assert src.exists()


def test_compress_cancelled_returns_none(monkeypatch, tmp_path):
    src = tmp_path / "a.mp4"
    src.write_bytes(b"orig")
    w = DownloadWorker("https://x.com/v", "out", codec="h264")
    monkeypatch.setattr("hlsdl.downloader.which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr("hlsdl.downloader.probe_duration", lambda p: 10.0)

    def fake_run(cmd, duration=None, is_ffmpeg=False):
        w._cancel = True
        return False, "cancelado"

    monkeypatch.setattr(w, "_run_process", fake_run)
    assert w._maybe_compress(str(src)) is None


def test_bridge_persists_codec_and_naming(qapp, tmp_path, fake_deps):
    settings = str(tmp_path / "s.ini")
    b = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
               settings_path=settings, deps=fake_deps)
    b.setCodec("h265")
    b.setCompressLevel("strong")
    b.setNamingMode("title")
    b2 = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
                settings_path=settings, deps=fake_deps)
    assert b2.codec == "h265"
    assert b2.compressLevel == "strong"
    assert b2.namingMode == "title"



def test_queue_clamps_format_mode(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    manager.setFormatMode("invalido")
    assert manager._format_mode == "video_audio"
    manager.setFormatMode("audio_only")
    assert manager._format_mode == "audio_only"


def test_bridge_persists_format_mode(qapp, tmp_path, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    settings = str(tmp_path / "s.ini")
    b = Bridge(manager, "out", settings_path=settings, deps=fake_deps)
    b.setFormatMode("audio_only")
    assert manager._format_mode == "audio_only"
    b2 = Bridge(QueueManager(DownloadModel([]), outdir="out"), "out",
                settings_path=settings, deps=fake_deps)
    assert b2.formatMode == "audio_only"


def test_bridge_last_item_scoped_to_single(qapp, tmp_path, fake_deps):
    class DoneWorker(DownloadWorker):
        def run(self) -> None:  # type: ignore[override]
            self.progressChanged.emit(100.0, "—", "—")
            self._succeed("/nope/fake.mp4")

    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", worker_factory=DoneWorker)
    bridge = Bridge(manager, "out", settings_path=str(tmp_path / "s.ini"), deps=fake_deps)

    # Item adicionado pelo lote NÃO deve aparecer na aba Individual.
    manager.addText("https://batch/1")
    assert bridge.lastItem == {}

    # Já o download individual deve aparecer.
    bridge.downloadSingle("https://single/1")
    assert bridge.lastItem["url"] == "https://single/1"
    bridge.shutdown()


def test_queue_pause_resume_state(qapp):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", worker_factory=_NoopWorker)
    states: list = []
    manager.queueStateChanged.connect(lambda active, paused: states.append((active, paused)))

    manager.addText("https://x/1")
    manager.start()
    manager.pause()
    assert manager.isPaused is True
    manager.resume()
    assert manager.isPaused is False
    assert states, "queueStateChanged deveria ter sido emitido"
    manager.shutdown(timeout=3)


def test_queue_becomes_idle_after_finish(qapp):
    from tests.conftest import process_until

    class DoneWorker(DownloadWorker):
        def run(self) -> None:  # type: ignore[override]
            self.progressChanged.emit(100.0, "—", "—")
            self._succeed("/nope/x.mp4")

    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", concurrency=1, worker_factory=DoneWorker)
    manager.addText("https://x/1")
    manager.start()
    assert process_until(
        qapp, lambda: all(i["status"].is_final for i in manager.items), timeout=15
    )
    assert process_until(qapp, lambda: manager.isActive is False, timeout=8)


def test_download_single_adds_and_starts(qapp, tmp_path, fake_deps):
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", worker_factory=_NoopWorker)
    manager.addText("https://lote/1")
    bridge = Bridge(manager, "out", settings_path=str(tmp_path / "s.ini"), deps=fake_deps)
    bridge.setFormatMode("audio_only")
    assert bridge.downloadSingle("https://x.com/v") is True
    # A fila individual é separada do lote: o item do lote continua parado.
    assert model.rowCount() == 1
    assert manager.items[0]["url"] == "https://lote/1"
    assert manager.items[0]["status"].value == "waiting"
    assert bridge.single_manager.items[0]["url"] == "https://x.com/v"
    assert bridge.single_manager.isActive is True
    assert bridge.downloadSingle("isto-nao-e-url") is False
    assert len(bridge.single_manager.items) == 1
    bridge.shutdown()


class _NoopWorker(DownloadWorker):
    """Não baixa nada: apenas registra que foi criado."""

    def run(self) -> None:  # type: ignore[override]
        self.statusChanged.emit("analyzing")
        self.finished.emit()


def test_queue_passes_format_mode_to_worker(qapp):
    captured = {}

    def factory(**kw):
        captured.update(kw)
        return _NoopWorker(**kw)

    model = DownloadModel([])
    manager = QueueManager(model, outdir="out", worker_factory=factory)
    manager.setFormatMode("video_only")
    manager.addText("https://x.com/v")
    manager.start()
    from tests.conftest import process_until

    process_until(qapp, lambda: "format_mode" in captured, timeout=10)
    assert captured.get("format_mode") == "video_only"
    manager.shutdown(timeout=3)

