"""Transactional file integrity, completion records and crash recovery.

Design goals
------------
* A finished media file is only ``DONE`` when it has a sidecar proving what it
  is (probe summary + hash) and that it still matches.
* Compression never destroys the original on failure, hash mismatch, power
  loss or an audio/subtitle integration problem.
* Every destructive install has a journal and a backup.  Journals are replayed
  on startup, so a crash between ``os.replace`` and bookkeeping is recoverable.
* Paths for parallel jobs are reserved in-process, preventing two encoders from
  writing the same ``.part``/final file.
"""

from __future__ import annotations

import errno
import glob
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from .media import analyze, media_summary, probe_media

try:  # Optional fast hash. SHA-256 remains the mandatory fallback.
    import blake3 as _blake3
except ImportError:  # pragma: no cover - environment without blake3
    _blake3 = None

log = logging.getLogger("hlsdl")

SIDECAR_SUFFIX = ".hlsdl.json"
JOURNAL_SUFFIX = ".hlsdl-job.json"
CHUNK = 1024 * 1024
# Sidecars são opcionais: o catálogo SQLite continua sendo a fonte central.
_SIDECARS_ENABLED = True
_RESERVED: set[str] = set()
_RESERVE_LOCK = None  # created lazily to keep import-time side effects tiny


def set_sidecars_enabled(enabled: bool) -> None:
    global _SIDECARS_ENABLED
    _SIDECARS_ENABLED = bool(enabled)


def sidecars_enabled() -> bool:
    return _SIDECARS_ENABLED


def cleanup_sidecars(directory: str) -> int:
    """Remove todos os ``*.hlsdl.json`` abaixo de ``directory``."""
    removed = 0
    if not directory or not os.path.isdir(directory):
        return 0
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if not name.endswith(SIDECAR_SUFFIX):
                continue
            path = os.path.join(root, name)
            try:
                os.remove(path)
                removed += 1
            except OSError:
                log.warning("falha ao remover sidecar: %s", path)
    return removed


def _lock():
    global _RESERVE_LOCK
    if _RESERVE_LOCK is None:
        import threading

        _RESERVE_LOCK = threading.Lock()
    return _RESERVE_LOCK


# ---------------------------------------------------------------------------
# Hashing / fsync
# ---------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blake3_file(path: str) -> str:
    """BLAKE3 digest when the optional module is installed, else ``""``."""
    if _blake3 is None:
        return ""
    digest = _blake3.blake3()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_hash(path: str, sample: int = 1024 * 1024) -> str:
    """Hash size + first/last sample; cheap guard against modifications."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return ""
    digest = hashlib.sha256()
    digest.update(str(size).encode("ascii"))
    try:
        with open(path, "rb") as handle:
            digest.update(handle.read(sample))
            if size > 2 * sample:
                handle.seek(max(0, size - sample))
                digest.update(handle.read(sample))
    except OSError:
        return ""
    return digest.hexdigest()


def fsync_file(path: str) -> None:
    try:
        with open(path, "rb") as handle:
            os.fsync(handle.fileno())
    except OSError:
        # Some network filesystems reject fsync; the atomic replace still
        # gives the best available guarantee there.
        pass


def fsync_dir(path: str) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_replace(source: str, destination: str, retries: int = 4) -> None:
    """Replace with retries and a copy fallback (Windows locks/network shares).

    Antivirus/indexers commonly hold a handle for a few hundred milliseconds.
    A failed ``os.replace`` must never destroy the source temp before the
    destination is safely written.
    """
    last_error: OSError | None = None
    for attempt in range(retries):
        try:
            os.replace(source, destination)
            return
        except OSError as exc:
            last_error = exc
            # EXDEV and some SMB shares reject rename; copy is the safe path.
            if getattr(exc, "errno", None) == errno.EXDEV:
                break
            time.sleep(0.15 * (attempt + 1))
    if last_error is not None and os.path.exists(source):
        try:
            shutil.copy2(source, destination)
            fsync_file(destination)
            os.remove(source)
            return
        except OSError:
            pass
    if last_error is not None:
        raise last_error


def _hide_generated_file(path: str) -> None:
    """Oculta sidecars/journals no Explorer do Windows.

    Os arquivos continuam ao lado da m?dia (portabilidade e verifica??o),
    mas n?o poluem a pasta para o usu?rio comum.
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs != -1:
            ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs | 0x2)
    except Exception:
        pass


