"""
worker.py
=========
Motor de download do HLS Downloader Pro.

Responsabilidades:
  1. Extrair URLs de textos em lote (clipboard / .txt / textarea).
  2. Baixar vídeos via `yt-dlp` em subprocesso controlado (tentativa primária).
  3. Fallback: se o yt-dlp falhar, raspar o HTML com `requests` + `BeautifulSoup`
     em busca de manifestos `.m3u8` ou links diretos e repetir o download.
  4. Fallback final: baixar o `.m3u8` diretamente com `ffmpeg` (merge `-c copy`).
  5. Expor a fila como um `QAbstractListModel` consumido pelo QML.
  6. Gerenciar N downloads simultâneos com threads isoladas (`QThread`).

Tudo que é bloqueante roda dentro de threads QThread, nunca na thread da GUI,
portanto a interface nunca congela.
"""

from __future__ import annotations

import os
import glob
import hashlib
import logging
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from PyQt6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    QUrl,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)

# ---------------------------------------------------------------------------
# Import opcional do scraper (se o usuário não instalou as dependências,
# o app continua funcionando, mas o fallback de HTML fica desabilitado).
# ---------------------------------------------------------------------------
try:
    import requests
    from bs4 import BeautifulSoup

    HAS_SCRAPER = True
except ImportError:  # pragma: no cover
    HAS_SCRAPER = False

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Regex usadas na raspagem / extração de URLs
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
M3U8_RE = re.compile(r"https?://[^\"'\s<>\\]+\.m3u8[^\"'\s<>\\]*", re.IGNORECASE)
DIRECT_MEDIA_RE = re.compile(
    r"https?://[^\"'\s<>\\]+\.(?:mp4|webm|mkv|mov|avi|mp3|m4a)[^\"'\s<>\\]*",
    re.IGNORECASE,
)
PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+~?\s*([\d.]+\s*\w+(?:/\w+)?)"
    r"(?:.*?at\s+([\d.]+\s*\w+/s))?(?:\s+ETA\s+(\S+))?.*"
)
FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):([\d.]+)")
FFMPEG_SIZE_RE = re.compile(r"size=\s*([\d.]+\w+)")

TRAILING = ".,;:!?)]}>\"'"

# ---------------------------------------------------------------------------
# Log de diagnóstico — em pasta estável do usuário (em binário empacotado o
# diretório do script é /tmp/_MEIxxxx, que some ao fechar o app).
# ---------------------------------------------------------------------------
def _stable_log_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "HLSDownloaderPro")
    try:
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "hls_downloader.log")
    except OSError:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "hls_downloader.log"
        )


