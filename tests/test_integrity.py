"""Integrity, transactional install and crash recovery tests."""

from __future__ import annotations

import os
import stat

from hlsdl.downloader import DownloadWorker
from hlsdl.integrity import (
    FileGuard,
    JobJournal,
    build_completion,
    cleanup_sidecars,
    create_backup,
    install_output,
    read_completion,
    recover_journal,
    recover_journals,
    release_output_path,
    reserve_output_path,
    set_sidecars_enabled,
    sha256_file,
    sidecar_path,
    verify_completion,
    write_completion,
)


def _probe(duration: str = "10") -> dict:
    return {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 320,
             "height": 240, "pix_fmt": "yuv420p", "duration": duration},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2,
             "duration": duration},
        ],
        "format": {"duration": duration},
    }


def test_sidecar_path_posix_is_hidden_and_legacy_remains_readable(tmp_path, monkeypatch):
    from hlsdl.integrity import legacy_sidecar_path

    media = tmp_path / "video.mp4"
    media.write_bytes(b"content")
    posix_path = sidecar_path(str(media), posix=True)
    assert os.path.basename(posix_path) == ".video.mp4.hlsdl.json"
    assert legacy_sidecar_path(str(media)).endswith("video.mp4.hlsdl.json")
    assert sidecar_path(str(media), posix=False).endswith("video.mp4.hlsdl.json")

    monkeypatch.setattr("hlsdl.integrity.probe_media", lambda path: _probe())
    record = build_completion(str(media), source_key="legacy")
    from hlsdl.integrity import write_json_atomic

    write_json_atomic(legacy_sidecar_path(str(media)), record.to_dict())
    loaded = read_completion(str(media))
    assert loaded is not None and loaded.source_key == "legacy"


def test_sidecars_can_be_disabled_and_cleaned(tmp_path, monkeypatch):
    monkeypatch.setattr("hlsdl.integrity.probe_media", lambda path: _probe())
    media = tmp_path / "video.mp4"
    media.write_bytes(b"content")
    record = build_completion(str(media), source_key="key")
    try:
        set_sidecars_enabled(False)
        assert write_completion(str(media), record) == ""
        assert not os.path.exists(sidecar_path(str(media)))
    finally:
        set_sidecars_enabled(True)
    assert write_completion(str(media), record)
    assert os.path.exists(sidecar_path(str(media)))
    assert cleanup_sidecars(str(tmp_path)) == 1
    assert not os.path.exists(sidecar_path(str(media)))


def test_completion_roundtrip_and_hash_verification(tmp_path, monkeypatch):
    monkeypatch.setattr("hlsdl.integrity.probe_media", lambda path: _probe())
    media = tmp_path / "video.mp4"
    media.write_bytes(b"original-content")
    record = build_completion(
        str(media), source_key="youtube:abc", source_url="https://x/y"
    )
    assert record.sha256 == sha256_file(str(media))
    sidecar = write_completion(str(media), record)
    assert os.path.exists(sidecar)
    if os.name == "nt":
        assert os.stat(sidecar).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN
    loaded = read_completion(str(media))
    assert loaded is not None and loaded.source_key == "youtube:abc"
    ok, reason = verify_completion(str(media))
    assert ok and reason == "ok"

    # Same size, different bytes -> hash must fail.
    media.write_bytes(b"tampered-content")
    ok, reason = verify_completion(str(media))
    assert not ok and reason in ("hash_mismatch", "size_mismatch")


def test_file_guard_detects_change(tmp_path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"a" * 100)
    guard = FileGuard.capture(str(path))
    ok, reason = guard.unchanged()
    assert ok and reason == "ok"
    path.write_bytes(b"b" * 100)
    ok, reason = guard.unchanged()
    assert not ok and reason in ("source_mtime_changed", "source_hash_changed")


def test_reserve_output_path_avoids_existing_and_duplicates(tmp_path):
    source = tmp_path / "movie.mp4"
    source.write_bytes(b"x")
    (tmp_path / "movie_hevc.mp4").write_bytes(b"existing")
    first = reserve_output_path(str(source), "hevc", "mp4")
    second = reserve_output_path(str(source), "hevc", "mp4")
    try:
        assert first.endswith("movie_hevc-2.mp4")
        assert second.endswith("movie_hevc-3.mp4")
        assert first != second
    finally:
        release_output_path(first)
        release_output_path(second)


