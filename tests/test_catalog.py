"""Catalog indexing/lookup tests."""

from __future__ import annotations

from hlsdl.catalog import Catalog
from hlsdl.integrity import CompletionRecord


def test_catalog_registers_and_finds_by_source_and_hash(tmp_path):
    catalog = Catalog(str(tmp_path / "catalog.sqlite3"))
    media = tmp_path / "video.mp4"
    media.write_bytes(b"content")
    record = CompletionRecord(
        media_path=str(media),
        source_key="youtube:abc",
        source_url="https://youtu.be/abc",
        size=7,
        sha256="a" * 64,
        duration=10.0,
        summary={
            "duration": 10.0,
            "video": {"width": 320, "height": 240, "codec": "h264"},
            "audio": [{"codec": "aac", "channels": 2}],
        },
        extra={"kind": "download", "blake3": "b" * 64},
    )
    catalog.register(record)
    by_source = catalog.find_by_source("youtube:abc")
    assert by_source is not None
    assert by_source.path == str(media)
    assert by_source.width == 320
    by_hash = catalog.find_by_hash("a" * 64)
    assert by_hash is not None and by_hash.source_key == "youtube:abc"
    by_blake = catalog.find_by_hash("b" * 64, algorithm="blake3")
    assert by_blake is not None and by_blake.path == str(media)
    stats = catalog.stats()
    assert stats["media"] == 1 and stats["files"] == 1


def test_catalog_prunes_missing_files(tmp_path):
    catalog = Catalog(str(tmp_path / "catalog.sqlite3"))
    media = tmp_path / "gone.mp4"
    media.write_bytes(b"x")
    catalog.register(CompletionRecord(media_path=str(media), source_key="k"))
    media.unlink()
    assert catalog.prune_missing() == 1
    assert catalog.find_by_source("k") is None


def test_catalog_tolerates_corrupt_database_path(tmp_path):
    # A directory is not a valid SQLite file; initialization must not crash.
    bad = tmp_path / "dir.sqlite3"
    bad.mkdir()
    catalog = Catalog(str(bad))
    assert catalog.stats()["files"] == 0
