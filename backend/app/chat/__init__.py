"""AI chat subsystem (PLAN.md Section 9).

Owns the `POST /api/chat` endpoint: it builds portfolio/watchlist context,
calls the LLM (LiteLLM -> OpenRouter, Cerebras inference) with structured
outputs, auto-executes any returned trades/watchlist changes through the shared
`app.services` seam, persists the conversation, and returns a structured
response enriched with per-action status for inline UI confirmations.

When `LLM_MOCK=true` the LLM call is replaced by a deterministic mock so the
endpoint runs with no network access (used by the E2E suite).
"""

from app.chat.router import router as chat_router

__all__ = ["chat_router"]
