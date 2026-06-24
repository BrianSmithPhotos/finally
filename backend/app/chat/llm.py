"""LLM client for the chat endpoint.

Calls the model via LiteLLM -> OpenRouter with Cerebras as the inference
provider (per the project's ``cerebras`` skill), requesting Structured Outputs
matching :class:`~app.chat.schemas.LLMResponse`.

When ``LLM_MOCK=true`` no network call is made; :mod:`app.chat.mock` produces a
deterministic response instead. The caller (``app.chat.service``) decides which
path to take, but :func:`call_llm` itself is the only place that touches the
network, so failures here degrade to a safe fallback rather than crashing the
endpoint.
"""

from __future__ import annotations

import json
import logging

from app.chat.schemas import LLMResponse

logger = logging.getLogger(__name__)

# Cerebras-via-OpenRouter wiring (from the `cerebras` skill).
MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant embedded in a simulated trading "
    "workstation. You help the user understand and manage a virtual portfolio "
    "(fake money — no real-world risk).\n\n"
    "Your responsibilities:\n"
    "- Analyze portfolio composition, risk concentration, and unrealized P&L.\n"
    "- Suggest trades with brief, data-driven reasoning.\n"
    "- Execute trades when the user asks for them or agrees to a suggestion.\n"
    "- Proactively manage the watchlist (add/remove tickers) when useful.\n"
    "- Be concise and specific; cite numbers from the provided context.\n\n"
    "Only buy or sell tickers that have a live price (those in the watchlist / "
    "portfolio context). Market orders only — instant fill, no fees. Never "
    "invent prices or positions.\n\n"
    "Always respond with valid structured JSON matching the required schema: a "
    "`message` string, an optional `trades` array "
    "([{ticker, side, quantity}]), and an optional `watchlist_changes` array "
    "([{ticker, action}] where action is 'add' or 'remove'). Put any trades or "
    "watchlist changes you want performed in those arrays — they are executed "
    "automatically — and describe what you did in `message`."
)

# Safe fallback when the model returns nothing usable or the call fails.
_FALLBACK_MESSAGE = (
    "Sorry, I ran into a problem generating a response just now. Please try "
    "again in a moment."
)


def build_context_block(portfolio: dict, watchlist: list[dict]) -> str:
    """Render the portfolio + watchlist context as a compact JSON block."""
    context = {
        "cash_balance": portfolio.get("cash_balance"),
        "positions_value": portfolio.get("positions_value"),
        "total_value": portfolio.get("total_value"),
        "total_unrealized_pnl": portfolio.get("total_unrealized_pnl"),
        "positions": [
            {
                "ticker": p["ticker"],
                "quantity": p["quantity"],
                "avg_cost": p["avg_cost"],
                "current_price": p["current_price"],
                "unrealized_pnl": p["unrealized_pnl"],
                "change_percent": p["change_percent"],
            }
            for p in portfolio.get("positions", [])
        ],
        "watchlist": [
            {
                "ticker": w["ticker"],
                "price": w["price"],
                "change_percent": w["change_percent"],
            }
            for w in watchlist
        ],
    }
    return json.dumps(context, default=str)


def build_messages(
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """Assemble the chat messages: system + context + history + new message."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "Current portfolio context (JSON):\n"
            + build_context_block(portfolio, watchlist),
        },
    ]
    for msg in history:
        role = msg.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})
    return messages


def call_llm(
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
    user_message: str,
) -> LLMResponse:
    """Call the LLM and return a parsed :class:`LLMResponse`.

    Never raises: on any error (network, malformed/empty output, parse failure)
    it returns a safe fallback ``LLMResponse`` so the endpoint cannot 500.
    """
    messages = build_messages(portfolio, watchlist, history, user_message)
    try:
        # Imported lazily so importing this module (and running mock-mode tests)
        # never requires litellm to be installed/configured.
        from litellm import completion

        response = completion(
            model=MODEL,
            messages=messages,
            response_format=LLMResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content
        return parse_llm_content(content)
    except Exception:
        logger.exception("LLM call failed; returning fallback response")
        return LLMResponse(message=_FALLBACK_MESSAGE)


def parse_llm_content(content: str | None) -> LLMResponse:
    """Parse raw model content into an :class:`LLMResponse`, degrading safely.

    Handles ``None``/empty content and malformed JSON without raising.
    """
    if not content or not content.strip():
        logger.warning("LLM returned empty content; using fallback message")
        return LLMResponse(message=_FALLBACK_MESSAGE)
    try:
        return LLMResponse.model_validate_json(content)
    except Exception:
        logger.warning("LLM returned non-schema content; surfacing as plain text")
        # Treat the raw text as the conversational message rather than failing.
        return LLMResponse(message=content.strip())