def write_json_atomic(path: str, data: dict) -> None:
    """Write JSON with a temp file + replace + fsync."""
    folder = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(folder, exist_ok=True)
    temp = f"{path}.{uuid.uuid4().hex}.tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    atomic_replace(temp, path)
    fsync_dir(folder)
    _hide_generated_file(path)


def read_json(path: str) -> dict | None:
    _hide_generated_file(path)
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def disk_space_ok(folder: str, required_bytes: int) -> tuple[bool, int]:
    try:
        usage = shutil.disk_usage(folder)
        return usage.free >= max(0, required_bytes), usage.free
    except OSError:
        return True, 0


# ---------------------------------------------------------------------------
# Completion records
# ---------------------------------------------------------------------------
def sidecar_path(media_path: str, *, posix: bool | None = None) -> str:
    """Caminho do sidecar; em POSIX usa ponto inicial para ficar oculto.

    O ponto não é usado no Windows (não teria efeito e quebraria a convenção
    existente). Sidecars antigos continuam legíveis via
    :func:`legacy_sidecar_path`.
    """
    hidden = (os.name != "nt") if posix is None else posix
    if not hidden:
        return media_path + SIDECAR_SUFFIX
    folder, name = os.path.split(media_path)
    return os.path.join(folder, "." + name + SIDECAR_SUFFIX)


def legacy_sidecar_path(media_path: str) -> str:
    return media_path + SIDECAR_SUFFIX


@dataclass
class CompletionRecord:
    media_path: str
    source_key: str = ""
    source_url: str = ""
    size: int = 0
    sha256: str = ""
    duration: float = 0.0
    summary: dict = field(default_factory=dict)
    validation: str = "ok"
    created_at: float = field(default_factory=time.time)
    ffmpeg_version: str = ""
    settings: dict = field(default_factory=dict)
    original_backup: str = ""
    extra: dict = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "media_path": self.media_path,
            "source_key": self.source_key,
            "source_url": self.source_url,
            "size": self.size,
            "sha256": self.sha256,
            "duration": self.duration,
            "summary": self.summary,
            "validation": self.validation,
            "created_at": self.created_at,
            "ffmpeg_version": self.ffmpeg_version,
            "settings": self.settings,
            "original_backup": self.original_backup,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict, media_path: str = "") -> CompletionRecord:
        return cls(
            media_path=str(data.get("media_path") or media_path),
            source_key=str(data.get("source_key") or ""),
            source_url=str(data.get("source_url") or ""),
            size=int(data.get("size") or 0),
            sha256=str(data.get("sha256") or ""),
            duration=float(data.get("duration") or 0),
            summary=data.get("summary") or {},
            validation=str(data.get("validation") or ""),
            created_at=float(data.get("created_at") or 0),
            ffmpeg_version=str(data.get("ffmpeg_version") or ""),
            settings=data.get("settings") or {},
            original_backup=str(data.get("original_backup") or ""),
            extra=data.get("extra") or {},
            version=int(data.get("version") or 1),
        )


def write_completion(media_path: str, record: CompletionRecord) -> str:
    if not sidecars_enabled():
        return ""
    record.media_path = os.path.abspath(media_path)
    path = sidecar_path(media_path)
    write_json_atomic(path, record.to_dict())
    return path


