"""Gerenciador da fila: escala workers, limita concorrência e mantém o modelo.

O gerente opera sobre a MESMA lista de itens do :class:`DownloadModel`
(``model.items()``), eliminando a dessincronização que existia quando remoções
afetavam apenas uma das duas listas.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot

from .downloader import DownloadWorker
from .formats import FORMAT_MODES
from .i18n import translator
from .model import DownloadModel, make_item
from .status import ACTIVE, FINAL, Status
from .urlutils import extract_urls, normalize_url

log = logging.getLogger("hlsdl")

WorkerFactory = Callable[..., DownloadWorker]


class QueueManager(QObject):
    """Coordena a fila: um worker+thread por item ativo, com limite."""

    statsChanged = Signal(int, int, int, int)  # aguardando, baixando, ok, erro
    outdirChanged = Signal(str)
    itemUpdated = Signal(object)  # um item da fila mudou (dict)
    queueStateChanged = Signal(bool, bool)  # ativo, pausado

    def __init__(
        self,
        model: DownloadModel,
        outdir: str,
        concurrency: int = 3,
        worker_factory: WorkerFactory = DownloadWorker,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.model = model
        self.items: list[dict] = model.items()  # lista única e compartilhada
        self._outdir = os.path.abspath(os.path.expanduser(outdir))
        self._concurrency = max(1, int(concurrency))
        self._active = False
        self._paused = False
        self._running = 0
        self._threads: dict[int, tuple[QThread, DownloadWorker, dict]] = {}
        self._counter = 0
        self._cookies = ""
        self._limit_rate = ""
        self._fragments = 1
        self._format_mode = "video_audio"
        self._quality = "best"
        self._container = "mp4"
        self._codec = "copy"
        self._compress_level = "medium"
        self._naming_mode = "id"
        self._worker_factory = worker_factory
        self._translate: Callable[..., str] = translator("pt")

    # ------------------------------------------------------------ propriedades
    @Property(str, notify=outdirChanged)
    def outdir(self) -> str:
        return self._outdir

    @outdir.setter
    def outdir(self, value: str) -> None:
        value = os.path.abspath(os.path.expanduser(value))
        if value != self._outdir:
            self._outdir = value
            self.outdirChanged.emit(value)

    @Property(bool, notify=queueStateChanged)
    def isActive(self) -> bool:
        return self._active

    @Property(bool, notify=queueStateChanged)
    def isPaused(self) -> bool:
        return self._paused

    def set_translator(self, fn: Callable[..., str]) -> None:
        self._translate = fn

    @Slot(str)
    def setCookies(self, cookies: str) -> None:
        self._cookies = cookies or ""

    @Slot(str)
    def setLimitRate(self, rate: str) -> None:
        self._limit_rate = (rate or "").strip()

    @Slot(int)
    def setFragments(self, n: int) -> None:
        self._fragments = max(1, int(n))

    @Slot(str)
    def setFormatMode(self, mode: str) -> None:
        """Define o modo de extração: video_audio | video_only | audio_only."""
        self._format_mode = mode if mode in FORMAT_MODES else "video_audio"

    @Slot(str)
    def setQuality(self, quality: str) -> None:
        """Limite de altura do vídeo (ex.: "1080") ou "best"."""
        self._quality = quality or "best"

    @Slot(str)
    def setContainer(self, container: str) -> None:
        """Contêiner/formato de saída (mp4, mkv, webm, avi, mov, mp3, ...)."""
        self._container = container or "mp4"

    @Slot(str)
    def setCodec(self, codec: str) -> None:
        """Compressão de vídeo: copy (sem reencode), h264 ou h265."""
        self._codec = codec or "copy"

    @Slot(str)
    def setCompressLevel(self, level: str) -> None:
        """Nível de compressão: light | medium | strong."""
        self._compress_level = level or "medium"

    @Slot(str)
    def setNamingMode(self, mode: str) -> None:
        """Nome do arquivo: id (hash estável) ou title (título da página)."""
        self._naming_mode = mode or "id"

    @Slot(int)
    def setConcurrency(self, n: int) -> None:
        self._concurrency = max(1, int(n))
        if self._active and not self._paused:
            self._pump()

    @Slot(str)
    def setOutdir(self, path: str) -> None:
        self.outdir = path

    # ------------------------------------------------------------- adição
    @Slot(str)
    def addText(self, text: str) -> list:
        """Adiciona os links extraídos de ``text``, ignorando duplicados ativos.

        Retorna ``[adicionados, duplicados_ignorados]``. Links finalizados
        podem ser re-adicionados (forma de tentar de novo).
        """
        urls = extract_urls(text)
        existing = {
            normalize_url(i["url"]) for i in self.items if i["status"] not in FINAL
        }
        added = 0
        skipped = 0
        for url in urls:
            norm = normalize_url(url)
            if norm in existing:
                skipped += 1
                continue
            existing.add(norm)
            self._counter += 1
            item = make_item(self._counter, url)
            self.model.add(item)
            self.itemUpdated.emit(item)
            added += 1
        if added:
            self._emit_stats()
        return [added, skipped]

    # ------------------------------------------------------------- controle
    @Slot()
    def start(self) -> None:
        self._active = True
        self._paused = False
        self._pump()
        self._emit_stats()
        self._emit_state()

    @Slot()
    def pause(self) -> None:
        """Para de agendar novos itens (os ativos continuam até terminar)."""
        self._paused = True
        self._emit_stats()
        self._emit_state()

    @Slot()
    def resume(self) -> None:
        self._paused = False
        if self._active:
            self._pump()
        self._emit_stats()
        self._emit_state()

    @Slot()
    def cancelAll(self) -> None:
        """Cancela os itens pendentes e interrompe os ativos."""
        self._active = False
        self._paused = False
        for item in self.items:
            if item["status"] == Status.WAITING or item["status"] in ACTIVE:
                self._set_status(item, Status.CANCELLED)
        for _, worker, _ in list(self._threads.values()):
            worker.cancel()
        self._emit_state()

    @Slot()
    def clearFinished(self) -> None:
        """Remove da fila os itens em estado final (ok/erro/cancelado)."""
        rows = [i for i, it in enumerate(self.items) if it["status"] in FINAL]
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()

    @Slot(int)
    def cancelItem(self, row: int) -> None:
        """Cancela um único item (pendente ou em execução)."""
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] in ACTIVE:
            entry = self._threads.get(item["id"])
            if entry:
                entry[1].cancel()
            self._set_status(item, Status.CANCELLED)
        elif item["status"] == Status.WAITING:
            self._set_status(item, Status.CANCELLED)

    @Slot(int)
    def removeItem(self, row: int) -> None:
        """Remove um item (cancelando se estiver ativo)."""
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] in ACTIVE or item["status"] == Status.WAITING:
            self.cancelItem(row)
        try:
            current = self.items.index(item)
        except ValueError:
            return
        self.model.remove_rows([current])
        self._emit_stats()

    @Slot(int)
    def retryItem(self, row: int) -> None:
        """Reenfileira um item em estado final com a mesma URL."""
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] not in FINAL:
            return
        item["status"] = Status.WAITING
        item["progress"] = 0.0
        item["speed"] = "—"
        item["size"] = "—"
        item["error"] = ""
        item.pop("path", None)
        item.pop("thumb", None)
        self._touch(item)
        self._emit_stats()
        if self._active and not self._paused:
            self._pump()

    @Slot(int, str)
    def editUrl(self, row: int, new_url: str) -> bool:
        """Edita a URL de um item parado e o reenfileira. Retorna True se ok."""
        if not (0 <= row < len(self.items)):
            return False
        new_url = (new_url or "").strip()
        if not new_url:
            return False
        item = self.items[row]
        if item["status"] in ACTIVE:
            return False  # não edita em andamento
        if normalize_url(new_url) == normalize_url(item["url"]):
            return True  # nada mudou
        existing = {
            normalize_url(i["url"])
            for i in self.items
            if i is not item and i["status"] not in FINAL
        }
        if normalize_url(new_url) in existing:
            return False  # viraria duplicado
        item["url"] = new_url
        item["title"] = new_url
        item["status"] = Status.WAITING
        item["progress"] = 0.0
        item["speed"] = "—"
        item["size"] = "—"
        item["error"] = ""
        item.pop("path", None)
        item.pop("thumb", None)
        self._touch(item)
        self._emit_stats()
        return True

    @Slot()
    def clearAll(self) -> None:
        self.cancelAll()
        rows = list(range(len(self.items)))
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()

    def shutdown(self, timeout: float = 8.0) -> None:
        """Cancela tudo e aguarda as threads terminarem (chamado ao fechar)."""
        self.cancelAll()
        import time as _time

        deadline = _time.time() + timeout
        for thread, _worker, _item in list(self._threads.values()):
            remaining = max(0.0, deadline - _time.time())
            try:
                thread.quit()
                thread.wait(int(remaining * 1000))
            except RuntimeError:
                pass
        self._threads.clear()
        self._running = 0

    # ------------------------------------------------------------- agendador
    def _pump(self) -> None:
        """Dispara workers até atingir o limite de concorrência."""
        if not self._active or self._paused:
            return
        while self._running < self._concurrency:
            nxt = next((i for i in self.items if i["status"] == Status.WAITING), None)
            if nxt is None:
                break
            self._launch(nxt)

    def _launch(self, item: dict) -> None:
        """Cria QThread + worker para um item."""
        item["status"] = Status.ANALYZING
        self._touch(item)

        thread = QThread(self)
        worker = self._worker_factory(
            url=item["url"],
            outdir=self._outdir,
            use_ffmpeg_hls=True,
            cookies=self._cookies,
            limit_rate=self._limit_rate,
            fragments=self._fragments,
            format_mode=self._format_mode,
            quality=self._quality,
            container=self._container,
            codec=self._codec,
            compress_level=self._compress_level,
            naming_mode=self._naming_mode,
            translate=self._translate,
        )
        worker.moveToThread(thread)

        worker.progressChanged.connect(lambda pct, sp, sz, it=item: self._on_progress(it, pct, sp, sz))
        worker.statusChanged.connect(lambda st, it=item: self._on_status(it, st))
        worker.titleChanged.connect(lambda title, it=item: self._on_title(it, title))
        worker.succeeded.connect(lambda url, path, it=item: self._on_success(it, path))
        worker.failed.connect(lambda url, err, it=item: self._on_failure(it, err))
        worker.cancelled.connect(lambda url, it=item: self._on_cancelled(it))
        worker.thumbnailReady.connect(lambda path, it=item: self._on_thumb(it, path))

        # Ciclo de vida da thread. NÃO usar deleteLater (padrão deleteLater +
        # GC do PySide6 pode deixar o wrapper apontando para o C++ deletado e
        # causar crash 0xC0000409). Refcount/GC após `finished` é seguro.
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda it=item: self._on_thread_done(it))

        self._threads[item["id"]] = (thread, worker, item)
        self._running += 1
        self._emit_stats()
        thread.start()

    # ----------------------------------------------------- callbacks (main)
    def _on_progress(self, item: dict, pct: float, speed: str, size: str) -> None:
        item["progress"] = pct
        item["speed"] = speed
        if size != "—":
            item["size"] = size
        self._touch(item)

    def _on_status(self, item: dict, status: str) -> None:
        try:
            self._set_status(item, Status(status))
        except ValueError:
            pass

    def _on_title(self, item: dict, title: str) -> None:
        if title:
            item["title"] = title
            self._touch(item)

    def _on_success(self, item: dict, path: str) -> None:
        item["status"] = Status.DONE
        item["progress"] = 100.0
        item["speed"] = "—"
        item["path"] = path
        item["title"] = item.get("title") or os.path.basename(path)
        self._touch(item)
        self._emit_stats()

    def _on_failure(self, item: dict, error: str) -> None:
        item["status"] = Status.ERROR
        item["error"] = error
        self._touch(item)
        self._emit_stats()

    def _on_cancelled(self, item: dict) -> None:
        item["status"] = Status.CANCELLED
        self._touch(item)
        self._emit_stats()

    def _on_thumb(self, item: dict, path: str) -> None:
        if path:
            item["thumb"] = QUrl.fromLocalFile(path).toString()
            self._touch(item)

    def _on_thread_done(self, item: dict) -> None:
        """Uma thread terminou -> libera a vaga e dispara o próximo item."""
        self._threads.pop(item["id"], None)
        self._running = max(0, self._running - 1)
        self._pump()
        self._emit_stats()

    # ------------------------------------------------------------- helpers
    def _set_status(self, item: dict, status: Status) -> None:
        item["status"] = status
        self._touch(item)
        self._emit_stats()

    def _touch(self, item: dict) -> None:
        row = self.model.index_of(item)
        if row >= 0:
            self.model.touch(row)
        self.itemUpdated.emit(item)

    def _emit_stats(self) -> None:
        waiting = sum(1 for i in self.items if i["status"] == Status.WAITING)
        downloading = sum(1 for i in self.items if i["status"] in ACTIVE)
        done = sum(1 for i in self.items if i["status"] == Status.DONE)
        errors = sum(1 for i in self.items if i["status"] == Status.ERROR)
        self.statsChanged.emit(waiting, downloading, done, errors)
        # Fila ociosa (nada pendente/ativo e nenhuma thread viva): volta ao
        # estado inicial para o botão "Iniciar Fila" reaparecer.
        if (
            self._active
            and not self._paused
            and waiting == 0
            and downloading == 0
            and not self._threads
        ):
            self._active = False
            self._emit_state()

    def _emit_state(self) -> None:
        self.queueStateChanged.emit(self._active, self._paused)
