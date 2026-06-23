"""Fixtures for database layer tests."""

from __future__ import annotations

import pytest

from app.db.connection import Database


@pytest.fixture
def db(tmp_path):
    """A fresh Database backed by a temp file, schema created and seeded."""
    database = Database(tmp_path / "test.db")
    yield database
    database.close()