def read_completion(media_path: str) -> CompletionRecord | None:
    for path in (sidecar_path(media_path), legacy_sidecar_path(media_path)):
        data = read_json(path)
        if data:
            return CompletionRecord.from_dict(data, media_path)
    return None


def verify_completion(media_path: str, full_hash: bool = True,
                      expected_duration: float | None = None) -> tuple[bool, str]:
    """Verify sidecar + actual file.  Returns ``(ok, reason)``."""
    if not media_path or not os.path.isfile(media_path):
        return False, "missing_file"
    record = read_completion(media_path)
    if record is None:
        return False, "missing_sidecar"
    try:
        size = os.path.getsize(media_path)
    except OSError:
        return False, "missing_file"
    if record.size and size != record.size:
        return False, "size_mismatch"
    if full_hash and not record.sha256:
        return False, "missing_hash"
    if full_hash and record.sha256:
        try:
            actual = sha256_file(media_path)
        except OSError:
            return False, "hash_read_failed"
        if actual.lower() != record.sha256.lower():
            return False, "hash_mismatch"
        expected_blake = str((record.extra or {}).get("blake3") or "")
        if expected_blake and _blake3 is not None:
            try:
                actual_blake = blake3_file(media_path)
            except OSError:
                return False, "hash_read_failed"
            if actual_blake.lower() != expected_blake.lower():
                return False, "hash_mismatch"
    probe = probe_media(media_path)
    summary = media_summary(probe)
    if not summary.get("video") and not summary.get("audio"):
        return False, "unreadable_media"
    duration = float(summary.get("duration") or 0)
    reference = expected_duration if expected_duration is not None else record.duration
    if reference and duration:
        tolerance = max(1.5, 0.005 * reference)
        if abs(duration - reference) > tolerance:
            return False, "duration_mismatch"
    return True, "ok"


def find_completion_by_source(directory: str, source_key: str,
                              kind: str = "") -> str:
    """Return a media path whose sidecar has ``source_key`` (empty if none).

    This gives cross-session identity dedup without a database: sidecars are
    small and scoped to the output folder.  Callers must still verify the file.
    """
    if not source_key or not directory or not os.path.isdir(directory):
        return ""
    patterns = [
        os.path.join(directory, "*" + SIDECAR_SUFFIX),
        os.path.join(directory, ".*" + SIDECAR_SUFFIX),
    ]
    for pattern in patterns:
        for sidecar in glob.glob(pattern):
            data = read_json(sidecar)
            if not data or str(data.get("source_key") or "") != source_key:
                continue
            if kind and str((data.get("extra") or {}).get("kind") or "") != kind:
                continue
            name = os.path.basename(sidecar)
            media_name = name[1:] if name.startswith(".") else name
            media = os.path.join(
                os.path.dirname(sidecar),
                media_name[: -len(SIDECAR_SUFFIX)],
            )
            if os.path.isfile(media):
                return media
    return ""


def build_completion(media_path: str, source_key: str = "",
                     source_url: str = "", settings: dict | None = None,
                     original_backup: str = "", extra: dict | None = None) -> CompletionRecord:
    probe = probe_media(media_path)
    summary = media_summary(probe)
    try:
        size = os.path.getsize(media_path)
    except OSError:
        size = 0
    extra_data = dict(extra or {})
    if size and _blake3 is not None:
        extra_data.setdefault("blake3", blake3_file(media_path))
    return CompletionRecord(
        media_path=os.path.abspath(media_path),
        source_key=source_key,
        source_url=source_url,
        size=size,
        sha256=sha256_file(media_path) if size else "",
        duration=float(summary.get("duration") or 0),
        summary=summary,
        settings=settings or {},
        original_backup=original_backup,
        extra=extra_data,
    )


