"""Motor de download de UM link, executado em uma ``QThread`` própria.

Fluxo em camadas:
  1) ``yt-dlp`` direto na URL original;
  2) se falhar -> raspa o HTML (``requests`` + ``BeautifulSoup``) buscando
     ``.m3u8``/link direto e repete o ``yt-dlp``;
  3) fallback final: ``ffmpeg -c copy`` no manifesto ``.m3u8``.

Todo o trabalho bloqueante roda nesta thread; sinais são entregues com
segurança à thread principal pelo Qt.
"""

from __future__ import annotations

import glob
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from . import config
from .compress import TEXT_SUBS, analyze, probe_media
from .config import USER_AGENT
from .formats import (
    AUDIO_CONTAINERS,
    CODECS,
    COMPRESS_LEVELS,
    CRF,
    DEFAULT_AUDIO_CONTAINER,
    DEFAULT_VIDEO_CONTAINER,
    NAMING_MODES,
)
from .i18n import translator
from .naming import resolve_existing_file, shorten_name, url_digest
from .services.procutils import (
    extract_thumbnail,
    probe_duration,
    spawn_kwargs,
    terminate_tree,
    which,
)
from .services.scraper import HtmlMediaScraper
from .status import Status

log = logging.getLogger("hlsdl")

PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+~?\s*([\d.]+\s*\w+(?:/\w+)?)"
    r"(?:.*?at\s+([\d.]+\s*\w+/s))?(?:\s+ETA\s+(\S+))?.*"
)
FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):([\d.]+)")
FFMPEG_SIZE_RE = re.compile(r"size=\s*([\d.]+\w+)")
TITLE_PREFIX = "__HSLDL_TITLE__"

# Tempo (s) sem nenhuma linha nova do ffmpeg antes de considerá-lo travado.
FFMPEG_STALL_TIMEOUT = 180.0


