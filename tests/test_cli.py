"""CLI surface tests (no network/GUI)."""

from __future__ import annotations

from hlsdl.cli import build_parser, main


def test_cli_parser_has_all_commands():
    parser = build_parser()
    for command in ("probe", "verify", "similar", "compress", "download"):
        assert command in parser._subparsers._group_actions[0].choices


def test_cli_probe_json(tmp_path, monkeypatch, capsys):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"x")
    monkeypatch.setattr(
        "hlsdl.cli.probe_media",
        lambda path: {
            "streams": [{"codec_type": "video", "codec_name": "h264",
                         "width": 320, "height": 240}],
            "format": {"duration": "10"},
        },
    )
    assert main(["probe", str(media)]) == 0
    output = capsys.readouterr().out
    assert '"width": 320' in output
    assert '"duration": 10.0' in output


def test_cli_verify_exit_code(tmp_path, monkeypatch, capsys):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"x")
    monkeypatch.setattr(
        "hlsdl.cli.verify_completion", lambda path, full_hash=True: (True, "ok")
    )
    assert main(["verify", str(media)]) == 0
    assert '"ok": true' in capsys.readouterr().out
