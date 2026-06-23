"""Chat entry point: get_chat_response(message, portfolio_context, history).

Calls the LLM via LiteLLM -> OpenRouter, with Cerebras as the inference
provider, requesting a structured ChatResponse. Falls back to LLM_MOCK
deterministic responses when LLM_MOCK=true (no network call in that path),
and degrades gracefully to a message-only ChatResponse if the model fails to
return valid structured output after one retry.
"""

from __future__ import annotations

import logging
import os

from litellm import completion

from .mock import get_mock_response
from .prompts import build_messages
from .schemas import ChatResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

_FALLBACK_MESSAGE = (
    "Sorry, I had trouble processing that request. Please try rephrasing or try again."
)


def _is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "false").strip().lower() == "true"


def _call_llm(messages: list[dict]) -> ChatResponse | None:
    """Call the LLM once and try to parse a ChatResponse. Returns None on failure."""
    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=ChatResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content
        return ChatResponse.model_validate_json(content)
    except Exception:
        logger.exception("LLM call or response parsing failed")
        return None


async def get_chat_response(
    message: str, portfolio_context: dict, history: list[dict]
) -> ChatResponse:
    """Get a structured chat response for the given user message.

    See app.llm.prompts module docstring for the expected shape of
    `portfolio_context`. `history` is a list of {"role": ..., "content": ...}
    dicts in chronological order.
    """
    if _is_mock_mode():
        return get_mock_response(message)

    messages = build_messages(message, portfolio_context, history)

    result = _call_llm(messages)
    if result is not None:
        return result

    result = _call_llm(messages)
    if result is not None:
        return result

    return ChatResponse(message=_FALLBACK_MESSAGE)
