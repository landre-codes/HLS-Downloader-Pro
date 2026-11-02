"""Regressão do bug crítico: modelo e fila devem compartilhar a mesma lista.

Antes, ``DownloadModel._items`` e ``QueueManager.items`` eram listas distintas;
``clearFinished``/``clearAll`` removiam apenas de uma delas, dessincronizando
índices e fazendo ``editUrl``/``cancelItem`` agirem sobre o item errado.
"""

from __future__ import annotations

from hlsdl.model import DownloadModel
from hlsdl.queue import QueueManager
from hlsdl.status import Status


def _make():
    model = DownloadModel([])
    manager = QueueManager(model, outdir="out")
    return model, manager


def test_model_and_manager_share_list(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1\nhttps://b.com/2")
    assert manager.items is model.items()
    assert model.rowCount() == 2


def test_clear_finished_keeps_sync(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1\nhttps://b.com/2\nhttps://c.com/3")
    manager.items[0]["status"] = Status.DONE

    manager.clearFinished()

    assert model.rowCount() == 2
    assert len(manager.items) == 2
    # O índice 0 agora é o b.com/2 tanto no modelo quanto no gerente.
    assert model.data(model.index(0, 0), DownloadModel.URL) == "https://b.com/2"
    assert manager.items[0]["url"] == "https://b.com/2"


def test_edit_url_targets_correct_row_after_clear(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1\nhttps://b.com/2\nhttps://c.com/3")
    manager.items[0]["status"] = Status.DONE
    manager.clearFinished()

    # Editar a linha 0 (b.com/2) não pode tocar em c.com/3.
    assert manager.editUrl(0, "https://editado.com/x")
    assert manager.items[0]["url"] == "https://editado.com/x"
    assert manager.items[1]["url"] == "https://c.com/3"
    assert model.data(model.index(0, 0), DownloadModel.URL) == "https://editado.com/x"


def test_clear_all_keeps_sync(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1\nhttps://b.com/2")
    manager.clearAll()
    assert model.rowCount() == 0
    assert len(manager.items) == 0


def test_remove_item_keeps_sync(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1\nhttps://b.com/2\nhttps://c.com/3")
    manager.removeItem(1)  # remove b.com/2
    assert model.rowCount() == 2
    assert [i["url"] for i in manager.items] == ["https://a.com/1", "https://c.com/3"]
    assert model.data(model.index(1, 0), DownloadModel.URL) == "https://c.com/3"


def test_retry_resets_item(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1")
    manager.items[0]["status"] = Status.ERROR
    manager.items[0]["error"] = "falhou"
    manager.retryItem(0)
    assert manager.items[0]["status"] == Status.WAITING
    assert manager.items[0]["error"] == ""


def test_duplicate_skipped(qapp):
    model, manager = _make()
    added, skipped = manager.addText("https://x.com/1\nhttps://y.com/2")
    assert (added, skipped) == (2, 0)
    added, skipped = manager.addText("https://x.com/1/\nhttps://y.com/2#frag")
    assert (added, skipped) == (0, 2)


def test_status_role_returns_plain_string(qapp):
    model, manager = _make()
    manager.addText("https://a.com/1")
    assert model.data(model.index(0, 0), DownloadModel.STATUS) == "waiting"
