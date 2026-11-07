"""Diagnóstico de ambiente, telas, escala e ferramentas.

Uso:
    python main.py --diagnose
    python diagnostico.py

Gera ``diagnostico-hlsdl.txt`` (ao lado do projeto em dev; na pasta de
configuração no build) e imprime o mesmo conteúdo quando há console.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QSettings, qVersion
from PySide6.QtGui import QGuiApplication

from . import __version__
from .config import (
    APP_NAME,
    app_dir,
    crash_log_path,
    default_output_folder,
    diagnostics_path,
    is_frozen,
    is_portable,
    log_path,
    qml_path,
    settings_path,
    tools_dir,
    user_config_dir,
)
from .services.procutils import popen_kwargs, which

_LINES: list[str] = []


def _line(text: str = "") -> None:
    _LINES.append(text)
    try:
        print(text, flush=True)
    except Exception:
        pass


def _safe(label: str, getter) -> None:
    try:
        _line(f"{label:<24}: {getter()}")
    except Exception as exc:
        _line(f"{label:<24}: (erro: {exc})")


def _tool_version(tool: str, args: list[str]) -> str:
    path = which(tool)
    if not path:
        return "não encontrado"
    try:
        result = subprocess.run(
            [path] + args,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
            **popen_kwargs(),
        )
        output = (result.stdout or result.stderr or "").strip().splitlines()
        version = output[0].strip() if output else "?"
        return f"{version} ({path})"
    except Exception as exc:
        return f"{path} (erro: {exc})"


def collect_lines() -> list[str]:
    """Monta o relatório sem abrir a janela principal."""
    _LINES.clear()
    _line(f"{APP_NAME} — diagnóstico")
    _line("=" * 64)
    _line(f"Versão do app          : {__version__}")
    _line(f"Python                 : {sys.version.split()[0]} ({platform.machine()})")
    _line(f"Executável             : {sys.executable}")
    _line(f"Sistema                : {platform.platform()}")
    _line(f"PySide6                : {pyside_version}")
    _line(f"Qt                     : {qVersion()}")
    _line(f"Empacotado (frozen)    : {is_frozen()}")
    _line(f"Modo portátil          : {is_portable()}")
    _line(f"QT_SCALE_FACTOR        : {os.environ.get('QT_SCALE_FACTOR', '(não definido)')}")
    _line()

    _line("Caminhos")
    _line("-" * 64)
    _safe("Pasta do app", app_dir)
    _safe("Configuração", user_config_dir)
    _safe("settings.ini", settings_path)
    _safe("Log", log_path)
    _safe("Crash log", crash_log_path)
    _safe("Ferramentas", tools_dir)
    _safe("Saída padrão", default_output_folder)
    _safe("QML", qml_path)
    _line()

    _line("Telas")
    _line("-" * 64)
    app = QGuiApplication.instance()
    if app is None:
        try:
            app = QGuiApplication(sys.argv[:1])
        except Exception as exc:
            _line(f"Não foi possível inicializar o Qt: {exc}")
            app = None
    if app is not None:
        from .app import compute_ui_scale

        for index, screen in enumerate(QGuiApplication.screens()):
            geometry = screen.geometry()
            available = screen.availableGeometry()
            _line(f"Tela {index} ({screen.name()})")
            _line(f"  geometry             : {geometry.getRect()}")
            _line(f"  available            : {available.getRect()}")
            _line(f"  devicePixelRatio     : {screen.devicePixelRatio():.3f}")
            _line(f"  logicalDpi           : {screen.logicalDotsPerInch():.2f}")
            _line(f"  physicalDpi          : {screen.physicalDotsPerInch():.2f}")
            _line(f"  escala automática    : {compute_ui_scale(geometry.width()):.2f}")
    else:
        _line("(sem QGuiApplication — não foi possível listar telas)")
    _line()

    _line("Janela salva")
    _line("-" * 64)
    try:
        settings = QSettings(settings_path(), QSettings.IniFormat)
        _line(f"geometry               : {settings.value('window/geometry', '')}")
        _line(f"maximized              : {settings.value('window/maximized', False)}")
    except Exception as exc:
        _line(f"(erro ao ler settings: {exc})")
    _line()

    _line("Ferramentas externas")
    _line("-" * 64)
    _line(f"ffmpeg                 : {_tool_version('ffmpeg', ['-version'])}")
    _line(f"ffprobe                : {_tool_version('ffprobe', ['-version'])}")
    _line(f"yt-dlp                 : {_tool_version('yt-dlp', ['--version'])}")
    _line()

    _line("GPUs e encoders")
    _line("-" * 64)
    try:
        from .compress import detect_encoders, detect_gpus, hardware_vendors

        for gpu in detect_gpus():
            _line(
                "GPU                    : "
                f"{gpu.get('name', '?')} (integrada={gpu.get('integrated')})"
            )
        _line(f"Fornecedores detectados: {', '.join(sorted(hardware_vendors())) or '(nenhum)'}")
        encoders = detect_encoders()
        hardware = sorted(n for n in encoders if n.endswith(("_qsv", "_nvenc", "_amf")))
        software = sorted(
            n for n in encoders if n in {"libx265", "libx264", "libsvtav1",
                                        "libaom-av1", "libkvazaar"}
        )
        _line(f"Hardware               : {', '.join(hardware) or '(nenhum)'}")
        _line(f"Software               : {', '.join(software) or '(nenhum)'}")
    except Exception as exc:
        _line(f"(erro ao detectar GPUs/encoders: {exc})")
    _line()
    _line("Fim do diagnóstico.")
    return list(_LINES)


def run(write_file: bool = True) -> int:
    lines = collect_lines()
    if not write_file:
        return 0
    target = diagnostics_path()
    try:
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"\nRelatório salvo em: {target}", flush=True)
    except OSError as exc:
        print(f"\nNão foi possível salvar o relatório: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
