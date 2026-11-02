"""Testes de status e de i18n do backend."""

from __future__ import annotations

from hlsdl.i18n import tr, translator
from hlsdl.status import ACTIVE, FINAL, Status


def test_status_values_are_stable_ids():
    assert Status.WAITING.value == "waiting"
    assert Status.DOWNLOADING.value == "downloading"
    assert Status.ANALYZING.value == "analyzing"
    assert Status.DONE.value == "done"
    assert Status.ERROR.value == "error"
    assert Status.CANCELLED.value == "cancelled"


def test_status_final():
    assert Status.DONE.is_final and Status.ERROR.is_final and Status.CANCELLED.is_final
    assert not Status.WAITING.is_final
    assert Status.WAITING not in FINAL
    assert Status.DOWNLOADING in ACTIVE


def test_i18n_pt_en():
    assert "adicionados" in tr("pt", "links_added", a=2)
    assert "added" in tr("en", "links_added", a=2)


def test_i18n_fallback_unknown_lang_and_key():
    assert tr("xx", "no_links") == tr("pt", "no_links")
    assert tr("pt", "chave_inexistente") == "chave_inexistente"


def test_translator_is_bound_to_lang():
    t = translator("en")
    assert "not found" in t("err_ytdlp_missing")


def test_all_languages_are_present_and_translated():
    from hlsdl.i18n import BACKEND, LANGUAGES

    assert LANGUAGES == ("pt", "en", "es", "it", "fr", "ru", "ja", "zh")
    core_keys = ("links_added", "queue_started", "err_unexpected", "dep_found")
    for lang in LANGUAGES:
        for key in core_keys:
            assert BACKEND[lang][key], f"chave {key} vazia em {lang}"
    # Amostras que precisam diferir do português.
    assert BACKEND["ja"]["links_added"] != BACKEND["pt"]["links_added"]
    assert BACKEND["ru"]["dep_found"] != BACKEND["pt"]["dep_found"]
    assert BACKEND["zh"]["err_unexpected"] != BACKEND["pt"]["err_unexpected"]
