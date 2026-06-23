"""Tests for prompt/message construction."""

from app.llm.prompts import SYSTEM_PROMPT, build_messages, format_portfolio_context


class TestFormatPortfolioContext:
    """Tests for format_portfolio_context."""

    def test_includes_cash_and_total_value(self):
        context = {"cash_balance": 5000.0, "total_value": 12000.0}

        rendered = format_portfolio_context(context)

        assert "5000.0" in rendered
        assert "12000.0" in rendered

    def test_includes_position_details(self):
        context = {
            "cash_balance": 1000.0,
            "total_value": 2000.0,
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
        }

        rendered = format_portfolio_context(context)

        assert "AAPL" in rendered
        assert "150.0" in rendered
        assert "190.0" in rendered
        assert "400.0" in rendered

    def test_includes_watchlist_details(self):
        context = {
            "cash_balance": 1000.0,
            "total_value": 1000.0,
            "watchlist": [{"ticker": "GOOGL", "price": 175.5}],
        }

        rendered = format_portfolio_context(context)

        assert "GOOGL" in rendered
        assert "175.5" in rendered

    def test_handles_empty_positions_and_watchlist(self):
        context = {"cash_balance": 10000.0, "total_value": 10000.0}

        rendered = format_portfolio_context(context)

        assert "No open positions" in rendered
        assert "Watchlist is empty" in rendered

    def test_handles_missing_keys_gracefully(self):
        rendered = format_portfolio_context({})

        assert "unknown" in rendered
        assert "No open positions" in rendered
        assert "Watchlist is empty" in rendered


class TestBuildMessages:
    """Tests for build_messages."""

    def test_includes_system_prompt(self):
        messages = build_messages("hello", {"cash_balance": 100, "total_value": 100}, [])

        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT

    def test_includes_portfolio_context_block(self):
        context = {"cash_balance": 100, "total_value": 100, "positions": [], "watchlist": []}

        messages = build_messages("hello", context, [])

        assert any("Cash balance" in m["content"] for m in messages if m["role"] == "system")

    def test_includes_history_in_order(self):
        history = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "first reply"},
        ]

        messages = build_messages("second message", {}, history)

        assert messages[2] == history[0]
        assert messages[3] == history[1]

    def test_appends_new_user_message_last(self):
        messages = build_messages("what is my balance", {}, [])

        assert messages[-1] == {"role": "user", "content": "what is my balance"}
