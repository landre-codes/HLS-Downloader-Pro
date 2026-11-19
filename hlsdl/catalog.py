"""SQLite catalog for media identity, hashes, validation and job history.

Sidecars remain the portable source of truth next to each file.  The catalog is
the fast index: lookup by stable ``source_key``, SHA-256/BLAKE3, path or state,
plus validation history for the UI.  Connections are opened per operation so
worker threads and the GUI can share the same file safely (WAL mode).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass

from . import config
from .integrity import CompletionRecord

log = logging.getLogger("hlsdl")

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT UNIQUE,
    kind TEXT,
    canonical_url TEXT,
    duration REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_tracks TEXT,
    manifest_hash TEXT,
    created_at REAL,
    last_seen REAL
);
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    media_id INTEGER,
    kind TEXT,
    size INTEGER,
    sha256 TEXT,
    blake3 TEXT,
    phash TEXT,
    validation TEXT,
    probe_json TEXT,
    created_at REAL,
    FOREIGN KEY(media_id) REFERENCES media(id)
);
CREATE INDEX IF NOT EXISTS idx_files_sha ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_blake3 ON files(blake3);
CREATE INDEX IF NOT EXISTS idx_media_source ON media(source_key);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    output TEXT,
    stage TEXT,
    journal TEXT,
    error TEXT,
    created_at REAL,
    updated_at REAL
);
"""

# Migrações incrementais. A chave é a versão de destino; cada função deve ser
# idempotente o suficiente para rodar uma única vez dentro da transação.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def _apply_migrations(connection: sqlite3.Connection) -> None:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0] or 0)
    if version > SCHEMA_VERSION:
        log.warning(
            "catálogo com schema %s mais novo que o suportado (%s); "
            "nenhuma migração será aplicada",
            version,
            SCHEMA_VERSION,
        )
        return
    if version == 0:
        connection.executescript(SCHEMA)
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return
    for target in range(version + 1, SCHEMA_VERSION + 1):
        migration = MIGRATIONS.get(target)
        if migration is not None:
            migration(connection)
        connection.execute(f"PRAGMA user_version={target}")


@dataclass
class CatalogEntry:
    path: str
    source_key: str = ""
    kind: str = ""
    size: int = 0
    sha256: str = ""
    blake3: str = ""
    validation: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> CatalogEntry:
        return cls(
            path=str(row["path"] or ""),
            source_key=str(row["source_key"] or ""),
            kind=str(row["kind"] or ""),
            size=int(row["size"] or 0),
            sha256=str(row["sha256"] or ""),
            blake3=str(row["blake3"] or ""),
            validation=str(row["validation"] or ""),
            duration=float(row["duration"] or 0),
            width=int(row["width"] or 0),
            height=int(row["height"] or 0),
            video_codec=str(row["video_codec"] or ""),
        )


