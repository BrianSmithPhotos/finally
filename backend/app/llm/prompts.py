"""System prompt and message construction for the FinAlly chat assistant.

Expected shape of `portfolio_context` (assembled by the caller, e.g. the API
route handler, from `app.db` + `app.market` data):

    {
        "cash_balance": float,
        "total_value": float,
        "positions": [
            {
                "ticker": str,
                "quantity": float,
                "avg_cost": float,
                "current_price": float,
                "unrealized_pnl": float,
                "unrealized_pnl_percent": float,
            },
            ...
        ],
        "watchlist": [
            {"ticker": str, "price": float},
            ...
        ],
    }

All keys are optional from this module's point of view — missing keys are
rendered as "unknown" rather than raising, so a partially-assembled context
still produces a usable prompt. `positions` and `watchlist` default to an
empty list when absent.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a simulated trading \
terminal. You help the user understand and manage their virtual portfolio.

Your responsibilities:
- Analyze portfolio composition, risk concentration, and P&L.
- Suggest trades with clear reasoning grounded in the data you're given.
- Execute trades when the user asks for them or agrees to a suggestion.
- Manage the watchlist proactively (add tickers worth tracking, remove ones that \
aren't relevant anymore) when it helps the user.
- Be concise and data-driven in your responses — lead with numbers, not filler.
- Always respond with valid structured JSON matching the required schema.

This is a simulated environment with fake money. Trades you specify are executed \
automatically without a confirmation step, so only include trades you actually intend \
to make."""


def _format_positions(positions: list[dict]) -> str:
    if not positions:
        return "No open positions."
    lines = []
    for p in positions:
        lines.append(
            f"- {p.get('ticker', 'unknown')}: {p.get('quantity', 'unknown')} shares @ "
            f"avg cost {p.get('avg_cost', 'unknown')}, current price "
            f"{p.get('current_price', 'unknown')}, unrealized P&L "
            f"{p.get('unrealized_pnl', 'unknown')} "
            f"({p.get('unrealized_pnl_percent', 'unknown')}%)"
        )
    return "\n".join(lines)


def _format_watchlist(watchlist: list[dict]) -> str:
    if not watchlist:
        return "Watchlist is empty."
    lines = [f"- {w.get('ticker', 'unknown')}: {w.get('price', 'unknown')}" for w in watchlist]
    return "\n".join(lines)


def format_portfolio_context(portfolio_context: dict) -> str:
    """Render the portfolio_context dict into a readable block for the prompt."""
    cash_balance = portfolio_context.get("cash_balance", "unknown")
    total_value = portfolio_context.get("total_value", "unknown")
    positions = portfolio_context.get("positions", [])
    watchlist = portfolio_context.get("watchlist", [])

    return (
        f"Cash balance: {cash_balance}\n"
        f"Total portfolio value: {total_value}\n\n"
        f"Positions:\n{_format_positions(positions)}\n\n"
        f"Watchlist:\n{_format_watchlist(watchlist)}"
    )


def build_messages(message: str, portfolio_context: dict, history: list[dict]) -> list[dict]:
    """Build the full message list to send to the LLM.

    `history` items are expected as {"role": "user"|"assistant", "content": str}
    and are passed through unchanged, in order.
    """
    context_block = format_portfolio_context(portfolio_context)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Current portfolio state:\n{context_block}"},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": message})
    return messages
