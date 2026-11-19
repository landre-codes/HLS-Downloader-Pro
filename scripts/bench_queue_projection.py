"""Benchmark da projeção da fila de downloads (sem GUI).

Mede a cópia usada por ``DownloadModel.snapshot()`` e uma aproximação do custo
de reconciliar as linhas exibidas. Não substitui um profile do QML, mas dá uma
ordem de grandeza para filas de 1 mil a 50 mil itens.

Uso:
    python scripts/bench_queue_projection.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hlsdl.model import DownloadModel, make_item  # noqa: E402


def _median_ms(function, rounds: int = 5) -> float:
    samples = []
    for _ in range(rounds):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1000.0)
    return statistics.median(samples)


def main() -> int:
    print(f"{'itens':>8}  {'snapshot':>10}  {'reconcile':>10}")
    for count in (1_000, 10_000, 50_000):
        model = DownloadModel([
            make_item(index, f"https://example.com/{index}")
            for index in range(count)
        ])
        rows = model.snapshot()

        def reconcile(rows=rows) -> None:
            # Aproxima applyBatchRows: mesma ordem, comparação de cada papel.
            for row in rows:
                _ = (row["sourceIndex"], row["title"], row["url"], row["status"],
                     row["progress"], row["speed"], row["size"], row["error"],
                     row["path"], row["thumb"])

        print(f"{count:8d}  {_median_ms(model.snapshot):9.1f}ms"
              f"  {_median_ms(reconcile):9.1f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
