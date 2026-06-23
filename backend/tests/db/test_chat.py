"""Tests for chat_messages CRUD."""

from __future__ import annotations

import time

from app.db.chat import get_chat_messages, insert_chat_message


class TestChat:
    def test_no_messages_initially(self, db):
        assert get_chat_messages(db) == []

    def test_insert_user_message(self, db):
        msg = insert_chat_message(db, "user", "What's my portfolio worth?")
        assert msg.role == "user"
        assert msg.content == "What's my portfolio worth?"
        assert msg.actions is None

    def test_insert_assistant_message_with_actions(self, db):
        msg = insert_chat_message(
            db, "assistant", "Bought 10 AAPL.", actions='{"trades": [{"ticker": "AAPL"}]}'
        )
        assert msg.actions == '{"trades": [{"ticker": "AAPL"}]}'

    def test_get_messages_chronological_order(self, db):
        insert_chat_message(db, "user", "first")
        time.sleep(0.01)
        insert_chat_message(db, "assistant", "second")
        messages = get_chat_messages(db)
        assert len(messages) == 2
        assert messages[0].content == "first"
        assert messages[1].content == "second"

    def test_get_messages_limit_keeps_chronological_order(self, db):
        for i in range(5):
            insert_chat_message(db, "user", f"msg {i}")
            time.sleep(0.005)
        messages = get_chat_messages(db, limit=2)
        assert len(messages) == 2
        assert messages[0].content == "msg 3"
        assert messages[1].content == "msg 4"

    def test_messages_scoped_per_user(self, db):
        insert_chat_message(db, "user", "hello", user_id="other")
        assert get_chat_messages(db, user_id="default") == []
        assert len(get_chat_messages(db, user_id="other")) == 1
