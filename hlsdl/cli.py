"""Headless CLI for automation and diagnostics.

Examples::

    hlsdl probe video.mp4
    hlsdl verify video.mp4
    hlsdl similar --threshold 90 C:\\Videos
    hlsdl compress input.mp4 --codec hevc --container mp4 --quality 24
    hlsdl download https://youtu.be/... --outdir C:\\Videos
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from .compress import (
    CompressionSettings,
    CompressionWorker,
    detect_encoders,
    resolve_encoder,
    skip_reason,
)
from .downloader import DownloadWorker
from .integrity import verify_completion
from .media import build_signature, group_similar, media_summary, probe_media


def _json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_probe(args) -> int:
    probe = probe_media(args.path)
    if not probe:
        print(f"não foi possível ler {args.path}", file=sys.stderr)
        return 1
    _json(media_summary(probe))
    return 0


def cmd_verify(args) -> int:
    ok, reason = verify_completion(args.path, full_hash=not args.fast)
    _json({"path": os.path.abspath(args.path), "ok": ok, "reason": reason})
    return 0 if ok else 1


def cmd_similar(args) -> int:
    paths: list[str] = []
    for raw in args.paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            paths.extend(str(p) for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            paths.append(str(path))
    if not paths:
        print("nenhum arquivo encontrado", file=sys.stderr)
        return 1
    signatures = [build_signature(path) for path in paths]
    groups = group_similar(signatures, threshold=args.threshold)
    _json(groups)
    return 0


def cmd_compress(args) -> int:
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841
    available = detect_encoders()
    settings = CompressionSettings(
        encoder=args.encoder,
        codec=args.codec,
        container=args.container,
        quality=args.quality,
        speed=args.speed,
        only_if_smaller=not args.allow_larger,
        replace_original=args.replace,
        quality_check=not args.no_quality_check,
        # O CLI não abre diálogos: sem a flag explícita, uma queda extrema de
        # bitrate é recusada e o original é mantido.
        confirm_quality_drop=False,
        allow_quality_drop=bool(args.allow_quality_drop),
    )
    encoder = resolve_encoder(settings, available)
    if not encoder:
        print("nenhum encoder disponível", file=sys.stderr)
        return 1
    failures = 0
    for raw in args.inputs:
        source = str(Path(raw).expanduser().resolve())
        if not os.path.isfile(source):
            print(f"ignorado (não é arquivo): {source}", file=sys.stderr)
            failures += 1
            continue
        probe = probe_media(source)
        reason = skip_reason(settings, probe) if probe else "probe_failed"
        if reason:
            print(f"ignorado ({reason}): {source}", file=sys.stderr)
            continue
        worker = CompressionWorker(
            source, settings, encoder,
            job_id=os.getpid(), catalog_path=None,
        )
        result = {"path": source, "status": "unknown"}
        worker.completed.connect(
            lambda final, backup, before, after, sha, validation, res=result:
            res.update({
                "status": "done", "output": final, "backup": backup,
                "before": before, "after": after, "sha256": sha,
            })
        )
        worker.skipped.connect(
            lambda msg, res=result: res.update({"status": "skipped", "reason": msg})
        )
        worker.qualityReport.connect(
            lambda report, res=result: res.update({"quality": report})
        )
        worker.failed.connect(
            lambda err, res=result: res.update({"status": "error", "error": err})
        )
        worker.run()
        print(json.dumps(result, ensure_ascii=False))
        quality = result.get("quality") or {}
        if result["status"] == "skipped" and quality.get("quality_warning"):
            print(
                "queda extrema de bitrate; use --allow-quality-drop para "
                "aceitar a saída mesmo assim",
                file=sys.stderr,
            )
        if result["status"] == "error":
            failures += 1
    return 0 if not failures else 1


def cmd_download(args) -> int:
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841
    failures = 0
    for url in args.urls:
        worker = DownloadWorker(
            url,
            outdir=str(Path(args.outdir).expanduser()),
            format_mode=args.format_mode,
            quality=args.quality,
            container=args.container,
            cookies=args.cookies or "",
            catalog_path=None,
        )
        result = {"url": url, "status": "unknown"}
        worker.succeeded.connect(
            lambda _url, path, res=result: res.update({"status": "done", "path": path})
        )
        worker.failed.connect(
            lambda _url, error, res=result:
            res.update({"status": "error", "error": error})
        )
        worker.run()
        print(json.dumps(result, ensure_ascii=False))
        if result["status"] != "done":
            failures += 1
    return 0 if not failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hlsdl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="mostra streams/duração/cor de um arquivo")
    probe.add_argument("path")
    probe.set_defaults(func=cmd_probe)

    verify = sub.add_parser("verify", help="verifica sidecar + SHA-256 de um arquivo")
    verify.add_argument("path")
    verify.add_argument("--fast", action="store_true", help="não relê o arquivo inteiro")
    verify.set_defaults(func=cmd_verify)

    similar = sub.add_parser("similar", help="busca mídias similares")
    similar.add_argument("paths", nargs="+")
    similar.add_argument("--threshold", type=float, default=85.0)
    similar.set_defaults(func=cmd_similar)

    compress = sub.add_parser("compress", help="comprime um ou mais arquivos")
    compress.add_argument("inputs", nargs="+")
    compress.add_argument("--codec", default="hevc", choices=("hevc", "h264", "av1"))
    compress.add_argument("--container", default="mp4")
    compress.add_argument("--quality", type=int, default=24)
    compress.add_argument("--speed", default="balanced",
                          choices=("fast", "balanced", "slow", "slower"))
    compress.add_argument("--encoder", default="auto")
    compress.add_argument("--replace", action="store_true",
                          help="remove o original após validação (backup é mantido)")
    compress.add_argument("--allow-larger", action="store_true")
    compress.add_argument("--no-quality-check", action="store_true")
    compress.add_argument(
        "--allow-quality-drop", action="store_true",
        help="aceita saída com queda extrema de bitrate sem confirmação",
    )
    compress.set_defaults(func=cmd_compress)

    download = sub.add_parser("download", help="baixa uma ou mais URLs")
    download.add_argument("urls", nargs="+")
    download.add_argument("--outdir", default=os.path.expanduser("~/Downloads/VideoDownloader"))
    download.add_argument("--format-mode", default="video_audio",
                          choices=("video_audio", "video_only", "audio_only"))
    download.add_argument("--quality", default="best")
    download.add_argument("--container", default="mp4")
    download.add_argument("--cookies", default="")
    download.set_defaults(func=cmd_download)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
