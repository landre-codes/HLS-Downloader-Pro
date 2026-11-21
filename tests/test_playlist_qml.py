"""Regressão do contrato QML da Playlist (unificada ao Lote)."""

from __future__ import annotations

from pathlib import Path

from hlsdl.bridge import Bridge
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager


def test_playlist_dialog_passes_url_and_limit_to_main(
    qapp, tmp_path, fake_deps, monkeypatch
):
    manager = QueueManager(DownloadModel([]), outdir=str(tmp_path / "out"))
    bridge = Bridge(
        manager,
        str(tmp_path / "out"),
        settings_path=str(tmp_path / "settings.ini"),
        state_path=str(tmp_path / "queue.json"),
        deps=fake_deps,
        defer_detection=True,
    )
    bridge.setLanguage("pt")
    seen: list[tuple] = []
    monkeypatch.setattr(
        bridge._playlist,
        "load",
        lambda url, limit, cookies: seen.append((url, limit)),
    )

    bridge.loadPlaylist("https://example.com/pl", 12)
    assert seen == [("https://example.com/pl", 12)]

    main_qml = Path(qml_path()).read_text(encoding="utf-8")
    dialog_qml = (
        Path(qml_path()).parent / "dialogs" / "PlaylistImportDialog.qml"
    ).read_text(encoding="utf-8")
    # A função não pode depender de ids internos de outro arquivo QML.
    assert "playlistUrl" not in main_qml
    assert "loadPlaylist(url, limit)" in main_qml
    assert "PlaylistImportDialog" in main_qml
    assert dialog_qml.count("dialog.appRoot.loadPlaylist(") == 1
    assert dialog_qml.count("dialog.submitPlaylist()") == 2
    assert dialog_qml.count("playlistUrl.text") >= 2
    assert dialog_qml.count("playlistLimit.value") == 1
    assert "playlist_clear_list" in dialog_qml

    bridge.shutdown()
