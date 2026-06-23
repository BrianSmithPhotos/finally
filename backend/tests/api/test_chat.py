"""Tests for /api/chat: mocks app.llm.chat.get_chat_response since that module
is owned by the LLM Engineer and not implemented yet (a NotImplementedError
placeholder lives at app/llm/chat.py pending their merge).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.db.positions import get_position
from app.db.users import get_user_profile
from app.llm.chat import ChatResponse, TradeAction, WatchlistChange


class TestChat:
    def test_chat_returns_message_with_no_actions(self, client, db):
        mock_response = ChatResponse(message="Your portfolio looks healthy.")
        with patch("app.api.chat.get_chat_response", new=AsyncMock(return_value=mock_response)):
            resp = client.post("/api/chat", json={"message": "How am I doing?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Your portfolio looks healthy."
        assert body["trades"] == []
        assert body["watchlist_changes"] == []

    def test_chat_executes_trade(self, client, db):
        mock_response = ChatResponse(
            message="Bought 10 AAPL for you.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        )
        with patch("app.api.chat.get_chat_response", new=AsyncMock(return_value=mock_response)):
            resp = client.post("/api/chat", json={"message": "Buy 10 AAPL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["trades"][0]["ticker"] == "AAPL"
        assert body["trades"][0]["error"] is None
        position = get_position(db, "AAPL")
        assert position.quantity == 10.0
        profile = get_user_profile(db)
        assert profile.cash_balance == 10000.0 - 10 * 190.0

    def test_chat_trade_failure_reported_not_raised(self, client, db):
        mock_response = ChatResponse(
            message="Tried to buy more than you can afford.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10000)],
        )
        with patch("app.api.chat.get_chat_response", new=AsyncMock(return_value=mock_response)):
            resp = client.post("/api/chat", json={"message": "Buy 10000 AAPL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["trades"][0]["error"] is not None
        assert get_position(db, "AAPL") is None

    def test_chat_applies_watchlist_change(self, client, db, market_source):
        mock_response = ChatResponse(
            message="Added PYPL to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
        with patch("app.api.chat.get_chat_response", new=AsyncMock(return_value=mock_response)):
            resp = client.post("/api/chat", json={"message": "Watch PYPL"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["watchlist_changes"][0]["ticker"] == "PYPL"
        assert body["watchlist_changes"][0]["error"] is None
        assert "PYPL" in market_source.added

    def test_chat_stores_messages_in_history(self, client, db):
        from app.db.chat import get_chat_messages

        mock_response = ChatResponse(message="Sure thing.")
        with patch("app.api.chat.get_chat_response", new=AsyncMock(return_value=mock_response)):
            client.post("/api/chat", json={"message": "Hello"})
        messages = get_chat_messages(db)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Sure thing."

    def test_chat_passes_portfolio_context_and_history(self, client, db):
        from app.db.chat import insert_chat_message
        from app.db.positions import apply_buy

        apply_buy(db, "AAPL", 5.0, 150.0)
        insert_chat_message(db, role="user", content="earlier question")
        insert_chat_message(db, role="assistant", content="earlier answer")

        mock_response = ChatResponse(message="ack")
        mock = AsyncMock(return_value=mock_response)
        with patch("app.api.chat.get_chat_response", new=mock):
            client.post("/api/chat", json={"message": "What do I own?"})

        _, kwargs = mock.call_args
        assert kwargs["message"] == "What do I own?"
        assert kwargs["portfolio_context"]["positions"][0]["ticker"] == "AAPL"
        assert len(kwargs["history"]) == 2
        assert kwargs["history"][0] == {"role": "user", "content": "earlier question"}