# ---------------------------------------------------------------------------
# Source guard
# ---------------------------------------------------------------------------
@dataclass
class FileGuard:
    path: str
    size: int
    mtime_ns: int
    sample_sha256: str

    @classmethod
    def capture(cls, path: str) -> FileGuard:
        try:
            stat = os.stat(path)
            return cls(
                path=os.path.abspath(path),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                sample_sha256=sample_hash(path),
            )
        except OSError:
            return cls(path=os.path.abspath(path), size=0, mtime_ns=0, sample_sha256="")

    def unchanged(self) -> tuple[bool, str]:
        try:
            stat = os.stat(self.path)
        except OSError:
            return False, "source_missing"
        if stat.st_size != self.size:
            return False, "source_size_changed"
        if stat.st_mtime_ns != self.mtime_ns:
            return False, "source_mtime_changed"
        if self.sample_sha256 and sample_hash(self.path) != self.sample_sha256:
            return False, "source_hash_changed"
        return True, "ok"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "sample_sha256": self.sample_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FileGuard:
        return cls(
            path=str(data.get("path") or ""),
            size=int(data.get("size") or 0),
            mtime_ns=int(data.get("mtime_ns") or 0),
            sample_sha256=str(data.get("sample_sha256") or ""),
        )


# ---------------------------------------------------------------------------
# Path reservation (in-process; the app is single-instance)
# ---------------------------------------------------------------------------
def reserve_output_path(src: str, codec: str, container: str,
                        suffix: str | None = None,
                        extra_reserved: set[str] | None = None) -> str:
    base, _ = os.path.splitext(src)
    suffix = suffix or codec
    reserved = extra_reserved or set()
    with _lock():
        candidate = f"{base}_{suffix}.{container}"
        index = 2
        while os.path.exists(candidate) or candidate in _RESERVED or candidate in reserved:
            candidate = f"{base}_{suffix}-{index}.{container}"
            index += 1
        _RESERVED.add(candidate)
        return candidate


def release_output_path(path: str) -> None:
    with _lock():
        _RESERVED.discard(path)


def reserved_paths() -> set[str]:
    with _lock():
        return set(_RESERVED)


# ---------------------------------------------------------------------------
# Backups and transactional install
# ---------------------------------------------------------------------------
def backup_path(source: str) -> str:
    folder, name = os.path.split(source)
    base, ext = os.path.splitext(name)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return os.path.join(folder, f"{base}.hlsdl-backup-{stamp}-{uuid.uuid4().hex[:6]}{ext}")


def create_backup(source: str) -> str:
    """Hard-link preferred (cheap), copy as fallback.  Source is never moved."""
    target = backup_path(source)
    try:
        os.link(source, target)
        fsync_dir(os.path.dirname(source) or ".")
        return target
    except (OSError, NotImplementedError):
        pass
    try:
        shutil.copy2(source, target)
        fsync_file(target)
        fsync_dir(os.path.dirname(source) or ".")
        return target
    except OSError:
        return ""


def restore_backup(backup: str, source: str) -> bool:
    if not backup or not os.path.isfile(backup):
        return False
    try:
        if os.path.exists(source):
            return True
        os.replace(backup, source)
        fsync_dir(os.path.dirname(source) or ".")
        return True
    except OSError:
        try:
            shutil.copy2(backup, source)
            fsync_file(source)
            return True
        except OSError:
            return False