class DownloadWorker(QObject):
    """Processa um único link e reporta o progresso por sinais."""

    statusChanged = Signal(str)                 # texto do estado (Status.value)
    progressChanged = Signal(float, str, str)   # %, velocidade, tamanho
    titleChanged = Signal(str)                  # título detectado
    succeeded = Signal(str, str)                # url, caminho final
    failed = Signal(str, str)                   # url, mensagem
    cancelled = Signal(str)                     # url
    finished = Signal()                         # fim do run()
    thumbnailReady = Signal(str)                # caminho da miniatura

    def __init__(
        self,
        url: str,
        outdir: str,
        use_ffmpeg_hls: bool = True,
        cookies: str = "",
        limit_rate: str = "",
        fragments: int = 1,
        format_mode: str = "video_audio",
        quality: str = "best",
        container: str = "mp4",
        codec: str = "copy",
        compress_level: str = "medium",
        naming_mode: str = "id",
        translate: Callable[..., str] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.url = url
        self.outdir = outdir
        self.use_ffmpeg_hls = use_ffmpeg_hls
        self.cookies = cookies or ""
        self.limit_rate = limit_rate or ""
        self.fragments = max(1, int(fragments))
        self.format_mode = format_mode or "video_audio"
        self.quality = quality or "best"
        if self.format_mode == "audio_only" and container not in AUDIO_CONTAINERS:
            container = DEFAULT_AUDIO_CONTAINER
        self.container = container or DEFAULT_VIDEO_CONTAINER
        self.codec = codec if codec in CODECS else "copy"
        self.compress_level = compress_level if compress_level in COMPRESS_LEVELS else "medium"
        self.naming_mode = naming_mode if naming_mode in NAMING_MODES else "id"
        self._t = translate or translator("pt")
        self._cancel = False
        self._proc: subprocess.Popen | None = None
        self._stdout_tail: list[str] = []
        self._metadata_title = False

    # ------------------------------------------------------------------ API
    def cancel(self) -> None:
        """Solicita cancelamento (thread-safe: marca flag e mata o processo)."""
        self._cancel = True
        proc = self._proc
        if proc is not None:
            terminate_tree(proc)

    # ----------------------------------------------------- ponto de entrada
    def run(self) -> None:
        result: object = ""
        try:
            self.statusChanged.emit(Status.ANALYZING.value)
            self.progressChanged.emit(0.0, "—", "—")
            log.info("INICIO url=%s outdir=%s", self.url, self.outdir)

            if not self._cancel:
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
            self.statusChanged.emit(Status.ANALYZING.value)
            self.progressChanged.emit(0.0, "—", "—")
            candidate = HtmlMediaScraper(USER_AGENT).find(self.url)
            log.info("scraper: candidate=%r", candidate)
            if self._cancel:
                self.cancelled.emit(self.url)
                self.finished.emit()
                return
            if not candidate:
                msg = result if isinstance(result, str) else self._t("err_download")
                self.failed.emit(self.url, self._t("err_no_stream", msg=msg))
                self.finished.emit()
                return

            # ---- Tentativa secundária: yt-dlp no link bruto ----
            ok2, result2 = self._run_ytdlp(candidate, referer=self.url)
            log.info("yt-dlp no link raspado: ok=%s result=%r", ok2, result2)
            if ok2:
                self._succeed(result2)
                return
            if self._cancel:
                self.cancelled.emit(self.url)
                self.finished.emit()
                return

            # ---- Tentativa final: ffmpeg direto no m3u8 ----
            if ".m3u8" in candidate.lower() and self.use_ffmpeg_hls and not self._cancel:
                ok3, result3 = self._run_ffmpeg(candidate)
                log.info("ffmpeg fallback: ok=%s result=%r", ok3, result3)
                if ok3:
                    self._succeed(result3)
                    return
                base = result2 if isinstance(result2, str) else self._t("err_download")
                self.failed.emit(self.url, f"{base} | ffmpeg: {result3}")
                self.finished.emit()
                return

            self.failed.emit(
                self.url, result2 if isinstance(result2, str) else self._t("err_download")
            )
            self.finished.emit()
        except Exception as exc:  # erro inesperado não pode matar a thread
            log.exception("erro inesperado no worker")
            self.failed.emit(self.url, self._t("err_unexpected", err=exc))
            self.finished.emit()

    # --------------------------------------------------- download via yt-dlp
    def _output_template(self, target: str) -> tuple[str, str]:
        """Devolve ``(name_base, template)`` conforme o modo de nome escolhido.

        - ``id``: ``vid_<hash da URL>`` (estável, sem caracteres especiais);
        - ``title``: ``%(title).120B`` (título vindo da página/metadados; o
          yt-dlp sanitiza com ``--windows-filenames``).
        """
        name_base = f"vid_{url_digest(target)}"
        if self.naming_mode == "title":
            # O ID evita colisão entre vídeos diferentes com o mesmo título
            # (o yt-dlp com --no-overwrites pularia o segundo download).
            return name_base, os.path.join(
                self.outdir, "%(title).100B [%(id)s].%(ext)s"
            )
        return name_base, os.path.join(self.outdir, f"{name_base}.%(ext)s")

    def _format_args(self) -> list[str]:
        """Seleção de formato/qualidade/contêiner conforme o modo escolhido.

        - ``video_audio``: melhor vídeo + melhor áudio (padrão);
        - ``video_only``:  melhor vídeo, sem áudio;
        - ``audio_only``:  extrai somente o áudio no formato escolhido.

        ``quality`` limita a altura (ex.: ``1080``); ``best`` não limita.
        ``container`` define o contêiner de saída (mp4/mkv/webm/avi/mov ou
        formato de áudio como mp3/m4a/flac).
        """
        if self.format_mode == "audio_only":
            return [
                "-f", "ba/b",
                "-x", "--audio-format", self.container,
                "--audio-quality", "0",
            ]
        height = "" if self.quality in ("", "best") else f"[height<={self.quality}]"
        if self.format_mode == "video_only":
            # Sem o fallback /b: ele pode ser um formato combinado com áudio
            # e violaria a escolha "apenas vídeo". Se não existir vídeo puro,
            # o yt-dlp reporta erro — melhor que entregar o arquivo errado.
            selector = f"bv*{height}"
        elif height:
            # O fallback também respeita a altura escolhida. Antes, /b podia
            # baixar 4K mesmo com 1080p selecionado.
            selector = f"bv*{height}+ba/b{height}"
        else:
            selector = "bv*+ba/b"
        return [
            "-f", selector,
            "--merge-output-format", self.container,
            "--remux-video", self.container,
        ]

    def _find_media_in_html(self) -> str | None:
        """Compat: raspa o HTML da URL original (usado por scripts/testes)."""
        return HtmlMediaScraper(USER_AGENT).find(self.url)

    def _ytdlp_argv(self) -> list[str] | None:
        """Escolhe como executar o yt-dlp.

        Em ambiente de desenvolvimento prefere o módulo ``yt_dlp`` (atualizável
        via pip). Em build empacotado, ``sys.executable`` é o próprio app (não é
        Python), então usamos sempre o binário autônomo baixado no PATH.
        """
        if not config.is_frozen():
            try:
                import yt_dlp  # noqa: F401

                return [sys.executable, "-m", "yt_dlp"]
            except ImportError:
                pass
        binary = which("yt-dlp")
        return [binary] if binary else None

    def _run_ytdlp(self, target: str, referer: str | None = None) -> tuple[bool, str]:
        """Executa yt-dlp em subprocesso e repassa o progresso pela GUI."""
        base_argv = self._ytdlp_argv()
        if not base_argv:
            return False, self._t("err_ytdlp_missing")

        os.makedirs(self.outdir, exist_ok=True)
        # Nome curto/estável (hash) ou título da própria página/metadados.
        name_base, out_template = self._output_template(target)

        cmd = base_argv + [
            "--newline",
            "--progress",
            "--no-playlist",
            "--no-mtime",
            "--no-overwrites",
            "--windows-filenames",
            "--retries",
            "3",
            "--fragment-retries",
            "5",
            "--socket-timeout",
            "20",
            "--concurrent-fragments",
            str(self.fragments),
        ]
        cmd += self._format_args()
        cmd += [
            # Título real da página/metadados; usado só para exibição,
            # independentemente do modo de nome do arquivo.
            "--print",
            f"before_dl:{TITLE_PREFIX}%(title)s",
            "--print",
            "after_move:filepath",
            "-o",
            out_template,
            "--user-agent",
            USER_AGENT,
        ]
        if self.limit_rate:
            cmd += ["--limit-rate", self.limit_rate]
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

        # Bloqueio de segurança do yt-dlp (CVE-2024-38519): URLs com extensão
        # incomum (.php, .aspx, ...) são recusadas mesmo com vídeo legítimo.
        # Retenta UMA vez com allow-unsafe-ext e extensão .mp4 forçada.
        log.warning("extensão incomum detectada (%r) — retry allow-unsafe-ext", msg[:200])
        retry_cmd = cmd.copy()
        retry_cmd += ["--compat-options", "allow-unsafe-ext"]
        try:
            i = retry_cmd.index("-o")
            forced_ext = "." + self.container.lstrip(".")
            retry_cmd[i + 1] = os.path.join(self.outdir, f"{name_base}{forced_ext}")
        except ValueError:
            pass
        ok2, msg2 = self._run_process(retry_cmd)
        if ok2 and isinstance(msg2, str) and os.path.isfile(msg2):
            if self._looks_like_non_video(msg2):
                log.warning("retry baixou conteúdo não-vídeo — descartando: %s", msg2)
                try:
                    os.remove(msg2)
                except OSError:
                    pass
                return False, msg
        return ok2, msg2

    def _build_cookies_args(self) -> list[str]:
        """Converte a configuração de cookies em argumentos do yt-dlp.

        ``"browser:<nome>"`` -> ``--cookies-from-browser``;
        ``"file:<caminho>"`` -> ``--cookies``; ``""`` -> sem cookies.
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
    def _ffmpeg_cookie_header(self) -> str:
        """Converte cookies.txt Netscape em ``name=value; ...`` para ffmpeg."""
        if not self.cookies.startswith("file:"):
            return ""
        path = self.cookies[len("file:"):].strip()
        if not path or not os.path.isfile(path):
            return ""
        pairs: list[str] = []
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if not line.strip() or line.startswith("#"):
                        continue
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 7 and parts[5] and parts[6]:
                        pairs.append(f"{parts[5]}={parts[6]}")
        except OSError:
            return ""
        return "; ".join(pairs)

    def _run_ffmpeg(self, media_url: str) -> tuple[bool, str]:
        """Fallback final via ffmpeg, respeitando modo/contêiner/referer."""
        ffmpeg = which("ffmpeg")
        if not ffmpeg:
            return False, self._t("err_ffmpeg_missing")

        digest = url_digest(media_url)
        audio_only = self.format_mode == "audio_only"
        if audio_only:
            container = (
                self.container if self.container in AUDIO_CONTAINERS
                else DEFAULT_AUDIO_CONTAINER
            )
        else:
            container = self.container or DEFAULT_VIDEO_CONTAINER
            if container not in ("mp4", "mkv", "webm", "mov", "avi"):
                container = "mp4"
        prefix = "vid" if self.naming_mode == "id" else "hls"
        out_path = os.path.join(self.outdir, f"{prefix}_{digest}.{container}")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return True, out_path  # já baixado antes

        duration = probe_duration(media_url)
        http_args = ["-user_agent", USER_AGENT]
        if self.url.startswith(("http://", "https://")):
            http_args += ["-referer", self.url]
        cookie_header = self._ffmpeg_cookie_header()
        if cookie_header:
            http_args += ["-cookies", cookie_header]

        last_error = "desconhecido"
        if audio_only:
            codec = {
                "mp3": "libmp3lame", "m4a": "aac", "wav": "pcm_s16le",
                "flac": "flac", "opus": "libopus",
            }.get(container, "aac")
            cmd = (
                [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
                + http_args
                + ["-i", media_url, "-vn", "-c:a", codec, out_path]
            )
            ok, last_error = self._run_process(
                cmd, duration=duration, is_ffmpeg=True
            )
            if not ok:
                try:
                    os.remove(out_path)
                except OSError:
                    pass
            return ok, out_path if ok else last_error

        # Copiar direto; recodificar áudio; recodificar tudo. Em "apenas
        # vídeo" todas as receitas usam -an.
        video_codec = "libvpx-vp9" if container == "webm" else "libx264"
        audio_codec = "libopus" if container == "webm" else "aac"
        if self.format_mode == "video_only":
            recipes = [
                ["-c", "copy", "-an"],
                ["-c:v", "copy", "-an"],
                ["-c:v", video_codec, "-preset", "veryfast", "-an"],
            ]
        else:
            bsf = ["-bsf:a", "aac_adtstoasc"] if container != "webm" else []
            recipes = [
                ["-c", "copy"] + bsf,
                ["-c:v", "copy", "-c:a", audio_codec] + bsf,
                ["-c:v", video_codec, "-preset", "veryfast", "-c:a", audio_codec],
            ]
        for recipe in recipes:
            if self._cancel:
                return False, self._t("err_cancelled")
            cmd = (
                [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
                + http_args
                + ["-i", media_url]
                + recipe
                + [out_path]
            )
            ok, last_error = self._run_process(cmd, duration=duration, is_ffmpeg=True)
            if ok:
                return True, out_path
            if self._cancel:
                return False, self._t("err_cancelled")
            try:
                os.remove(out_path)
            except OSError:
                pass
        return False, last_error

    # ----------------------------------------------------- executor genérico
    def _run_process(
        self,
        cmd: list[str],
        duration: float | None = None,
        is_ffmpeg: bool = False,
    ) -> tuple[bool, str]:
        """Roda um subprocesso, parseia o progresso e retorna (ok, mensagem)."""
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **spawn_kwargs(),
        )

        stderr_lines: list[str] = []
        line_queue: queue.Queue[str] = queue.Queue()

        def _drain_stderr() -> None:
            for raw in self._proc.stderr:
                line = raw.rstrip("\n")
                stderr_lines.append(line)
                line_queue.put(line)

        drainer = threading.Thread(target=_drain_stderr, daemon=True)
        drainer.start()

        result_msg = ""
        try:
            if is_ffmpeg:
                self._consume_ffmpeg_stderr(line_queue, duration)
            else:
                result_msg = self._consume_ytdlp_stdout(self._proc)
        finally:
            rc = self._wait_or_kill(self._proc, timeout=10)
            drainer.join(timeout=2)
            self._proc = None

        if self._cancel:
            if is_ffmpeg:
                self._safe_remove(cmd[-1])
            else:
                self._cleanup_temp_files(result_msg)
            return False, self._t("err_cancelled")

        if rc != 0:
            if stderr_lines:
                log.error("rc=%s | stderr:\n%s", rc, "\n".join(stderr_lines[-15:]))
            else:
                log.error("rc=%s | stdout final: %r", rc, result_msg[-500:])
            if is_ffmpeg:
                self._safe_remove(cmd[-1])
            else:
                self._cleanup_temp_files(result_msg)
            if stderr_lines:
                errors = [
                    line for line in stderr_lines
                    if "error" in line.lower() or "ERROR" in line
                ]
                msg = errors[-1] if errors else stderr_lines[-1]
                return False, msg.strip()
            return False, result_msg or self._t("err_process_code", code=rc)

        if is_ffmpeg:
            if os.path.exists(cmd[-1]):
                return True, cmd[-1]
            log.warning("ffmpeg rc=0 sem arquivo; stderr:\n%s", "\n".join(stderr_lines[-12:]))
            return False, self._t("err_ffmpeg_no_output")
        if result_msg:
            real = resolve_existing_file(result_msg)
            if real:
                if real != result_msg:
                    log.warning("caminho impresso != arquivo real; resolvido: %r", real)
                if self.naming_mode != "title":
                    real = shorten_name(real)
                return True, real
        log.warning(
            "yt-dlp rc=0 sem arquivo detectado; stdout:\n%s",
            "\n".join(self._stdout_tail[-12:]) or "(vazio)",
        )
        return False, result_msg or self._t("err_ytdlp_no_output")

    @staticmethod
    def _wait_or_kill(proc: subprocess.Popen, timeout: float = 10.0) -> int:
        """Espera o processo, mas nunca fica bloqueado para sempre.

        ``terminate_tree`` pode falhar (taskkill sem permissão, processo
        zumbi, etc.). Nesse caso tentamos ``kill`` e, se ainda assim o
        processo não morrer, retornamos -1 para o worker conseguir sair.
        """
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            terminate_tree(proc)
        try:
            return proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                return proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.error("processo %s não terminou após kill", proc.pid)
                return -1

    @staticmethod
    def _safe_remove(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    def _looks_like_non_video(self, path: str) -> bool:
        """True se o arquivo baixado for HTML ou playlist HLS crua."""
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

    def _consume_ytdlp_stdout(self, proc) -> str:
        """Lê o stdout do yt-dlp e emite sinais de progresso."""
        out_path: str | None = None
        for line in proc.stdout:
            if self._cancel:
                terminate_tree(proc)
                break
            line = line.strip()
            if not line:
                continue
            self._stdout_tail.append(line)
            if len(self._stdout_tail) > 40:
                self._stdout_tail.pop(0)
            if line.startswith(TITLE_PREFIX):
                title = line[len(TITLE_PREFIX):].strip()
                if title:
                    self._metadata_title = True
                    self.titleChanged.emit(title)
                continue
            m = PROGRESS_RE.search(line)
            if m:
                pct = min(100.0, float(m.group(1)))
                size = m.group(2)
                speed = m.group(3) or "—"
                self.statusChanged.emit(Status.DOWNLOADING.value)
                self.progressChanged.emit(pct, speed, size)
                continue
            if os.path.isabs(line):
                out_path = line.strip()
                if not self._metadata_title:
                    self.titleChanged.emit(os.path.basename(out_path))
                continue
            dm = re.search(r"\[download\] Destination: (.+)", line)
            if dm:
                out_path = dm.group(1).strip()
                if not self._metadata_title:
                    self.titleChanged.emit(os.path.basename(out_path))
                continue
            skip = re.search(r"\[download\] (.+?) has already been downloaded", line)
            if skip:
                out_path = skip.group(1).strip()
                continue
            mm = re.search(r"\[(?:Merger|VideoMerge|Mux)\]\s*Merging formats into \"(.+)\"", line)
            if mm:
                out_path = mm.group(1).strip()
                self.titleChanged.emit(os.path.basename(out_path))
        return out_path or ""

    def _consume_ffmpeg_stderr(self, line_queue: queue.Queue[str], duration) -> None:
        """Consome o stderr do ffmpeg por fila (sem busy-wait).

        Detecta travamento: se nenhuma linha nova chega por
        ``FFMPEG_STALL_TIMEOUT`` segundos com o processo vivo, encerra.
        """
        self.statusChanged.emit(Status.DOWNLOADING.value)
        last_time = 0.0
        last_activity = time.time()
        while True:
            if self._cancel:
                proc = self._proc
                if proc is not None:
                    terminate_tree(proc)
                break
            try:
                line = line_queue.get(timeout=0.25)
                last_activity = time.time()
            except queue.Empty:
                proc = self._proc
                if proc is None or proc.poll() is not None:
                    break
                if time.time() - last_activity > FFMPEG_STALL_TIMEOUT:
                    log.warning("ffmpeg sem progresso por %.0fs — encerrando", FFMPEG_STALL_TIMEOUT)
                    terminate_tree(proc)
                    break
                continue
            tm = FFMPEG_TIME_RE.search(line)
            if not tm:
                continue
            h, m_, s = tm.groups()
            t = int(h) * 3600 + int(m_) * 60 + float(s)
            if t >= last_time:
                last_time = t
            pct = (last_time / duration * 100.0) if duration else 0.0
            sm = FFMPEG_SIZE_RE.search(line)
            self.progressChanged.emit(
                min(99.0, pct), f"{last_time:.1f}s", sm.group(1) if sm else "—"
            )

    # -------------------------------------------------- conclusão e miniatura
    def _maybe_compress(self, path: str) -> str | None:
        """Reencoda para H.264/H.265 se configurado.

        Retorna o caminho final (original ou comprimido) ou ``None`` se o
        usuário cancelou durante a compressão. Em falha de reencode, mantém o
        arquivo original (o download não é perdido).
        """
        if self.codec not in ("h264", "h265") or self.format_mode == "audio_only":
            return path
        if not path or not os.path.isfile(path):
            return path
        if self._cancel:
            return None
        ffmpeg = which("ffmpeg")
        if not ffmpeg:
            return path

        container = self.container if self.container in ("mp4", "mkv", "mov", "avi") else "mkv"
        if self.codec == "h265" and container == "avi":
            container = "mkv"  # HEVC em AVI é mal suportado
        base, _ = os.path.splitext(path)
        out = f"{base}_{self.codec}.{container}"
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out

        crf = CRF.get(self.codec, {}).get(self.compress_level, 23)
        vcodec = "libx264" if self.codec == "h264" else "libx265"
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-i", path,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", vcodec, "-preset", "medium", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "192k",
            "-map_metadata", "0", "-map_chapters", "0",
            "-max_muxing_queue_size", "4096",
        ]
        # Preserva legendas de texto. MP4/MOV não aceitam PGS/DVD bitmap;
        # nesse caso copiamos tudo só no MKV, onde qualquer codec é válido.
        probe = probe_media(path) or {}
        _videos, _audios, subs, _duration = analyze(probe)
        text_subs = [
            index for index, sub in enumerate(subs)
            if (sub.get("codec_name") or "").lower() in TEXT_SUBS
        ]
        if container in ("mp4", "mov") and text_subs:
            for index in text_subs:
                cmd += ["-map", f"0:s:{index}"]
            cmd += ["-c:s", "mov_text", "-movflags", "+faststart"]
        elif container == "mkv" and subs:
            cmd += ["-map", "0:s?", "-c:s", "copy"]
        else:
            cmd += ["-sn"]
        if self.codec == "h265":
            cmd += ["-tag:v", "hvc1"]
        cmd.append(out)

        duration = probe_duration(path)
        self.statusChanged.emit(Status.ENCODING.value)
        ok, err = self._run_process(cmd, duration=duration, is_ffmpeg=True)
        if self._cancel:
            return None
        if ok and os.path.exists(out) and os.path.getsize(out) > 0:
            # O arquivo original é preservado. A versão recomprimida ganha
            # sufixo _h264/_h265; quem quiser substituir pode usar a aba
            # Compressão (que tem a opção explícita de apagar o original).
            log.info(
                "comprimido (%s/%s): %s -> %s (original mantido)",
                self.codec, self.compress_level, path, out,
            )
            return out
        log.warning("compressão falhou (%s) — mantendo original", err)
        self._safe_remove(out)
        return path

    def _succeed(self, path: str) -> None:
        compressed = self._maybe_compress(path)
        if compressed is None:  # cancelado durante a compressão
            self.cancelled.emit(self.url)
            self.finished.emit()
            return
        path = compressed
        try:
            thumb = extract_thumbnail(path)
        except Exception:
            thumb = None
        if thumb:
            self.thumbnailReady.emit(thumb)
        self.succeeded.emit(self.url, path)
        self.finished.emit()