class Catalog:
    def __init__(self, path: str | None = None):
        self.path = path or config.catalog_path()
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        folder = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(folder, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        # Necessário em cada conexão; sem isso a FK declarada em ``files`` não
        # é aplicada pelo SQLite.
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        try:
            with self._connect() as connection:
                _apply_migrations(connection)
        except sqlite3.Error:
            log.exception("falha ao inicializar catálogo %s", self.path)

    def schema_version(self) -> int:
        try:
            with self._connect() as connection:
                return int(connection.execute("PRAGMA user_version").fetchone()[0] or 0)
        except sqlite3.Error:
            return 0

    def register(self, record: CompletionRecord, kind: str = "") -> None:
        """Index a completion sidecar (media + file rows)."""
        summary = record.summary or {}
        video = summary.get("video") or {}
        audios = summary.get("audio") or []
        kind = kind or str((record.extra or {}).get("kind") or "")
        identity = (record.extra or {}).get("identity") or {}
        manifest_hash = str(
            (record.extra or {}).get("manifest_hash")
            or identity.get("manifest_hash") or ""
        )
        try:
            with self._connect() as connection:
                now = time.time()
                connection.execute(
                    """
                    INSERT INTO media (source_key, kind, canonical_url, duration,
                                       width, height, video_codec, audio_tracks,
                                       manifest_hash, created_at, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_key) DO UPDATE SET
                        canonical_url=excluded.canonical_url,
                        duration=excluded.duration,
                        width=excluded.width,
                        height=excluded.height,
                        video_codec=excluded.video_codec,
                        audio_tracks=excluded.audio_tracks,
                        last_seen=excluded.last_seen
                    """,
                    (
                        record.source_key or record.media_path,
                        kind,
                        record.source_url,
                        record.duration,
                        int(video.get("width") or 0),
                        int(video.get("height") or 0),
                        str(video.get("codec") or ""),
                        json.dumps(audios, ensure_ascii=False),
                        manifest_hash,
                        now,
                        now,
                    ),
                )
                media_id = connection.execute(
                    "SELECT id FROM media WHERE source_key = ?",
                    (record.source_key or record.media_path,),
                ).fetchone()["id"]
                connection.execute(
                    """
                    INSERT INTO files (path, media_id, kind, size, sha256, blake3,
                                       phash, validation, probe_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        media_id=excluded.media_id,
                        size=excluded.size,
                        sha256=excluded.sha256,
                        blake3=excluded.blake3,
                        validation=excluded.validation,
                        probe_json=excluded.probe_json
                    """,
                    (
                        os.path.abspath(record.media_path),
                        media_id,
                        kind,
                        record.size,
                        record.sha256,
                        str((record.extra or {}).get("blake3") or ""),
                        str((record.extra or {}).get("phash") or ""),
                        record.validation,
                        json.dumps(summary, ensure_ascii=False),
                        now,
                    ),
                )
        except sqlite3.Error:
            log.exception("falha ao registrar %s no catálogo", record.media_path)

    def find_by_source(self, source_key: str, kind: str = "") -> CatalogEntry | None:
        if not source_key:
            return None
        query = (
            "SELECT f.*, m.source_key, m.duration, m.width, m.height, m.video_codec "
            "FROM files f JOIN media m ON m.id = f.media_id "
            "WHERE m.source_key = ?"
        )
        params: list = [source_key]
        if kind:
            query += " AND f.kind = ?"
            params.append(kind)
        query += " ORDER BY f.created_at DESC LIMIT 1"
        try:
            with self._connect() as connection:
                row = connection.execute(query, params).fetchone()
                return CatalogEntry.from_row(row) if row else None
        except sqlite3.Error:
            return None

    def find_by_hash(self, digest: str, algorithm: str = "sha256") -> CatalogEntry | None:
        if not digest:
            return None
        column = "blake3" if algorithm == "blake3" else "sha256"
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT f.*, m.source_key, m.duration, m.width, m.height, m.video_codec "
                    "FROM files f JOIN media m ON m.id = f.media_id "
                    f"WHERE lower(f.{column}) = lower(?) LIMIT 1",
                    (digest,),
                ).fetchone()
                return CatalogEntry.from_row(row) if row else None
        except sqlite3.Error:
            return None

    def recent(self, limit: int = 100) -> list[CatalogEntry]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT f.*, m.source_key, m.duration, m.width, m.height, m.video_codec "
                    "FROM files f JOIN media m ON m.id = f.media_id "
                    "ORDER BY f.created_at DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
                return [CatalogEntry.from_row(row) for row in rows]
        except sqlite3.Error:
            return []

    def prune_missing(self) -> int:
        removed = 0
        try:
            with self._connect() as connection:
                rows = connection.execute("SELECT path FROM files").fetchall()
                for row in rows:
                    path = str(row["path"])
                    if not os.path.isfile(path):
                        connection.execute("DELETE FROM files WHERE path = ?", (path,))
                        removed += 1
        except sqlite3.Error:
            log.exception("falha ao limpar catálogo")
        return removed

    def stats(self) -> dict:
        try:
            with self._connect() as connection:
                media = connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
                files = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                jobs = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            return {"media": int(media), "files": int(files), "jobs": int(jobs)}
        except sqlite3.Error:
            return {"media": 0, "files": 0, "jobs": 0}