try:
    logging.basicConfig(
        filename=_stable_log_path(),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    log = logging.getLogger("hlsdl")
except OSError:  # sem permissão de escrita em lugar nenhum
    log = logging.getLogger("hlsdl")
    log.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Constantes de status exibidas na GUI (idioma PT-BR)
# ---------------------------------------------------------------------------
class Status:
    WAITING = "Aguardando"
    ANALYZING = "Analisando HTML"
    DOWNLOADING = "Baixando"
    DONE = "Concluído"
    ERROR = "Erro"
    CANCELLED = "Cancelado"

    FINAL = {DONE, ERROR, CANCELLED}


def extract_urls(text: str) -> List[str]:
    """Extrai URLs válidas de um texto, ignorando duplicatas."""
    if not text:
        return []
    urls: List[str] = []
    seen: set = set()
    for line in text.splitlines():
        for match in URL_RE.finditer(line):
            raw = match.group(0)
            url = raw.rstrip(TRAILING)  # remove pontuação final acidental
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def normalize_url(url: str) -> str:
    """Normaliza uma URL para comparação (fragmento e barra final ignorados)."""
    u = (url or "").strip().rstrip("/")
    u = u.split("#", 1)[0]  # fragmento (#...) não muda o recurso
    return u.lower()


def _which(name: str) -> Optional[str]:
    """Localiza um binário no PATH (aceita .exe no Windows)."""
    for exe in (name, name + ".exe"):
        found = shutil.which(exe)
        if found:
            return found
    return None


def cleanup_thumbs() -> None:
    """Apaga a pasta temporária de miniaturas (chamado ao fechar o app)."""
    shutil.rmtree(os.path.join(tempfile.gettempdir(), "hlsdlp-thumbs"),
                  ignore_errors=True)


# Caracteres proibidos no Windows (ASCII) e seus equivalentes fullwidth que o
# yt-dlp usa ao sanitizar com --windows-filenames (ex.: '?' -> '？' U+FF1F).
_INVALID_CHARS_RE = re.compile(
    r"[?*<>|\":/\\\uFF1F\uFF0A\uFF1C\uFF1E\uFF5C\uFF02\uFF1A\uFF0F]"
)


def _normalize_name(name: str) -> str:
    """Remove caracteres proibidos/fullwidth de um nome de arquivo."""
    return _INVALID_CHARS_RE.sub("", name).lower()


def _resolve_existing_file(path: str) -> str:
    """
    Retorna o caminho real de um arquivo recém-baixado.

    O yt-dlp (algumas versões) imprime em `after_move:filepath` um caminho
    sanitizado que NÃO corresponde ao nome gravado no disco (o arquivo fica
    com caracteres fullwidth, ex.: '?'). Então `os.path.exists` falha mesmo
    com o download concluído. Aqui procuramos o arquivo no diretório pelo
    nome normalizado (sem caracteres proibidos/fullwidth).
    """
    if path and os.path.exists(path):
        return path
    if not path:
        return ""
    d, base = os.path.split(path)
    want = _normalize_name(base)
    if not want:
        return ""
    try:
        candidates = [
            os.path.join(d, n)
            for n in os.listdir(d)
            if _normalize_name(n) == want
        ]
    except OSError:
        return ""
    if not candidates:
        return ""
    # se houver mais de um, prefere o mais recente (acabou de ser baixado)
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _shorten_name(path: str, limit: int = 20) -> str:
    """Renomeia o arquivo para um nome curto (base <= `limit` caracteres).

    O limite é aplicado por CARACTERES (não bytes), então nunca quebra
    acentos/UTF-8. Se já está curto, devolve o caminho sem mexer.
    """
    folder, name = os.path.split(path)
    base, ext = os.path.splitext(name)
    if len(base) <= limit:
        return path
    base = base[:limit].rstrip(" ._-")
    if not base:
        base = "video"
    target = os.path.join(folder, base + ext)
    n = 2
    while os.path.exists(target) and os.path.normcase(target) != os.path.normcase(path):
        target = os.path.join(folder, f"{base}-{n}{ext}")
        n += 1
    if os.path.normcase(target) == os.path.normcase(path):
        return path
    try:
        os.rename(path, target)
        log.info("nome encurtado: %r -> %r", name, os.path.basename(target))
        return target
    except OSError:
        return path


# ===========================================================================
# MODELO DA FILA (QAbstractListModel) consumido pelo QML
# ===========================================================================
class DownloadModel(QAbstractListModel):
    """
    Expõe a fila de downloads como um modelo de lista.

    O QML acessa cada campo pelo nome do role: `url`, `title`, `status`,
    `progress`, `speed`, `size` e `error`. As linhas compartilham a mesma
    lista de dicts usada pelo QueueManager (`items`).
    """

    URL = Qt.ItemDataRole.UserRole + 1
    TITLE = Qt.ItemDataRole.UserRole + 2
    STATUS = Qt.ItemDataRole.UserRole + 3
    PROGRESS = Qt.ItemDataRole.UserRole + 4
    SPEED = Qt.ItemDataRole.UserRole + 5
    SIZE = Qt.ItemDataRole.UserRole + 6
    ERROR = Qt.ItemDataRole.UserRole + 7
    PATH = Qt.ItemDataRole.UserRole + 8
    THUMB = Qt.ItemDataRole.UserRole + 9

    def __init__(self, items: List[dict], parent: Optional[QObject] = None):
        super().__init__(parent)
        self._items = items

    def roleNames(self) -> dict:
        return {
            self.URL: b"url",
            self.TITLE: b"title",
            self.STATUS: b"status",
            self.PROGRESS: b"progress",
            self.SPEED: b"speed",
            self.SIZE: b"size",
            self.ERROR: b"error",
            self.PATH: b"path",
            self.THUMB: b"thumb",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None
        item = self._items[index.row()]
        if role == self.URL:
            return item.get("url", "")
        if role == self.TITLE:
            return item.get("title") or item.get("url", "")
        if role == self.STATUS:
            return item.get("status", Status.WAITING)
        if role == self.PROGRESS:
            return int(item.get("progress", 0.0))
        if role == self.SPEED:
            return item.get("speed", "—")
        if role == self.SIZE:
            return item.get("size", "—")
        if role == self.ERROR:
            return item.get("error", "")
        if role == self.PATH:
            return item.get("path", "")
        if role == self.THUMB:
            return item.get("thumb", "")
        return None

    # ---- métodos de mutação usados pelo QueueManager ---------------------
    def add(self, item: dict) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()

    def touch(self, row: int) -> None:
        """Notifica o QML de que a linha `row` mudou."""
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx)

    def remove_rows(self, rows: List[int]) -> None:
        """Remove as linhas (ordem decrescente) da fila."""
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._items):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._items.pop(row)
                self.endRemoveRows()


