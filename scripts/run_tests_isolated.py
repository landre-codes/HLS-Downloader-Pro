"""Executa cada arquivo de teste em um processo separado.

O Qt Quick acumula estado entre engines na mesma sessão. Com PySide6 6.12 no
Windows e no Linux, a suíte inteira em um único processo pode abortar com
segfault/access violation durante o processamento de eventos. Isolar por
arquivo preserva o sinal dos testes e impede que o teardown instável de um
arquivo derrube os demais.

Uso:
    python scripts/run_tests_isolated.py
    python scripts/run_tests_isolated.py --coverage
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str]) -> int:
    print("==> " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="acumula cobertura e exige o mínimo de 60%% no final",
    )
    args = parser.parse_args()

    files = sorted((ROOT / "tests").glob("test_*.py"))
    if not files:
        print("nenhum arquivo tests/test_*.py encontrado", file=sys.stderr)
        return 2

    if args.coverage:
        (ROOT / ".coverage").unlink(missing_ok=True)

    for path in files:
        command = [sys.executable, "-m", "pytest", "-q", str(path.relative_to(ROOT))]
        if args.coverage:
            command += ["--cov=hlsdl", "--cov-append", "--cov-report="]
        rc = _run(command)
        if rc != 0:
            print(f"falhou: {path.name} (rc={rc})", file=sys.stderr)
            return rc

    if args.coverage:
        rc = _run(
            [sys.executable, "-m", "coverage", "report", "--fail-under=60"]
        )
        if rc != 0:
            return rc

    print(f"OK: {len(files)} arquivos de teste passaram", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
