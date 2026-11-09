"""Testes da redação de dados sensíveis nos logs."""

from __future__ import annotations

import logging

from hlsdl.redact import RedactionFilter, redact_text


def test_redacts_query_values_but_keeps_names():
    text = (
        "INICIO url=https://cdn.example/live/master.m3u8"
        "?token=abc123&expires=999&sig=xyz"
    )
    out = redact_text(text)
    assert "abc123" not in out
    assert "999" not in out
    assert "xyz" not in out
    assert "token=***" in out
    assert "expires=***" in out
    assert "sig=***" in out
    assert "https://cdn.example/live/master.m3u8" in out


def test_redacts_userinfo_and_fragment():
    out = redact_text("https://user:senha@example.com/video.m3u8#access_token=abc")
    assert "senha" not in out
    assert "access_token" not in out
    assert out.startswith("https://***@example.com/video.m3u8#***")


def test_redacts_authorization_and_cookies():
    out = redact_text(
        "Authorization: Bearer abc.def.ghi\n"
        "Cookie: session=segredo; tema=escuro\n"
        "Set-Cookie: auth=xyz; HttpOnly"
    )
    assert "abc.def.ghi" not in out
    assert "segredo" not in out
    assert "xyz" not in out
    assert "Authorization: Bearer ***" in out
    assert "Cookie: ***" in out
    assert "Set-Cookie: ***" in out


def test_redacts_cookie_file_argument():
    out = redact_text(r'--cookies "C:\Users\me\cookies.txt" --verbose')
    assert "cookies.txt" not in out
    assert "--cookies *** --verbose" in out


def test_filter_redacts_formatted_args():
    record = logging.LogRecord(
        "hlsdl",
        logging.INFO,
        __file__,
        1,
        "progresso %d%% em %s",
        (50, "https://cdn/x.m3u8?token=segredo"),
        None,
    )
    assert RedactionFilter().filter(record) is True
    message = record.getMessage()
    assert "50%" in message
    assert "segredo" not in message
    assert "token=***" in message


def test_filter_is_noop_for_plain_messages():
    record = logging.LogRecord(
        "hlsdl", logging.INFO, __file__, 1, "fila iniciada", (), None
    )
    RedactionFilter().filter(record)
    assert record.getMessage() == "fila iniciada"
