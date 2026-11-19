"""Regressões das tabelas: filtro dinâmico, ordenação e alinhamento.

O bug original da aba Compressão era o cabeçalho "Arquivo" fora de posição e
colunas do cabeçalho divergentes das colunas do delegate. Estes testes leem a
geometria real do QML (offscreen) e comparam cabeçalho × linha.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine, QQmlExpression

from hlsdl.bridge import Bridge
from hlsdl.compress import CompressionModel, CompressStatus, make_item
from hlsdl.config import qml_path
from hlsdl.model import DownloadModel
from hlsdl.model import make_item as make_download_item
from hlsdl.queue import QueueManager
from hlsdl.status import Status


def _pump(qapp, rounds: int = 45) -> None:
    for _ in range(rounds):
        qapp.processEvents()
        time.sleep(0.01)


def _ev(ctx, scope, expr):
    expression = QQmlExpression(ctx, scope, expr)
    result = expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())
    return result[0] if isinstance(result, tuple) else result


def test_tablefilter_js_normalizes_and_supports_prefixes(qapp):
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    base = Path(__file__).resolve().parents[1] / "hlsdl" / "ui" / "__probe.qml"
    qml = '''import QtQuick
import "tablefilter.js" as TF
QtObject {
    property bool normalized: TF.normalize("AÇÃO Ção") === "acao cao"
    property bool simple: TF.matchText("ALPHA", {}, {name: ["alpha.mp4"]})
    property bool miss: TF.matchText("beta", {}, {name: ["alpha.mp4"]})
    property bool prefixed: TF.matchText("status:concluido",
        {status: "status"},
        {name: ["alpha.mp4"], status: ["Concluído"]})
    property bool multi: TF.matchText("4k erro",
        {erro: "status"},
        {name: ["alpha 4k.mp4"], status: ["erro"]})
    property bool emptyPrefix: TF.matchText("status:",
        {status: "status"}, {name: ["alpha.mp4"]})
}'''
    component.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(base)))
    obj = component.create()
    assert obj is not None, component.errorString()
    assert obj.property("normalized") is True
    assert obj.property("simple") is True
    assert obj.property("miss") is False
    assert obj.property("prefixed") is True
    assert obj.property("multi") is True
    assert obj.property("emptyPrefix") is True


def test_download_snapshot_preserves_source_order_and_indexes():
    model = DownloadModel([])
    first = make_download_item(1, "https://a.example/1")
    first["title"] = "Beta"
    first["status"] = Status.DONE
    second = make_download_item(2, "https://a.example/2")
    second["title"] = "Alpha"
    second["status"] = Status.DOWNLOADING
    model.add(first)
    model.add(second)

    rows = model.snapshot()
    assert [row["sourceIndex"] for row in rows] == [0, 1]
    assert [row["title"] for row in rows] == ["Beta", "Alpha"]
    assert [row["status"] for row in rows] == ["done", "downloading"]
    # A ordem de agendamento da fila não pode ser alterada pelo snapshot.
    assert model.items()[0] is first and model.items()[1] is second


def test_batch_uses_python_proxy_instead_of_js_projection():
    qml = (
        Path(__file__).resolve().parents[1]
        / "hlsdl" / "ui" / "pages" / "BatchPage.qml"
    ).read_text(encoding="utf-8")
    assert "model: bridge.batchModel" in qml
    assert "rebuildBatchRows" not in qml
    assert "batchRows" not in qml
    assert "batchSyncTimer" not in qml


def test_compression_actions_reference_source_index():
    qml = (
        Path(__file__).resolve().parents[1]
        / "hlsdl" / "ui" / "pages" / "CompressionPage.qml"
    ).read_text(encoding="utf-8")
    for method in (
        "cancelCompressionItem",
        "retryCompressionItem",
        "removeCompressionItem",
    ):
        assert f"{method}(model.sourceIndex)" in qml, method


def _build_app(qapp, tmp_path, fake_deps):
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

    # Ordem de inserção diferente da ordem alfabética: a ordenação visual
    # não pode alterar a ordem de agendamento do manager.
    specs = [
        ("beta-lecture.mp4", CompressStatus.ENCODING, 42.0, 0.0, "hevc_qsv"),
        ("alpha-documentary.mp4", CompressStatus.DONE, 100.0, 0.0, "hevc"),
        ("gamma-archive.mkv", CompressStatus.ERROR, 0.0, 88.0, ""),
    ]
    for index, (name, status, progress, saving, encoder) in enumerate(specs):
        path = tmp_path / name
        path.write_bytes(b"x")
        item = make_item(index + 1, str(path))
        item.update(
            status=status,
            progress=progress,
            saving=saving,
            encoder=encoder,
            size_before=10_000_000,
            size_after=3_000_000 if status == CompressStatus.DONE else 0,
            error="falha simulada" if status == CompressStatus.ERROR else "",
        )
        bridge.compression.model.add(item)

    for index, (title, status, progress) in enumerate([
        ("Documentário de arquivo", Status.DONE, 100.0),
        ("Aula de física", Status.DOWNLOADING, 37.5),
        ("Entrevista", Status.ERROR, 12.0),
    ]):
        item = make_download_item(index + 1, f"https://example.com/{index}")
        item.update(title=title, status=status, progress=progress,
                    speed="-", size="1 MiB",
                    error="HTTP 403" if status is Status.ERROR else "")
        manager.model.add(item)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("downloadModel", manager.model)
    engine.rootContext().setContextProperty(
        "compressionModel", bridge.compression.model
    )
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(qml_path()))
    assert engine.rootObjects()
    root = engine.rootObjects()[0]
    root.show()
    return bridge, engine, root


def test_compression_header_and_rows_share_same_geometry(qapp, tmp_path, fake_deps):
    bridge, engine, root = _build_app(qapp, tmp_path, fake_deps)
    _ev(engine.contextForObject(root), root, "tabBar.currentIndex = 3")
    _pump(qapp, 70)

    page = root.findChild(QObject, "compressionPage")
    listing = root.findChild(QObject, "compressionList")
    assert page is not None and listing is not None
    assert listing.property("count") == 3

    headers = {
        name: root.findChild(QObject, name)
        for name in ("compHeaderName", "compHeaderStatus",
                     "compHeaderProgress", "compHeaderResult")
    }
    ctx = engine.contextForObject(page)
    for width, height in ((1160, 800), (940, 620)):
        root.resize(width, height)
        _pump(qapp, 45)
        for name, header in headers.items():
            assert header is not None, name
            assert header.property("height") == 36, (width, name)
            assert header.property("y") == 0, (width, name)

        geometry = _ev(ctx, page, "JSON.stringify(rowCellXsAt(0))")
        cells = json.loads(geometry)
        assert len(cells) >= 4
        by_name = [headers["compHeaderName"], headers["compHeaderStatus"],
                   headers["compHeaderProgress"], headers["compHeaderResult"]]
        for header, cell_x in zip(by_name, cells, strict=False):
            assert abs(header.property("x") - cell_x) <= 1, (
                width, header.objectName(), header.property("x"), cell_x
            )

    root.resize(1160, 800)
    _pump(qapp, 30)

    # Filtro dinâmico com prefixo de campo, sem combobox.
    page.setProperty("compFilterText", "status:concluido")
    _pump(qapp, 20)
    assert listing.property("contentHeight") == 58
    page.setProperty("compFilterText", "")
    _pump(qapp, 20)
    assert listing.property("contentHeight") == 174

    # Clique no cabeçalho ordena; segundo clique inverte.
    QMetaObject.invokeMethod(headers["compHeaderName"], "activate")
    _pump(qapp, 10)
    model = bridge.compression.model
    assert model.property("sortKey") == "name"
    assert model.property("sortAscending") is True
    assert model.data(model.index(0, 0), CompressionModel.NAME) == "alpha-documentary.mp4"
    assert model.data(model.index(0, 0), CompressionModel.SOURCE_INDEX) == 1
    # A ordem de trabalho continua beta, alpha, gamma.
    assert [item["name"] for item in model.items()] == [
        "beta-lecture.mp4", "alpha-documentary.mp4", "gamma-archive.mkv"
    ]
    QMetaObject.invokeMethod(headers["compHeaderName"], "activate")
    _pump(qapp, 10)
    assert model.property("sortAscending") is False

    # Em 940x620 os ajustes podem ser recolhidos para liberar a fila.
    root.resize(940, 620)
    _pump(qapp, 40)
    height_before = listing.property("height")
    _ev(ctx, page, "toggleSettings()")
    _pump(qapp, 40)
    assert page.property("compSettingsCollapsed") is True
    assert listing.property("height") > height_before + 80
    assert root.findChild(QObject, "compPresetRow").property("visible") is False
    _ev(ctx, page, "toggleSettings()")
    _pump(qapp, 30)
    assert page.property("compSettingsCollapsed") is False

    bridge.shutdown()


def test_batch_filter_sort_and_source_index_mapping(
    qapp, tmp_path, fake_deps, monkeypatch
):
    bridge, engine, root = _build_app(qapp, tmp_path, fake_deps)
    _ev(engine.contextForObject(root), root, "tabBar.currentIndex = 1")
    _pump(qapp, 70)

    page = root.findChild(QObject, "batchPage")
    rows = bridge.batchModel
    assert page is not None and rows is not None
    assert rows.rowCount() == 3

    # Filtro cobre status e nome, com prefixo.
    root.setProperty("queueFilterText", "status:erro")
    _pump(qapp, 25)
    assert rows.rowCount() == 1
    root.setProperty("queueFilterText", "aula")
    _pump(qapp, 25)
    assert rows.rowCount() == 1
    root.setProperty("queueFilterText", "")
    _pump(qapp, 25)
    assert rows.rowCount() == 3

    header = root.findChild(QObject, "batchHeaderName")
    assert header is not None
    QMetaObject.invokeMethod(header, "activate")
    _pump(qapp, 15)
    assert page.property("batchSortKey") == "name"
    assert page.property("batchSortAscending") is True

    ctx = engine.contextForObject(page)
    first = _ev(ctx, page, "rowTitleAt(0) + '|' + rowSourceAt(0)")
    assert first == "Aula de física|1"
    assert _ev(ctx, page, "batchSourceIndex(0)") == 1

    header_objs = [
        root.findChild(QObject, "batchHeaderName"),
        root.findChild(QObject, "batchHeaderStatus"),
        root.findChild(QObject, "batchHeaderProgress"),
        root.findChild(QObject, "batchHeaderSpeed"),
        root.findChild(QObject, "batchHeaderActions"),
    ]
    assert all(header_objs)
    for width, height in ((1160, 800), (940, 620)):
        root.resize(width, height)
        _pump(qapp, 45)
        rects = json.loads(_ev(ctx, page, "JSON.stringify(rowCellRectsAt(0))"))
        assert len(rects) >= 5
        # A coluna Título começa depois da miniatura; a borda direita coincide.
        name_header = header_objs[0]
        assert abs((name_header.property("x") + name_header.property("width"))
                   - (rects[0]["x"] + rects[0]["width"])) <= 1
        for header, cell in zip(header_objs[1:], rects[1:], strict=False):
            assert abs(header.property("x") - cell["x"]) <= 1, (
                width, header.objectName(), header.property("x"), cell["x"]
            )

    # A atualização da tabela não pode ser adiada por um fluxo contínuo de
    # progresso: com touch a ~100 Hz, o timer ainda precisa disparar antes do
    # fim da rajada (coalescência, não restart).
    source = 1  # "Aula de física", linha 0 na ordem alfabética
    item = bridge.manager.model.items()[source]
    item["progress"] = 0.0
    bridge.manager.model.touch(source)
    _pump(qapp, 25)
    assert _ev(ctx, page, "rowProgressAt(0)") == 0.0
    for value in range(1, 70):
        item["progress"] = float(value)
        bridge.manager.model.touch(source)
        _pump(qapp, 1)
        if value == 30:
            assert _ev(ctx, page, "rowProgressAt(0)") >= 10
    _pump(qapp, 30)
    assert _ev(ctx, page, "rowProgressAt(0)") == 69.0

    # Contrato do root: URL/limite explícitos, sem ids internos de outra página.
    seen: list[tuple] = []
    monkeypatch.setattr(
        bridge._playlist,
        "load",
        lambda url, limit, cookies: seen.append((url, limit)),
    )
    root_ctx = engine.contextForObject(root)
    _ev(root_ctx, root, 'loadPlaylist("  https://example.com/pl  ", 7)')
    assert seen == [("https://example.com/pl", 7)]

    bridge.shutdown()
