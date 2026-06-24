"""Unit tests for the deterministic mock LLM."""

from __future__ import annotations

import pytest

from app.chat.mock import mock_llm_response

_PORTFOLIO = {"cash_balance": 10000.0, "positions": []}


@pytest.mark.parametrize(
    "message,ticker,side,qty",
    [
        ("buy 5 AAPL", "AAPL", "buy", 5.0),
        ("sell 2.5 shares of TSLA", "TSLA", "sell", 2.5),
        ("please buy 10 shares NVDA now", "NVDA", "buy", 10.0),
        ("BUY 3 msft", "MSFT", "buy", 3.0),
    ],
)
def test_trade_intent_parsed(message, ticker, side, qty):
    resp = mock_llm_response(message, _PORTFOLIO)
    assert len(resp.trades) == 1
    t = resp.trades[0]
    assert (t.ticker, t.side, t.quantity) == (ticker, side, qty)


def test_add_watchlist_intent():
    resp = mock_llm_response("add PYPL to my list", _PORTFOLIO)
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].ticker == "PYPL"
    assert resp.watchlist_changes[0].action == "add"
    assert resp.trades == []


def test_remove_watchlist_intent():
    resp = mock_llm_response("remove META", _PORTFOLIO)
    assert resp.watchlist_changes[0].action == "remove"
    assert resp.watchlist_changes[0].ticker == "META"


def test_plain_message_is_echo_with_context():
    resp = mock_llm_response("hello there", _PORTFOLIO)
    assert resp.trades == []
    assert resp.watchlist_changes == []
    assert "10,000" in resp.message


def test_deterministic_same_input_same_output():
    a = mock_llm_response("buy 5 AAPL", _PORTFOLIO)
    b = mock_llm_response("buy 5 AAPL", _PORTFOLIO)
    assert a.model_dump() == b.model_dump()
