"""Tests for get_chat_response: mock mode, structured parsing, and fallback."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.llm.chat import get_chat_response
from app.llm.schemas import ChatResponse

PORTFOLIO_CONTEXT = {
    "cash_balance": 8000.0,
    "total_value": 10000.0,
    "positions": [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "avg_cost": 150.0,
            "current_price": 190.0,
            "unrealized_pnl": 400.0,
            "unrealized_pnl_percent": 26.67,
        }
    ],
    "watchlist": [{"ticker": "GOOGL", "price": 175.5}],
}


def _make_llm_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@pytest.mark.asyncio
class TestMockMode:
    """LLM_MOCK=true must be fully deterministic and never touch the network."""

    async def test_mock_mode_makes_no_network_call(self):
        with patch.dict(os.environ, {"LLM_MOCK": "true"}, clear=False):
            with patch("app.llm.chat.completion") as mock_completion:
                response = await get_chat_response("buy AAPL", PORTFOLIO_CONTEXT, [])

        mock_completion.assert_not_called()
        assert isinstance(response, ChatResponse)
        assert response.trades[0].ticker == "AAPL"
        assert response.trades[0].side == "buy"

    async def test_mock_mode_is_case_insensitive_flag(self):
        with patch.dict(os.environ, {"LLM_MOCK": "True"}, clear=False):
            with patch("app.llm.chat.completion") as mock_completion:
                await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        mock_completion.assert_not_called()

    async def test_llm_mock_false_does_not_use_mock_path(self):
        valid_json = ChatResponse(message="real response").model_dump_json()

        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch(
                "app.llm.chat.completion", return_value=_make_llm_response(valid_json)
            ) as mock_completion:
                response = await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        mock_completion.assert_called_once()
        assert response.message == "real response"


@pytest.mark.asyncio
class TestStructuredOutputParsing:
    """A valid structured response from the LLM should parse cleanly."""

    async def test_parses_valid_response_with_trades_and_watchlist(self):
        payload = ChatResponse(
            message="Buying AAPL and adding PYPL to watchlist.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
            watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
        ).model_dump_json()

        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch("app.llm.chat.completion", return_value=_make_llm_response(payload)):
                response = await get_chat_response("buy 5 AAPL", PORTFOLIO_CONTEXT, [])

        assert response.message == "Buying AAPL and adding PYPL to watchlist."
        assert len(response.trades) == 1
        assert response.trades[0].ticker == "AAPL"
        assert response.trades[0].quantity == 5
        assert len(response.watchlist_changes) == 1
        assert response.watchlist_changes[0].ticker == "PYPL"

    async def test_calls_completion_with_expected_model_and_provider(self):
        payload = ChatResponse(message="ok").model_dump_json()

        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch(
                "app.llm.chat.completion", return_value=_make_llm_response(payload)
            ) as mock_completion:
                await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        _, kwargs = mock_completion.call_args
        assert kwargs["model"] == "openrouter/openai/gpt-oss-120b"
        assert kwargs["extra_body"] == {"provider": {"order": ["cerebras"]}}
        assert kwargs["response_format"] is ChatResponse


@pytest.mark.asyncio
class TestMalformedResponseFallback:
    """Malformed/failed responses should degrade gracefully, never raise."""

    async def test_invalid_json_falls_back_to_message_only_response(self):
        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch(
                "app.llm.chat.completion",
                return_value=_make_llm_response("not valid json at all"),
            ):
                response = await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        assert isinstance(response, ChatResponse)
        assert response.trades == []
        assert response.watchlist_changes == []
        assert response.message

    async def test_completion_raising_exception_falls_back_gracefully(self):
        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch("app.llm.chat.completion", side_effect=RuntimeError("network down")):
                response = await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        assert isinstance(response, ChatResponse)
        assert response.trades == []
        assert response.watchlist_changes == []

    async def test_retries_once_then_succeeds(self):
        valid_json = ChatResponse(message="second try worked").model_dump_json()

        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch(
                "app.llm.chat.completion",
                side_effect=[_make_llm_response("garbage"), _make_llm_response(valid_json)],
            ) as mock_completion:
                response = await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        assert mock_completion.call_count == 2
        assert response.message == "second try worked"

    async def test_never_raises_after_two_failed_attempts(self):
        with patch.dict(os.environ, {"LLM_MOCK": "false"}, clear=False):
            with patch(
                "app.llm.chat.completion",
                side_effect=[_make_llm_response("garbage"), _make_llm_response("still garbage")],
            ) as mock_completion:
                response = await get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        assert mock_completion.call_count == 2
        assert isinstance(response, ChatResponse)
        assert response.message
