"""Unit tests for LLM content parsing and the call_llm fallback path.

These exercise the real (non-mock) code path by monkeypatching litellm so no
network call occurs.
"""

from __future__ import annotations

import app.chat.llm as llm_module
from app.chat.llm import call_llm, parse_llm_content


def test_parse_valid_schema():
    raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 3}]}'
    parsed = parse_llm_content(raw)
    assert parsed.message == "ok"
    assert parsed.trades[0].ticker == "AAPL"
    assert parsed.watchlist_changes == []


def test_parse_empty_content_falls_back():
    parsed = parse_llm_content("")
    assert "problem" in parsed.message.lower()
    assert parsed.trades == []


def test_parse_none_content_falls_back():
    parsed = parse_llm_content(None)
    assert parsed.message
    assert parsed.trades == []


def test_parse_malformed_json_becomes_plain_message():
    parsed = parse_llm_content("I think you should buy AAPL.")
    assert parsed.message == "I think you should buy AAPL."
    assert parsed.trades == []


def test_call_llm_handles_exception_gracefully(monkeypatch):
    # Make `from litellm import completion` raise inside call_llm.
    def _raising_completion(*a, **k):
        raise RuntimeError("network down")

    import sys
    import types

    fake = types.ModuleType("litellm")
    fake.completion = _raising_completion
    monkeypatch.setitem(sys.modules, "litellm", fake)

    resp = call_llm({"cash_balance": 0.0, "positions": []}, [], [], "hi")
    assert resp.message  # fallback message, no crash
    assert resp.trades == []


def test_call_llm_parses_structured_output(monkeypatch):
    import sys
    import types

    class _Msg:
        content = '{"message": "done", "trades": [], "watchlist_changes": []}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    fake = types.ModuleType("litellm")
    fake.completion = lambda *a, **k: _Resp()
    monkeypatch.setitem(sys.modules, "litellm", fake)

    resp = call_llm({"cash_balance": 0.0, "positions": []}, [], [], "summarize")
    assert resp.message == "done"


def test_build_messages_includes_system_context_and_history():
    portfolio = {"cash_balance": 100.0, "positions": []}
    watchlist = [{"ticker": "AAPL", "price": 190.0, "change_percent": 1.0}]
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    messages = llm_module.build_messages(portfolio, watchlist, history, "new question")
    assert messages[0]["role"] == "system"
    assert "FinAlly" in messages[0]["content"]
    assert messages[1]["role"] == "system"  # context block
    assert messages[-1] == {"role": "user", "content": "new question"}
    roles = [m["role"] for m in messages]
    assert roles.count("assistant") == 1