# ===========================================================================
# WORKER INDIVIDUAL (roda em uma QThread própria)
# ===========================================================================
class DownloadWorker(QObject):
    """
    Processa UM link de cada vez dentro de sua própria QThread.

    Sinais emitidos da thread do worker são entregues com segurança à thread
    principal via fila de eventos do Qt (connection type automático).
    """

    statusChanged = pyqtSignal(str)          # novo texto de status
    progressChanged = pyqtSignal(float, str, str)  # percentual, velocidade, tamanho
    titleChanged = pyqtSignal(str)           # título detectado (do arquivo destino)
    succeeded = pyqtSignal(str, str)         # url, caminho do arquivo final
    failed = pyqtSignal(str, str)            # url, mensagem de erro
    cancelled = pyqtSignal(str)              # url
    finished = pyqtSignal()                  # fim do run() (aciona thread.quit)

    def __init__(
        self,
        url: str,
        outdir: str,
        use_ffmpeg_hls: bool = True,
        cookies: str = "",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.url = url
        self.outdir = outdir
        self.use_ffmpeg_hls = use_ffmpeg_hls
        self.cookies = cookies or ""
        self._cancel = False
        self._proc: Optional[subprocess.Popen] = None
        self._stdout_tail: List[str] = []

    # Sinais adicionais
    thumbnailReady = pyqtSignal(str)  # caminho da miniatura gerada (ou vazio)

    # ------------------------------------------------------------------ API
    def cancel(self) -> None:
        """Solicita cancelamento (thread-safe: apenas marca flag e mata proc)."""
        self._cancel = True
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    # ----------------------------------------------------- ponto de entrada
    def run(self) -> None:
        """
        Fluxo de engenharia exigido:
          1) yt-dlp direto na URL;
          2) se falhar -> raspa HTML buscando m3u8 / link direto;
          3) tenta o link encontrado no yt-dlp;
          4) se ainda falhar e for m3u8 -> ffmpeg com -c copy.
        """
        try:
            self.statusChanged.emit(Status.ANALYZING)
            self.progressChanged.emit(0.0, "—", "—")
            log.info("INICIO url=%s outdir=%s", self.url, self.outdir)

            if not self._cancel:
                # ---- Tentativa primária: yt-dlp na URL original ----
                ok, result = self._run_ytdlp(self.url)
                log.info("yt-dlp direto: ok=%s result=%r", ok, result)
                if ok:
                    self._succeed(result)
                    return

            if self._cancel:
                self.cancelled.emit(self.url)
                self.finished.emit()
                return

            # ---- Fallback: raspar o HTML da página ----
            self.statusChanged.emit(Status.ANALYZING)
            self.progressChanged.emit(0.0, "—", "—")
            candidate = self._find_media_in_html()
            log.info("scraper: candidate=%r", candidate)
            if not candidate:
                msg = result if isinstance(result, str) else "Falha na extração"
                self.failed.emit(
                    self.url,
                    f"{msg} | Nenhum stream .m3u8/link direto encontrado no HTML",
                )
                self.finished.emit()
                return

            # ---- Tentativa secundária: yt-dlp no link bruto ----
            ok2, result2 = self._run_ytdlp(candidate, referer=self.url)
            log.info("yt-dlp no link raspado: ok=%s result=%r", ok2, result2)
            if ok2:
                self._succeed(result2)
                return

            # ---- Tentativa final: ffmpeg direto no m3u8 ----
            is_hls = ".m3u8" in candidate.lower()
            if is_hls and self.use_ffmpeg_hls and not self._cancel:
                ok3, result3 = self._run_ffmpeg(candidate)
                log.info("ffmpeg fallback: ok=%s result=%r", ok3, result3)
                if ok3:
                    self._succeed(result3)
                    return
                self.failed.emit(
                    self.url,
                    f"{result2 if isinstance(result2, str) else 'Falha no yt-dlp'} | "
                    f"ffmpeg: {result3}",
                )
                self.finished.emit()
                return

            self.failed.emit(self.url, result2 if isinstance(result2, str) else "Falha no download")
            self.finished.emit()
        except Exception as exc:  # qualquer erro inesperado não pode matar a thread
            self.failed.emit(self.url, f"Erro inesperado: {exc}")
            self.finished.emit()

    # --------------------------------------------------- download via yt-dlp
    def _run_ytdlp(self, target: str, referer: Optional[str] = None) -> Tuple[bool, str]:
        """Executa yt-dlp em subprocesso e repassa o progresso pela GUI."""
        ytdlp = _which("yt-dlp")
        if not ytdlp:
            return False, "yt-dlp não encontrado no PATH (instale via pip)."

        os.makedirs(self.outdir, exist_ok=True)
        # Nome do arquivo: curto, estável e sem caracteres especiais —
        # hash da URL (mesmo padrão do fallback ffmpeg). O mesmo link sempre
        # gera o mesmo nome, então `--no-overwrites` nunca duplica arquivos;
        # e o nome nunca contém título/id raspado (que traz `?`, `/`, acentos
        # e URLs inteiras — fonte de falhas ao salvar, principalmente no Linux).
        digest = hashlib.sha1(target.encode("utf-8")).hexdigest()[:10]
        name_base = f"vid_{digest}"
        out_template = os.path.join(self.outdir, f"{name_base}.%(ext)s")

        cmd = [
            ytdlp,
            "--newline",          # uma atualização de progresso por linha
            "--progress",
            "--no-playlist",
            "--no-mtime",
            "--no-overwrites",     # nunca re-baixa arquivo já existente no disco
            "--windows-filenames",
            "--retries", "3",
            "--fragment-retries", "5",
            "--socket-timeout", "20",
            "-f", "bv*+ba/b",     # melhor vídeo + melhor áudio (ou o melhor único)
            "--merge-output-format", "mp4",
            "--print", "after_move:filepath",  # caminho final pós-pós-processamento
            "-o", out_template,
            "--user-agent", USER_AGENT,
        ]
        if referer:
            cmd += ["--add-header", f"Referer:{referer}"]
        cookie_args = self._build_cookies_args()
        if cookie_args:
            log.info("cookies ativos: %s", " ".join(cookie_args))
            cmd += cookie_args
        cmd.append(target)

        ok, msg = self._run_process(cmd)
        lower = msg.lower()
        if ok or not ("unusual" in lower or "unsafe" in lower or "skipped for" in lower):
            return ok, msg

        # Bloqueio de segurança do yt-dlp (CVE-2024-38519): URLs cuja
        # extensão é incomum (.php, .aspx, ...) são recusadas mesmo quando o
        # conteúdo é um vídeo legítimo. Retentamos UMA vez com
        # `allow-unsafe-ext` e a extensão .mp4 FORÇADA no template — o nome
        # final fica seguro e a extensão suspeita nunca entra no arquivo.
        log.warning(
            "extensão incomum detectada (%r) — retry allow-unsafe-ext + .mp4",
            msg[:200],
        )
        retry_cmd = cmd.copy()
        retry_cmd += ["--compat-options", "allow-unsafe-ext"]
        try:
            i = retry_cmd.index("-o")
            retry_cmd[i + 1] = os.path.join(
                self.outdir, f"{name_base}.mp4"
            )
        except ValueError:
            pass
        ok2, msg2 = self._run_process(retry_cmd)
        if ok2 and isinstance(msg2, str) and os.path.isfile(msg2):
            # O retry pode baixar a PÁGINA HTML em vez do vídeo (extensão .php
            # vale para os dois) ou a playlist HLS crua (sem os segmentos,
            # inútil como .mp4). Se o conteúdo não for vídeo, descarta e
            # devolve o erro original — o fluxo segue para o scraper/ffmpeg.
            if self._looks_like_non_video(msg2):
                log.warning(
                    "retry baixou conteúdo não-vídeo (HTML/playlist) — descartando: %s",
                    msg2,
                )
                try:
                    os.remove(msg2)
                except OSError:
                    pass
                return False, msg
        return ok2, msg2

    def _build_cookies_args(self) -> List[str]:
        """Converte a configuração de cookies em argumentos do yt-dlp.

        `self.cookies` pode ser:
          "browser:<nome>"  -> --cookies-from-browser (chrome, firefox, ...)
          "file:<caminho>"  -> --cookies <caminho> (formato Netscape)
          ""                -> sem cookies
        """
        if not self.cookies:
            return []
        if self.cookies.startswith("browser:"):
            name = self.cookies[len("browser:"):].strip().lower()
            if name:
                return ["--cookies-from-browser", name]
        elif self.cookies.startswith("file:"):
            path = self.cookies[len("file:"):].strip()
            if path and os.path.isfile(path):
                return ["--cookies", path]
            log.warning("arquivo de cookies não encontrado: %r", path)
        return []

    # ---------------------------------------------------- download via ffmpeg
    def _run_ffmpeg(self, media_url: str) -> Tuple[bool, str]:
        """Baixa um .m3u8 com ffmpeg, copiando o codec (fallback final).

        O nome do arquivo é estável (hash da URL), então re-baixar o mesmo
        link não cria arquivo duplicado: se o arquivo já existe, é sucesso.
        """
        ffmpeg = _which("ffmpeg")
        if not ffmpeg:
            return False, "ffmpeg não encontrado no PATH."

        digest = hashlib.sha1(media_url.encode("utf-8")).hexdigest()[:10]
        out_path = os.path.join(self.outdir, f"hls_{digest}.mp4")
        if os.path.exists(out_path):
            return True, out_path  # arquivo duplicado já baixado antes

        duration = self._probe_duration(media_url)

        # Estratégia: copiar direto; se falhar, re-codificar áudio; se ainda
        # falhar, re-codificar tudo (compatibilidade máxima com HLS "difícil").
        recipes = [
            ["-c", "copy", "-bsf:a", "aac_adtstoasc"],
            ["-c:v", "copy", "-c:a", "aac", "-bsf:a", "aac_adtstoasc"],
            ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"],
        ]
        last_error = "desconhecido"
        for recipe in recipes:
            if self._cancel:
                return False, "cancelado"
            # -nostats REMOVIDO de propósito: é ele que suprime as linhas de
            # progresso (time=...) que usamos para calcular o percentual.
            cmd = [ffmpeg, "-y", "-hide_banner", "-i", media_url] + recipe + [out_path]
            ok, last_error = self._run_process(
                cmd, duration=duration, is_ffmpeg=True
            )
            if ok:
                return True, out_path
            if self._cancel:
                return False, "cancelado"
            try:
                os.remove(out_path)
            except OSError:
                pass
        return False, last_error

    def _probe_duration(self, media_url: str) -> Optional[float]:
        """Obtém a duração total (segundos) do m3u8 via ffprobe."""
        ffprobe = _which("ffprobe")
        if not ffprobe:
            return None
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_url,
        ]
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=40,
                encoding="utf-8", errors="replace",
            )
            return float(out.stdout.strip())
        except Exception:
            return None

    # ----------------------------------------------------- executor genérico
    def _run_process(
        self,
        cmd: List[str],
        duration: Optional[float] = None,
        is_ffmpeg: bool = False,
    ) -> Tuple[bool, str]:
        """Roda um subprocesso, parseia progresso e retorna (ok, mensagem)."""
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # Drena o stderr em uma thread auxiliar (ffmpeg escreve progresso lá)
        stderr_lines: List[str] = []
        def _drain_stderr() -> None:
            for line in self._proc.stderr:
                stderr_lines.append(line.rstrip())

        drainer = threading.Thread(target=_drain_stderr, daemon=True)
        drainer.start()

        result_msg = ""
        rc: Optional[int] = None

        try:
            if is_ffmpeg:
                result_msg = self._consume_ffmpeg_stdout(
                    self._proc, stderr_lines, duration
                )
            else:
                result_msg = self._consume_ytdlp_stdout(self._proc, stderr_lines)
        finally:
            rc = self._proc.wait()
            drainer.join(timeout=2)
            self._proc = None

        if self._cancel:
            if is_ffmpeg:
                try:
                    os.remove(cmd[-1])
                except OSError:
                    pass
            else:
                self._cleanup_temp_files(result_msg)
            return False, "cancelado"

        if rc != 0:
            if stderr_lines:
                log.error("rc=%s | stderr:\n%s", rc, "\n".join(stderr_lines[-15:]))
            else:
                log.error("rc=%s | stdout final: %r", rc, result_msg[-500:])
            if is_ffmpeg:
                try:
                    os.remove(cmd[-1])
                except OSError:
                    pass
            else:
                self._cleanup_temp_files(result_msg)
            if stderr_lines:
                # última linha de erro real (ignora avisos)
                errors = [l for l in stderr_lines if "error" in l.lower() or "ERROR" in l]
                msg = errors[-1] if errors else stderr_lines[-1]
                return False, msg.strip()
            return False, result_msg or f"Processo terminou com código {rc}"

        if is_ffmpeg:
            if os.path.exists(cmd[-1]):
                return True, cmd[-1]
            log.warning("ffmpeg rc=0 sem arquivo; stderr:\n%s", "\n".join(stderr_lines[-12:]))
            return False, "ffmpeg não gerou o arquivo de saída."
        if result_msg:
            real = _resolve_existing_file(result_msg)
            if real:
                if real != result_msg:
                    log.warning(
                        "caminho impresso != arquivo real; resolvido por nome: %r",
                        real,
                    )
                real = _shorten_name(real)
                return True, real
        log.warning(
            "yt-dlp rc=0 sem arquivo detectado; stdout:\n%s",
            "\n".join(self._stdout_tail[-12:]) or "(vazio)",
        )
        return False, result_msg or "yt-dlp não gerou o arquivo de saída."

    def _looks_like_non_video(self, path: str) -> bool:
        """True se o arquivo baixado não for um vídeo: página HTML ou
        playlist HLS crua (sem os segmentos baixados)."""
        try:
            with open(path, "rb") as fh:
                head = fh.read(4096).lower()
        except OSError:
            return False
        return (
            b"<html" in head
            or b"<!doctype" in head
            or b"<head" in head
            or b"<body" in head
            or head.lstrip().startswith(b"#extm3u")
        )

    def _cleanup_temp_files(self, out_path: str) -> None:
        """Remove arquivos temporários (.part / .ytdl) de downloads cancelados."""
        if not out_path:
            return
        for pattern in (out_path + ".part", out_path + ".ytdl", out_path + ".part-Frag*"):
            try:
                for f in glob.glob(pattern):
                    os.remove(f)
            except OSError:
                pass

    def _consume_ytdlp_stdout(self, proc, stderr_lines) -> str:
        """Lê o stdout do yt-dlp e emite sinais de progresso."""
        out_path: Optional[str] = None
        for line in proc.stdout:
            if self._cancel:
                proc.terminate()
                break
            line = line.strip()
            if not line:
                continue
            self._stdout_tail.append(line)
            if len(self._stdout_tail) > 40:
                self._stdout_tail.pop(0)
            m = PROGRESS_RE.search(line)
            if m:
                pct = min(100.0, float(m.group(1)))
                size = m.group(2)
                speed = m.group(3) or "—"
                self.statusChanged.emit(Status.DOWNLOADING)
                self.progressChanged.emit(pct, speed, size)
                continue
            # Caminho final impresso por `--print after_move:filepath`:
            # sai no fim, após qualquer merge/remux/re-encode, e é a fonte
            # mais confiável para o arquivo realmente gerado. `isabs` cobre
            # caminhos Windows (C:\) e Linux (/home/...).
            if os.path.isabs(line):
                out_path = line.strip()
                self.titleChanged.emit(os.path.basename(out_path))
                continue
            dm = re.search(r"\[download\] Destination: (.+)", line)
            if dm:
                out_path = dm.group(1).strip()
                self.titleChanged.emit(os.path.basename(out_path))
                continue
            # Download já existente na pasta: yt-dlp pula e informa o caminho.
            skip = re.search(r"\[download\] (.+?) has already been downloaded", line)
            if skip:
                out_path = skip.group(1).strip()
                continue
            # Quando vídeo+áudio são baixados separados, o arquivo final é o
            # do pós-processador de merge (diferente do último Destination).
            mm = re.search(r"\[(?:Merger|VideoMerge|Mux)\]\s*Merging formats into \"(.+)\"", line)
            if mm:
                out_path = mm.group(1).strip()
                self.titleChanged.emit(os.path.basename(out_path))
        return out_path or ""

    def _consume_ffmpeg_stdout(self, proc, stderr_lines, duration) -> str:
        """Lê o stdout do ffmpeg (progresso em pipe:1) e emite sinais."""
        # O ffmpeg com -progress escreve no stderr por padrão; vamos ler o
        # stderr que foi drenado na thread auxiliar. Para feedback em tempo
        # real, monitoramos a lista compartilhada.
        self.statusChanged.emit(Status.DOWNLOADING)
        last_time = 0.0
        start = time.time()
        while proc.poll() is None:
            if self._cancel:
                proc.terminate()
                break
            if stderr_lines:
                line = stderr_lines[-1]
                tm = FFMPEG_TIME_RE.search(line)
                sm = FFMPEG_SIZE_RE.search(line)
                if tm:
                    h, m_, s = tm.groups()
                    t = int(h) * 3600 + int(m_) * 60 + float(s)
                    if t >= last_time:
                        last_time = t
                    pct = (last_time / duration * 100.0) if duration else 0.0
                    speed = f"{last_time:.1f}s"
                    self.progressChanged.emit(
                        min(99.0, pct),
                        speed,
                        sm.group(1) if sm else "—",
                    )
            # evita girar a CPU: aguarda nova linha aparecer
            time.sleep(0.15)
        return "ffmpeg finalizou"

    # -------------------------------------------------- conclusão e miniatura
    def _succeed(self, path: str) -> None:
        """Conclui com sucesso: gera miniatura (se possível) e emite sinais."""
        try:
            thumb = self._extract_thumbnail(path)
        except Exception:
            thumb = None
        if thumb:
            self.thumbnailReady.emit(thumb)
        self.succeeded.emit(self.url, path)
        self.finished.emit()

    def _extract_thumbnail(self, video_path: str) -> Optional[str]:
        """Gera uma miniatura .jpg do vídeo com ffmpeg (usada na tabela).

        As miniaturas são gravadas em uma pasta TEMPORÁRIA do sistema
        (`hlsdlp-thumbs`) e apagadas ao fechar o app — não poluem a pasta de
        downloads. Se falhar ou o ffmpeg não existir, retorna None (o download
        não é afetado — miniatura é um extra).
        """
        ffmpeg = _which("ffmpeg")
        if not ffmpeg or not video_path or not os.path.exists(video_path):
            return None
        thumbs_dir = os.path.join(tempfile.gettempdir(), "hlsdlp-thumbs")
        try:
            os.makedirs(thumbs_dir, exist_ok=True)
        except OSError:
            return None
        base = os.path.splitext(os.path.basename(video_path))[0]
        thumb = os.path.join(thumbs_dir, base + ".jpg")
        if os.path.exists(thumb):
            return thumb  # já existe de um download anterior na sessão
        for seek in ("2", "0"):
            cmd = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", seek, "-i", video_path,
                "-frames:v", "1",
                "-vf", "scale=320:-2",
                "-q:v", "4",
                thumb,
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=40)
            except Exception:
                continue
            if os.path.exists(thumb):
                return thumb
        return None

    # ------------------------------------------------------------- scraper
    def _find_media_in_html(self) -> Optional[str]:
        """
        Raspa o HTML da página procurando manifestos `.m3u8` ou links diretos.

        Passos:
          1) GET com cabeçalhos de navegador;
          2) BeautifulSoup: tags <source>/<video> e scripts JSON-LD;
          3) Regex no HTML bruto (pega streams injetados via JS);
          4) Normaliza URLs relativas e prioriza .m3u8.
        """
        if not HAS_SCRAPER:
            return None

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.url,
        }
        try:
            resp = requests.get(self.url, headers=headers, timeout=25, allow_redirects=True)
            resp.raise_for_status()
        except Exception:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        raw: List[str] = []

        # 1) <source> e <video> dentro do documento
        for tag in soup.find_all(["source", "video"]):
            for attr in ("src", "data-src", "data-url"):
                val = tag.get(attr)
                if val:
                    raw.append(val)

        # 2) scripts JSON-LD (muitos players embutem o stream aqui)
        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            raw.extend(M3U8_RE.findall(text))
            raw.extend(DIRECT_MEDIA_RE.findall(text))

        # 3) regex no HTML bruto (JS inline, objetos JSON, etc.)
        raw.extend(M3U8_RE.findall(resp.text))
        raw.extend(DIRECT_MEDIA_RE.findall(resp.text))

        # 4) normalizar relativos e deduplicar
        seen: set = set()
        normalized: List[str] = []
        for value in raw:
            value = value.strip().rstrip(TRAILING)
            if value.startswith("//"):
                value = "https:" + value
            elif not value.startswith("http"):
                value = urljoin(resp.url, value)
            if value not in seen and ("m3u8" in value or value.lower().endswith(
                (".mp4", ".webm", ".mkv", ".mov", ".avi", ".mp3", ".m4a")
            )):
                seen.add(value)
                normalized.append(value)

        # prioriza manifestos HLS
        normalized.sort(key=lambda u: (0 if ".m3u8" in u else 1, len(u)))
        return normalized[0] if normalized else None