def test_install_output_with_backup_and_completion(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    temp = tmp_path / "encoded.part.mp4"
    temp.write_bytes(b"encoded")
    final = tmp_path / "source_hevc.mp4"
    journal = JobJournal.create(
        str(tmp_path / "journals"), 1, str(source), str(final), str(temp),
    )
    backup = install_output(
        str(temp), str(final), str(source),
        replace_original=True,
        expected_hash=sha256_file(str(temp)),
        expected_size=os.path.getsize(temp),
        journal=journal,
        verify_final=lambda path: (True, "ok"),
    )
    assert os.path.exists(final)
    assert final.read_bytes() == b"encoded"
    assert not source.exists()
    assert backup and os.path.exists(backup)
    assert open(backup, "rb").read() == b"original"
    assert journal.stage_name == "done"


def test_install_output_rolls_back_on_hash_mismatch(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    temp = tmp_path / "encoded.part.mp4"
    temp.write_bytes(b"encoded")
    final = tmp_path / "source_hevc.mp4"
    journal = JobJournal.create(
        str(tmp_path / "journals"), 2, str(source), str(final), str(temp),
    )
    try:
        install_output(
            str(temp), str(final), str(source),
            replace_original=True,
            expected_hash="0" * 64,
            expected_size=os.path.getsize(temp),
            journal=journal,
        )
        raise AssertionError("expected hash mismatch")
    except RuntimeError as exc:
        assert "hash" in str(exc)
    # The original must still be intact and the bad final removed.
    assert source.read_bytes() == b"original"
    assert not final.exists()


def test_install_output_refuses_if_source_changed(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    temp = tmp_path / "encoded.part.mp4"
    temp.write_bytes(b"encoded")
    final = tmp_path / "source_hevc.mp4"
    journal = JobJournal.create(
        str(tmp_path / "journals"), 3, str(source), str(final), str(temp),
    )
    source.write_bytes(b"changed")
    try:
        install_output(
            str(temp), str(final), str(source),
            replace_original=True,
            expected_hash=sha256_file(str(temp)),
            expected_size=os.path.getsize(temp),
            journal=journal,
        )
        raise AssertionError("expected source guard failure")
    except RuntimeError as exc:
        assert "source_" in str(exc)
    assert source.read_bytes() == b"changed"


def test_install_output_rejects_final_equal_to_source(tmp_path):
    """P3-01: a colisão não pode apagar a saída já validada."""
    source = tmp_path / "same.mp4"
    source.write_bytes(b"original")
    temp = tmp_path / "encoded.part.mp4"
    temp.write_bytes(b"encoded")
    journal = JobJournal.create(
        str(tmp_path / "journals"), 4, str(source), str(source), str(temp),
    )
    try:
        install_output(
            str(temp), str(source), str(source),
            replace_original=True,
            expected_hash=sha256_file(str(temp)),
            expected_size=os.path.getsize(temp),
            journal=journal,
        )
        raise AssertionError("expected collision failure")
    except RuntimeError as exc:
        assert str(exc) == "source_equals_final"
    assert source.read_bytes() == b"original"
    assert temp.read_bytes() == b"encoded"
    assert journal.stage_name != "done"


def test_recover_installing_keeps_verified_final(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    final = tmp_path / "source_hevc.mp4"
    final.write_bytes(b"encoded")
    temp = tmp_path / "old.part.mp4"
    temp.write_bytes(b"partial")
    journal = JobJournal.create(
        str(tmp_path / "journals"), 4, str(source), str(final), str(temp),
    )
    journal.stage(
        "installing",
        expected_hash=sha256_file(str(final)),
        output_size=os.path.getsize(final),
    )
    action = recover_journal(journal)
    assert action == "kept_installed"
    assert final.read_bytes() == b"encoded"
    assert source.exists()
    assert not temp.exists()
    assert not os.path.exists(journal.path)


def test_recover_encoding_discards_temp_and_keeps_source(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    final = tmp_path / "source_hevc.mp4"
    temp = tmp_path / "source_hevc.part.mp4"
    temp.write_bytes(b"partial")
    journal = JobJournal.create(
        str(tmp_path / "journals"), 5, str(source), str(final), str(temp),
    )
    journal.stage("encoding")
    action = recover_journal(journal)
    assert action == "discarded_partial"
    assert source.read_bytes() == b"original"
    assert not temp.exists()
    assert not os.path.exists(journal.path)


def test_recover_backing_up_restores_missing_source(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    backup = create_backup(str(source))
    source.unlink()
    final = tmp_path / "source_hevc.mp4"
    temp = tmp_path / "temp.mp4"
    temp.write_bytes(b"partial")
    journal = JobJournal.create(
        str(tmp_path / "journals"), 6, str(source), str(final), str(temp),
    )
    journal.stage("backing_up", backup=backup)
    action = recover_journal(journal)
    assert action == "restored_backup"
    assert source.read_bytes() == b"original"


def test_recover_journals_directory(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    final = tmp_path / "final.mp4"
    temp = tmp_path / "temp.mp4"
    temp.write_bytes(b"partial")
    journal = JobJournal.create(
        str(tmp_path / "journals"), 7, str(source), str(final), str(temp),
    )
    journal.stage("encoding")
    results = recover_journals(str(tmp_path / "journals"))
    assert results and results[0]["action"] == "discarded_partial"


def test_find_completion_by_source(tmp_path, monkeypatch):
    from hlsdl.integrity import find_completion_by_source

    monkeypatch.setattr("hlsdl.integrity.probe_media", lambda path: _probe())
    media = tmp_path / "video.mp4"
    media.write_bytes(b"content")
    record = build_completion(str(media), source_key="youtube:abc")
    write_completion(str(media), record)
    assert find_completion_by_source(str(tmp_path), "youtube:abc") == str(media)
    assert find_completion_by_source(str(tmp_path), "youtube:other") == ""


def test_download_finalize_writes_completion(tmp_path, monkeypatch):
    media = tmp_path / "download.mp4"
    media.write_bytes(b"media-content")
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: _probe())
    monkeypatch.setattr("hlsdl.integrity.probe_media", lambda path: _probe())
    worker = DownloadWorker("https://youtu.be/abc123", str(tmp_path))
    result = worker._finalize_download(str(media))
    assert result == str(media)
    assert os.path.exists(sidecar_path(str(media)))
    ok, reason = verify_completion(str(media))
    assert ok, reason


def test_download_finalize_quarantines_unreadable_file(tmp_path, monkeypatch):
    media = tmp_path / "download.mp4"
    media.write_bytes(b"<html>not media</html>")
    monkeypatch.setattr("hlsdl.downloader.probe_media", lambda path: {})
    worker = DownloadWorker("https://x/y", str(tmp_path))
    assert worker._finalize_download(str(media)) == ""
    assert not media.exists()
    assert os.path.exists(str(media) + ".invalid")
