"""Testes de status e de i18n do backend."""

from __future__ import annotations

import re
from pathlib import Path

from hlsdl.i18n import BACKEND, LANGUAGES, detect_language, is_rtl, tr, translator
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


def test_detect_language_accepts_portugal_variant(monkeypatch):
    from PySide6.QtCore import QLocale

    assert detect_language("pt_pt") == "pt_pt"
    assert detect_language("pt") == "pt"

    class _PtPtLocale:
        @staticmethod
        def name():
            return "pt_PT"

    monkeypatch.setattr(QLocale, "system", staticmethod(lambda: _PtPtLocale()))
    assert detect_language(None) == "pt_pt"


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

    assert LANGUAGES == (
        "pt", "pt_pt", "en", "es", "de", "it", "fr", "ru", "ar", "he", "ja", "ko", "zh"
    )
    core_keys = (
        "links_added", "queue_started", "err_unexpected", "dep_found",
        "compress_quality_rejected",
    )
    for lang in LANGUAGES:
        for key in core_keys:
            assert BACKEND[lang][key], f"chave {key} vazia em {lang}"
    # Amostras que precisam diferir do português.
    assert BACKEND["ja"]["links_added"] != BACKEND["pt"]["links_added"]
    assert BACKEND["ru"]["dep_found"] != BACKEND["pt"]["dep_found"]
    assert BACKEND["zh"]["err_unexpected"] != BACKEND["pt"]["err_unexpected"]
    for lang in ("de", "ar", "he", "ko"):
        assert BACKEND[lang]["links_added"] != BACKEND["pt"]["links_added"]
        assert BACKEND[lang]["dep_log_downloading"] != BACKEND["pt"]["dep_log_downloading"]
    assert BACKEND["pt_pt"]["dep_log_downloading"] != BACKEND["pt"]["dep_log_downloading"]
    assert "ficheiro" in BACKEND["pt_pt"]["read_failed"]
    assert "transferir" in BACKEND["pt_pt"]["dep_log_downloading"]
    assert is_rtl("ar") is True
    assert is_rtl("he") is True
    assert is_rtl("en") is False
    assert is_rtl("ko") is False


def test_backend_catalogs_have_full_key_parity():
    base = set(BACKEND["pt"])
    for lang in LANGUAGES:
        missing = base - set(BACKEND[lang])
        assert not missing, f"chaves ausentes em {lang}: {sorted(missing)[:10]}"
        empty = [key for key in base if not str(BACKEND[lang].get(key, "")).strip()]
        assert not empty, f"chaves vazias em {lang}: {empty[:10]}"


def _js_object_end(text: str, start: int) -> int:
    """Índice do ``}`` que fecha o objeto iniciado em ``start``.

    Ignora chaves dentro de strings e comentários de linha, para que
    placeholders como ``{a}`` não alterem o balanço.
    """
    depth = 0
    in_string = False
    escaped = False
    i = start
    while i < len(text):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "/" and i + 1 < len(text) and text[i + 1] == "/":
            newline = text.find("\n", i)
            if newline < 0:
                break
            i = newline
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise AssertionError("objeto JS não balanceado")


def _ui_catalog_keys() -> dict[str, set[str]]:
    path = Path(__file__).resolve().parents[1] / "hlsdl" / "ui" / "i18n.js"
    text = path.read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    for match in re.finditer(r"^var\s+\w+\s*=\s*\{", text, re.MULTILINE):
        body_start = match.end() - 1
        body_end = _js_object_end(text, body_start)
        body = text[body_start:body_end]
        for lang_match in re.finditer(r'"(\w+)"\s*:\s*\{', body):
            block_start = body.find("{", lang_match.start())
            block_end = _js_object_end(body, block_start)
            block = body[block_start + 1:block_end]
            keys = set(
                re.findall(r'(?:^|[{,])\s*"?([A-Za-z_]\w*)"?\s*:', block)
            )
            result.setdefault(lang_match.group(1), set()).update(keys)
    return result


def test_ui_catalog_has_full_parity_and_covers_qml_keys():
    catalogs = _ui_catalog_keys()
    assert set(catalogs) == set(LANGUAGES)
    base = catalogs["pt"]
    assert len(base) > 300, f"catálogo PT inesperadamente pequeno: {len(base)}"
    for lang in LANGUAGES:
        missing = base - catalogs[lang]
        assert not missing, f"chaves ausentes em ui/{lang}: {sorted(missing)[:10]}"
        extra = catalogs[lang] - base
        assert not extra, f"chaves sem fallback PT em ui/{lang}: {sorted(extra)[:10]}"

    used: set[str] = set()
    ui_dir = Path(__file__).resolve().parents[1] / "hlsdl" / "ui"
    for qml in ui_dir.rglob("*.qml"):
        used |= set(re.findall(r"\bstrings\.([A-Za-z_]\w*)", qml.read_text(encoding="utf-8")))
    missing = used - base
    assert not missing, f"chaves usadas no QML sem tradução: {sorted(missing)}"