# ---------------------------------------------------------------------------
# Job journal
# ---------------------------------------------------------------------------
@dataclass
class JobJournal:
    path: str
    data: dict

    @classmethod
    def create(cls, journal_dir: str, job_id: int | str, source: str,
               final: str, temp: str, *, settings: dict | None = None,
               source_guard: FileGuard | None = None) -> JobJournal:
        os.makedirs(journal_dir, exist_ok=True)
        path = os.path.join(journal_dir, f"{job_id}-{uuid.uuid4().hex[:10]}{JOURNAL_SUFFIX}")
        data = {
            "version": 1,
            "job_id": str(job_id),
            "source": os.path.abspath(source),
            "final": os.path.abspath(final),
            "temp": os.path.abspath(temp),
            "backup": "",
            "stage": "created",
            "created_at": time.time(),
            "pid": os.getpid(),
            "settings": settings or {},
            "source_guard": (source_guard or FileGuard.capture(source)).to_dict(),
            "expected_hash": "",
            "output_size": 0,
            "error": "",
        }
        journal = cls(path=path, data=data)
        journal.write()
        return journal

    @classmethod
    def load(cls, path: str) -> JobJournal | None:
        data = read_json(path)
        return cls(path=path, data=data) if data else None

    def write(self) -> None:
        write_json_atomic(self.path, self.data)

    def update(self, **values) -> None:
        self.data.update(values)
        self.write()

    def stage(self, stage: str, **values) -> None:
        self.data["stage"] = stage
        self.data.update(values)
        self.write()

    def finish(self) -> None:
        try:
            os.remove(self.path)
        except OSError:
            pass

    @property
    def source(self) -> str:
        return str(self.data.get("source") or "")

    @property
    def final(self) -> str:
        return str(self.data.get("final") or "")

    @property
    def temp(self) -> str:
        return str(self.data.get("temp") or "")

    @property
    def backup(self) -> str:
        return str(self.data.get("backup") or "")

    @property
    def stage_name(self) -> str:
        return str(self.data.get("stage") or "")

    def source_guard(self) -> FileGuard:
        return FileGuard.from_dict(self.data.get("source_guard") or {})


def journal_paths(directory: str) -> list[str]:
    try:
        return [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if name.endswith(JOURNAL_SUFFIX)
        ]
    except OSError:
        return []


def recover_journal(journal: JobJournal,
                    verify_cb: Callable[[str], tuple[bool, str]] | None = None) -> str:
    """Replay one journal safely.  Returns a short action code.

    We bias towards preservation: a partially written temp is discarded, a
    missing original is restored from backup, and a final file is kept only if
    it can be verified.
    """
    stage = journal.stage_name
    source, final, temp, backup = (
        journal.source, journal.final, journal.temp, journal.backup,
    )
    if stage in ("created", "encoding", "validating"):
        if temp and os.path.isfile(temp) and temp != final:
            try:
                os.remove(temp)
            except OSError:
                pass
        if source and not os.path.exists(source) and backup:
            restore_backup(backup, source)
        journal.finish()
        return "discarded_partial"
    if stage == "backing_up":
        if temp and os.path.isfile(temp) and temp != final:
            try:
                os.remove(temp)
            except OSError:
                pass
        if source and not os.path.exists(source) and backup:
            restore_backup(backup, source)
        journal.finish()
        return "restored_backup"
    if stage == "installing":
        if temp and os.path.isfile(temp) and temp != final:
            try:
                os.remove(temp)
            except OSError:
                pass
        valid = False
        expected = str(journal.data.get("expected_hash") or "")
        size = int(journal.data.get("output_size") or 0)
        if final and os.path.isfile(final):
            if expected:
                # The journal hash is stronger than a sidecar that may not
                # have been written before the crash.
                valid = (not size or os.path.getsize(final) == size)
                if valid:
                    try:
                        valid = sha256_file(final) == expected
                    except OSError:
                        valid = False
            elif verify_cb is not None:
                valid, _reason = verify_cb(final)
                if not valid:
                    # A missing sidecar should not discard a readable output;
                    # fall back to the media probe before rolling back.
                    videos, audios, _subs, _duration = analyze(probe_media(final))
                    valid = bool(videos or audios)
            else:
                valid = not size or (
                    size and os.path.getsize(final) == size
                )
        if valid:
            # The final output is good.  Keep the source and backup untouched;
            # the user can clean the backup when convenient.
            journal.finish()
            return "kept_installed"
        if final and os.path.isfile(final):
            try:
                os.remove(final)
            except OSError:
                pass
        if source and not os.path.exists(source) and backup:
            restore_backup(backup, source)
        journal.finish()
        return "rolled_back"
    if stage == "done":
        if temp and os.path.isfile(temp) and temp != final:
            try:
                os.remove(temp)
            except OSError:
                pass
        journal.finish()
        return "completed"
    journal.finish()
    return "unknown"


