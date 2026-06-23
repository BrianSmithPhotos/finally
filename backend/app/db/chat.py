"""CRUD for the chat_messages table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .connection import Database
from .models import ChatMessage

DEFAULT_USER_ID = "default"


def _row_to_message(row) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        user_id=row["user_id"],
        role=row["role"],
        content=row["content"],
        actions=row["actions"],
        created_at=row["created_at"],
    )


def insert_chat_message(
    db: Database,
    role: str,
    content: str,
    actions: str | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> ChatMessage:
    """Append a chat message. `role` is "user" or "assistant"; `actions` is a JSON
    string describing trades/watchlist changes executed as a result (None for user
    messages, or when no actions were taken)."""
    message_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (message_id, user_id, role, content, actions, created_at),
    )
    return ChatMessage(
        id=message_id,
        user_id=user_id,
        role=role,
        content=content,
        actions=actions,
        created_at=created_at,
    )


def get_chat_messages(
    db: Database, user_id: str = DEFAULT_USER_ID, limit: int | None = None
) -> list[ChatMessage]:
    """Return conversation history, oldest-to-newest. Optionally capped to the most
    recent `limit` messages, still returned in chronological order."""
    if limit is not None:
        rows = db.query(
            "SELECT * FROM (SELECT * FROM chat_messages WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC",
            (user_id, limit),
        )
    else:
        rows = db.query(
            "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,),
        )
    return [_row_to_message(row) for row in rows]
