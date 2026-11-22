"""Executa cada arquivo de teste em um processo separado.

O Qt Quick acumula estado entre engines na mesma sessão. Com PySide6 6.12 no
Windows e no Linux, a suíte inteira em um único processo pode abortar com
segfault/access violation durante o processamento de eventos. Isolar por
arquivo preserva o sinal dos testes e impede que o teardown instável de um
arquivo derrube os demais.

Além do isolamento, cada arquivo tem uma repetição extra quando o interpretador
morre com um código nativo de crash (access violation/abort) do PySide6 6.12.
Falhas de asserção e erros Python não são repetidos: o código de saída é
diferente e a suíte continua falhando normalmente.

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

# Códigos nativos de crash observados no PySide6 6.12 durante o processamento
# de eventos do Qt no Windows. Podem chegar com sinal ou sem sinal.
_CRASH_CODES = {
    -1073741819,  # 0xC0000005 access violation
    3221225477,   # 0xC0000005 sem sinal
    -1073740791,  # 0xC0000409 abort/stack buffer overrun
    3221226505,   # 0xC0000409 sem sinal
}
_ATTEMPTS = 2


def _run(command: list[str]) -> int:
    print("==> " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def _run_with_retry(command: list[str], name: str) -> int:
    for attempt in range(1, _ATTEMPTS + 1):
        rc = _run(command)
        if rc == 0 or rc not in _CRASH_CODES or attempt == _ATTEMPTS:
            return rc
        print(
            f"AVISO: {name} abortou com código nativo {rc}; "
            f"repetindo ({attempt}/{_ATTEMPTS - 1})...",
            file=sys.stderr,
            flush=True,
        )
    return rc


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
        rc = _run_with_retry(command, path.name)
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
