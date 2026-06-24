"""End-to-end tests for POST /api/chat in LLM_MOCK mode."""

from __future__ import annotations

import json


def test_plain_message_returns_message_no_actions(client, db):
    resp = client.post("/api/chat", json={"message": "How am I doing?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"]
    assert body["trades"] == []
    assert body["watchlist_changes"] == []
    # User + assistant messages persisted.
    history = db.list_chat_messages()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "How am I doing?"


def test_buy_executes_trade_and_decrements_cash(client, db):
    start_cash = db.get_cash_balance()
    resp = client.post("/api/chat", json={"message": "buy 5 AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["trades"]) == 1
    trade = body["trades"][0]
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 5
    assert trade["status"] == "executed"
    assert trade["price"] == 190.0
    assert trade["error"] is None
    # Cash decreased by 5 * 190.
    assert db.get_cash_balance() == start_cash - 5 * 190.0
    pos = db.get_position("AAPL")
    assert pos is not None and pos["quantity"] == 5


def test_sell_more_than_owned_surfaces_error_not_500(client, db):
    resp = client.post("/api/chat", json={"message": "sell 3 TSLA"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["trades"]) == 1
    trade = body["trades"][0]
    assert trade["status"] == "error"
    assert trade["price"] is None
    assert "No position" in trade["error"] or "Insufficient" in trade["error"]


def test_insufficient_cash_surfaces_error(client, db):
    # 1000 * 650 (NFLX) far exceeds the $10k balance.
    resp = client.post("/api/chat", json={"message": "buy 1000 NFLX"})
    assert resp.status_code == 200
    trade = resp.json()["trades"][0]
    assert trade["status"] == "error"
    assert "Insufficient cash" in trade["error"]


def test_watchlist_add_via_chat(client, db, source):
    resp = client.post("/api/chat", json={"message": "add PYPL"})
    assert resp.status_code == 200
    changes = resp.json()["watchlist_changes"]
    assert len(changes) == 1
    assert changes[0]["ticker"] == "PYPL"
    assert changes[0]["action"] == "add"
    assert changes[0]["status"] == "added"
    assert "PYPL" in db.list_watchlist_tickers()
    assert "PYPL" in source.added


def test_watchlist_remove_via_chat(client, db, source):
    resp = client.post("/api/chat", json={"message": "remove AAPL"})
    assert resp.status_code == 200
    changes = resp.json()["watchlist_changes"]
    assert changes[0]["status"] == "removed"
    assert "AAPL" not in db.list_watchlist_tickers()
    assert "AAPL" in source.removed


def test_remove_unwatched_ticker_is_noop(client, db, source):
    resp = client.post("/api/chat", json={"message": "remove ZZZZ"})
    assert resp.status_code == 200
    changes = resp.json()["watchlist_changes"]
    assert changes[0]["status"] == "noop"
    assert "ZZZZ" not in source.removed


def test_blank_message_rejected(client):
    resp = client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 422


def test_assistant_actions_persisted_as_json(client, db):
    client.post("/api/chat", json={"message": "buy 2 GOOGL"})
    history = db.list_chat_messages()
    assistant = history[-1]
    assert assistant["role"] == "assistant"
    actions = json.loads(assistant["actions"])
    assert actions["trades"][0]["ticker"] == "GOOGL"
    assert actions["trades"][0]["status"] == "executed"
