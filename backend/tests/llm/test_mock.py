"""Tests for deterministic LLM_MOCK responses."""

from app.llm.mock import get_mock_response
from app.llm.schemas import ChatResponse


class TestGetMockResponse:
    """Tests for get_mock_response."""

    def test_buy_message_returns_buy_trade(self):
        response = get_mock_response("Please buy AAPL for me")

        assert isinstance(response, ChatResponse)
        assert len(response.trades) == 1
        assert response.trades[0].ticker == "AAPL"
        assert response.trades[0].side == "buy"
        assert response.trades[0].quantity == 1
        assert response.watchlist_changes == []

    def test_sell_message_returns_sell_trade(self):
        response = get_mock_response("sell TSLA now")

        assert len(response.trades) == 1
        assert response.trades[0].ticker == "TSLA"
        assert response.trades[0].side == "sell"

    def test_watch_message_returns_watchlist_add(self):
        response = get_mock_response("please watch PYPL")

        assert response.trades == []
        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "PYPL"
        assert response.watchlist_changes[0].action == "add"

    def test_add_message_returns_watchlist_add(self):
        response = get_mock_response("add NFLX to my list")

        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "NFLX"

    def test_unrecognized_message_returns_canned_response(self):
        response = get_mock_response("how is my portfolio doing")

        assert response.trades == []
        assert response.watchlist_changes == []
        assert "mock mode" in response.message.lower()

    def test_buy_without_ticker_returns_canned_response(self):
        response = get_mock_response("buy something nice for me")

        assert response.trades == []

    def test_is_deterministic(self):
        first = get_mock_response("buy AAPL please")
        second = get_mock_response("buy AAPL please")

        assert first == second
