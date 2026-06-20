"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


def _make_request(disconnected: bool = False, client_host: str = "127.0.0.1") -> MagicMock:
    """Build a mock Request with an async is_disconnected()."""
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=disconnected)
    if client_host is None:
        request.client = None
    else:
        request.client = MagicMock(host=client_host)
    return request


class TestGenerateEvents:
    """Unit tests for the `_generate_events` async generator."""

    async def test_first_chunk_is_retry_directive(self):
        cache = PriceCache()
        request = _make_request(disconnected=True)

        gen = _generate_events(cache, request, interval=0.01)
        first = await gen.__anext__()

        assert first == "retry: 1000\n\n"

    async def test_yields_data_event_when_cache_has_prices(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        request = _make_request(disconnected=False)

        gen = _generate_events(cache, request, interval=0.01)
        await gen.__anext__()  # retry directive

        # Make the next is_disconnected() call return True so the loop exits
        # after this iteration, but only after the data has been yielded.
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        event = await gen.__anext__()

        assert event.startswith("data: ")
        payload = json.loads(event[len("data: ") : -2])
        assert payload["AAPL"]["ticker"] == "AAPL"
        assert payload["AAPL"]["price"] == 190.50
        assert payload["AAPL"]["direction"] == "flat"

    async def test_no_event_when_version_unchanged(self):
        """The generator should not yield a data event on a tick where the
        cache version hasn't changed since the last send."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        request = _make_request(disconnected=False)
        request.is_disconnected = AsyncMock(side_effect=[False, False, True])

        gen = _generate_events(cache, request, interval=0.01)
        await gen.__anext__()  # retry directive
        first_data_event = await gen.__anext__()
        assert first_data_event.startswith("data: ")

        # No new price update happened, so the next yielded item — if any —
        # must not be another data event before the generator stops.
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    async def test_stops_on_disconnect(self):
        cache = PriceCache()
        request = _make_request(disconnected=True)

        gen = _generate_events(cache, request, interval=0.01)
        await gen.__anext__()  # retry directive

        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    async def test_no_event_when_cache_empty(self):
        cache = PriceCache()
        request = _make_request(disconnected=False)
        request.is_disconnected = AsyncMock(side_effect=[False, True])

        gen = _generate_events(cache, request, interval=0.01)
        await gen.__anext__()  # retry directive

        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    async def test_handles_missing_client(self):
        """request.client can be None (e.g. behind certain proxies/test
        clients) — the generator should not raise."""
        cache = PriceCache()
        request = _make_request(disconnected=True, client_host=None)

        gen = _generate_events(cache, request, interval=0.01)
        first = await gen.__anext__()

        assert first == "retry: 1000\n\n"


class TestStreamRouter:
    """Smoke tests for the FastAPI router wiring (headers, response type).

    These call the route's endpoint coroutine directly rather than going
    through a real ASGI transport, so the test isn't at the mercy of
    StreamingResponse buffering/timing in a test HTTP client — the endpoint
    is exercised exactly as FastAPI would call it, just without the network.
    """

    def test_router_has_prices_route(self):
        cache = PriceCache()
        router = create_stream_router(cache)

        paths = [route.path for route in router.routes]
        assert "/api/stream/prices" in paths

    async def test_route_returns_event_stream_response(self):
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        router = create_stream_router(cache)

        endpoint = router.routes[0].endpoint
        request = _make_request(disconnected=True)

        response = await endpoint(request)

        assert response.media_type == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-accel-buffering"] == "no"

        # The body iterator is the same _generate_events generator under test
        # above; just confirm it yields the retry directive first.
        first_chunk = await response.body_iterator.__anext__()
        assert first_chunk == "retry: 1000\n\n"