# ===========================================================================
# GERENCIADOR DE FILA (multithread com limite de concorrência)
# ===========================================================================
class QueueManager(QObject):
    """Coordena a fila: cria um worker+thread por item ativo e limita o
    número de downloads simultâneos."""

    statsChanged = pyqtSignal(int, int, int, int)  # aguardando, baixando, ok, erro
    outdirChanged = pyqtSignal(str)

    def __init__(
        self,
        model: DownloadModel,
        outdir: str,
        concurrency: int = 3,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.model = model
        self.items: List[dict] = []
        self._outdir = outdir
        self._concurrency = max(1, concurrency)
        self._active = False
        self._running = 0
        self._threads: Dict[int, Tuple[QThread, DownloadWorker, dict]] = {}
        self._counter = 0
        self._cookies = ""

    # ------------------------------------------------------------ propriedades
    @pyqtProperty(str, notify=outdirChanged)
    def outdir(self) -> str:
        return self._outdir

    @outdir.setter
    def outdir(self, value: str) -> None:
        value = os.path.abspath(os.path.expanduser(value))
        if value != self._outdir:
            self._outdir = value
            self.outdirChanged.emit(value)

    @pyqtSlot(str)
    def setCookies(self, cookies: str) -> None:
        """Define a configuração de cookies repassada aos workers."""
        self._cookies = cookies or ""

    @pyqtSlot(int)
    def setConcurrency(self, n: int) -> None:
        self._concurrency = max(1, int(n))
        if self._active:
            self._pump()

    @pyqtSlot(str)
    def setOutdir(self, path: str) -> None:
        self.outdir = path

    # ------------------------------------------------------------- adição
    @pyqtSlot(str)
    def addText(self, text: str) -> list:
        """Adiciona os links extraídos de `text`, ignorando duplicados ativos.

        Retorna [adicionados, duplicados_ignorados]. Links de itens já
        finalizados (concluído/erro/cancelado) podem ser re-adicionados —
        é a forma de tentar de novo sem editar a linha.
        """
        urls = extract_urls(text)
        existing = {
            normalize_url(i["url"])
            for i in self.items
            if i["status"] not in Status.FINAL
        }
        added = 0
        skipped = 0
        for url in urls:
            if normalize_url(url) in existing:
                skipped += 1
                continue
            existing.add(normalize_url(url))
            self._counter += 1
            item = {
                "id": self._counter,
                "url": url,
                "title": url,
                "status": Status.WAITING,
                "progress": 0.0,
                "speed": "—",
                "size": "—",
                "error": "",
            }
            self.items.append(item)
            self.model.add(item)
            added += 1
        if added:
            self._emit_stats()
        return [added, skipped]

    # ------------------------------------------------------------- controle
    @pyqtSlot()
    def start(self) -> None:
        self._active = True
        self._pump()

    @pyqtSlot()
    def cancelAll(self) -> None:
        """Cancela os itens pendentes e interrompe os ativos."""
        self._active = False
        for item in self.items:
            if item["status"] == Status.WAITING:
                self._set_status(item, Status.CANCELLED)
            elif item["status"] in (Status.ANALYZING, Status.DOWNLOADING):
                self._set_status(item, Status.CANCELLED)
        for _, worker, _ in list(self._threads.values()):
            worker.cancel()

    @pyqtSlot()
    def clearFinished(self) -> None:
        """Remove da fila os itens em estado final (ok/erro/cancelado)."""
        rows = [
            i for i, it in enumerate(self.items)
            if it["status"] in Status.FINAL
        ]
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()

    @pyqtSlot(int)
    def cancelItem(self, row: int) -> None:
        """Cancela um único item (pendente ou em execução)."""
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        if item["status"] in (Status.ANALYZING, Status.DOWNLOADING):
            entry = self._threads.get(item["id"])
            if entry:
                entry[1].cancel()
            self._set_status(item, Status.CANCELLED)
        elif item["status"] == Status.WAITING:
            self._set_status(item, Status.CANCELLED)

    @pyqtSlot(int, str)
    def editUrl(self, row: int, new_url: str) -> bool:
        """Edita a URL de um item parado e o reenfileira. Retorna True se ok."""
        if not (0 <= row < len(self.items)):
            return False
        new_url = (new_url or "").strip()
        if not new_url:
            return False
        item = self.items[row]
        if item["status"] in (Status.ANALYZING, Status.DOWNLOADING):
            return False  # não edita em andamento
        if normalize_url(new_url) == normalize_url(item["url"]):
            return True  # nada mudou
        existing = {
            normalize_url(i["url"])
            for i in self.items
            if i is not item and i["status"] not in Status.FINAL
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

    @pyqtSlot()
    def clearAll(self) -> None:
        self.cancelAll()
        rows = list(range(len(self.items)))
        if rows:
            self.model.remove_rows(rows)
            self._emit_stats()

    # ------------------------------------------------------------- agendador
    def _pump(self) -> None:
        """Dispara workers até atingir o limite de concorrência."""
        if not self._active:
            return
        while self._running < self._concurrency:
            nxt = next(
                (i for i in self.items if i["status"] == Status.WAITING), None
            )
            if nxt is None:
                break
            self._launch(nxt)

    def _launch(self, item: dict) -> None:
        """Cria QThread + DownloadWorker para um item."""
        item["status"] = Status.ANALYZING
        self._touch(item)

        thread = QThread(self)
        worker = DownloadWorker(
            item["url"],
            self._outdir,
            use_ffmpeg_hls=True,
            cookies=self._cookies,
            parent=None,
        )
        worker.moveToThread(thread)

        # Religação: sinais da thread -> atualização do item (thread principal)
        worker.progressChanged.connect(
            lambda pct, sp, sz, it=item: self._on_progress(it, pct, sp, sz)
        )
        worker.statusChanged.connect(
            lambda st, it=item: self._on_status(it, st)
        )
        worker.titleChanged.connect(
            lambda title, it=item: self._on_title(it, title)
        )
        worker.succeeded.connect(
            lambda url, path, it=item: self._on_success(it, path)
        )
        worker.failed.connect(
            lambda url, err, it=item: self._on_failure(it, err)
        )
        worker.cancelled.connect(
            lambda url, it=item: self._on_cancelled(it)
        )
        worker.thumbnailReady.connect(
            lambda path, it=item: self._on_thumb(it, path)
        )

        # Ciclo de vida da thread.
        # IMPORTANTE: NÃO usar deleteLater aqui — o padrão deleteLater + GC
        # do PyQt6 pode deixar o wrapper Python apontando para o objeto C++
        # já deletado e causar crash (0xC0000409). Quando `thread.finished`
        # dispara, a thread já parou; a destruição por refcount/GC é segura.
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.finished.connect(
            lambda it=item: self._on_thread_done(it)
        )

        self._threads[item["id"]] = (thread, worker, item)
        self._running += 1
        thread.start()

    # ----------------------------------------------------- callbacks (main)
    def _on_progress(self, item: dict, pct: float, speed: str, size: str) -> None:
        item["progress"] = pct
        item["speed"] = speed
        if size != "—":
            item["size"] = size
        self._touch(item)

    def _on_status(self, item: dict, status: str) -> None:
        self._set_status(item, status)

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
            # URL codificada (espaços/colchetes/caracteres especiais no caminho)
            item["thumb"] = QUrl.fromLocalFile(path).toString()
            self._touch(item)

    def _on_thread_done(self, item: dict) -> None:
        """Uma thread terminou -> libera a vaga e dispara o próximo item."""
        self._threads.pop(item["id"], None)
        self._running = max(0, self._running - 1)
        self._pump()

    # ------------------------------------------------------------- helpers
    def _set_status(self, item: dict, status: str) -> None:
        item["status"] = status
        self._touch(item)
        self._emit_stats()

    def _touch(self, item: dict) -> None:
        try:
            row = self.items.index(item)
            self.model.touch(row)
        except ValueError:
            pass

    def _emit_stats(self) -> None:
        waiting = sum(1 for i in self.items if i["status"] == Status.WAITING)
        downloading = sum(
            1 for i in self.items if i["status"] in (Status.ANALYZING, Status.DOWNLOADING)
        )
        done = sum(1 for i in self.items if i["status"] == Status.DONE)
        errors = sum(1 for i in self.items if i["status"] == Status.ERROR)
        self.statsChanged.emit(waiting, downloading, done, errors)