def recover_journals(directory: str,
                    verify_cb: Callable[[str], tuple[bool, str]] | None = None) -> list[dict]:
    results = []
    for path in journal_paths(directory):
        journal = JobJournal.load(path)
        if journal is None:
            try:
                os.remove(path)
            except OSError:
                pass
            continue
        try:
            action = recover_journal(journal, verify_cb)
        except Exception:
            log.exception("falha ao recuperar journal %s", path)
            action = "error"
        results.append({
            "journal": path,
            "source": journal.source,
            "final": journal.final,
            "action": action,
        })
    return results


def _same_path(first: str, second: str) -> bool:
    """Compara identidade de caminho (canônico e, se existir, no SO)."""
    if not first or not second:
        return False
    left = os.path.normcase(os.path.abspath(first))
    right = os.path.normcase(os.path.abspath(second))
    if left == right:
        return True
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def install_output(temp: str, final: str, source: str, *,
                   replace_original: bool, expected_hash: str,
                   journal: JobJournal,
                   expected_size: int = 0,
                   verify_final: Callable[[str], tuple[bool, str]] | None = None) -> str:
    """Atomically install ``temp`` as ``final`` with backup/rollback.

    Returns the backup path (empty when the original was not replaced).
    Raises on any verification failure, after restoring the original.
    """
    # Rejeita colisões ANTES de criar backup ou tocar em qualquer arquivo.
    # ``final == source`` faria o fluxo remover a saída recém-validada.
    if _same_path(final, source):
        raise RuntimeError("source_equals_final")
    if _same_path(temp, final):
        raise RuntimeError("temp_equals_final")
    if _same_path(temp, source):
        raise RuntimeError("temp_equals_source")
    backup = ""
    guard = journal.source_guard()
    ok, reason = guard.unchanged()
    if not ok:
        raise RuntimeError(reason)
    if replace_original:
        backup = create_backup(source)
        if not backup:
            raise RuntimeError("backup_failed")
        journal.stage("backing_up", backup=backup)

    journal.stage("installing", expected_hash=expected_hash, output_size=expected_size)
    try:
        atomic_replace(temp, final)
        try:
            if os.path.exists(temp):
                os.remove(temp)
        except OSError:
            pass
        fsync_file(final)
        fsync_dir(os.path.dirname(final) or ".")
    except Exception:
        if backup:
            restore_backup(backup, source)
        raise

    # Verify the installed bytes, not just the temp file.
    if expected_size and os.path.getsize(final) != expected_size:
        _rollback(final, backup, source)
        raise RuntimeError("installed_size_mismatch")
    if expected_hash:
        actual = sha256_file(final)
        if actual.lower() != expected_hash.lower():
            _rollback(final, backup, source)
            raise RuntimeError("installed_hash_mismatch")
    if verify_final is not None:
        valid, reason = verify_final(final)
        if not valid:
            _rollback(final, backup, source)
            raise RuntimeError(f"installed_invalid:{reason}")

    if replace_original:
        try:
            os.remove(source)
        except OSError as exc:
            journal.update(error=f"source_remove_failed:{exc}")
    journal.stage("done", backup=backup)
    return backup


def _rollback(final: str, backup: str, source: str) -> None:
    try:
        if final and os.path.isfile(final):
            os.remove(final)
    except OSError:
        pass
    if backup:
        restore_backup(backup, source)


def ffmpeg_version() -> str:
    from .services.procutils import popen_kwargs, which

    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return ""
    try:
        import subprocess

        result = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace", **popen_kwargs(),
        )
        lines = (result.stdout or "").splitlines()
        return lines[0].replace("ffmpeg version ", "").split(" ")[0] if lines else ""
    except Exception:
        return ""
