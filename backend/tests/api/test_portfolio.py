"""Tests for /api/portfolio routes: GET, trade execution, history."""

from __future__ import annotations

from app.db.positions import apply_buy
from app.db.snapshots import insert_portfolio_snapshot
from app.db.users import adjust_cash_balance


class TestGetPortfolio:
    def test_empty_portfolio(self, client):
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cash_balance"] == 10000.0
        assert body["positions"] == []
        assert body["total_value"] == 10000.0
        assert body["total_unrealized_pnl"] == 0.0

    def test_portfolio_with_position_uses_live_price(self, client, db):
        apply_buy(db, "AAPL", 10.0, 180.0)
        resp = client.get("/api/portfolio")
        body = resp.json()
        assert len(body["positions"]) == 1
        pos = body["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10.0
        assert pos["avg_cost"] == 180.0
        assert pos["current_price"] == 190.00
        assert pos["market_value"] == 1900.0
        assert pos["unrealized_pnl"] == 100.0
        assert body["total_value"] == 10000.0 + 1900.0
        assert body["total_unrealized_pnl"] == 100.0

    def test_position_without_cached_price_falls_back_to_avg_cost(self, client, db):
        apply_buy(db, "UNKNOWN", 5.0, 50.0)
        resp = client.get("/api/portfolio")
        pos = resp.json()["positions"][0]
        assert pos["current_price"] == 50.0
        assert pos["unrealized_pnl"] == 0.0


class TestTrade:
    def test_buy_executes_and_updates_cash(self, client, db):
        resp = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["cash_balance"] == 10000.0 - 10 * 190.0
        assert len(body["positions"]) == 1
        assert body["positions"][0]["quantity"] == 10.0

    def test_buy_insufficient_cash_returns_400(self, client):
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"}
        )
        assert resp.status_code == 400
        assert "insufficient" in resp.json()["detail"].lower()

    def test_sell_insufficient_shares_returns_400(self, client):
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 5, "side": "sell"}
        )
        assert resp.status_code == 400
        assert "insufficient" in resp.json()["detail"].lower()

    def test_sell_reduces_position_and_increases_cash(self, client, db):
        apply_buy(db, "AAPL", 10.0, 180.0)
        adjust_cash_balance(db, -1800.0)
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 4, "side": "sell"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["positions"][0]["quantity"] == 6.0
        assert body["cash_balance"] == 10000.0 - 1800.0 + 4 * 190.0

    def test_sell_full_position_removes_it(self, client, db):
        apply_buy(db, "AAPL", 10.0, 180.0)
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"}
        )
        assert resp.status_code == 200
        assert resp.json()["positions"] == []

    def test_unknown_ticker_returns_400(self, client):
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"}
        )
        assert resp.status_code == 400

    def test_invalid_side_returns_400(self, client):
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "hold"}
        )
        assert resp.status_code == 400

    def test_non_positive_quantity_returns_400(self, client):
        resp = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 0, "side": "buy"}
        )
        assert resp.status_code == 400

    def test_trade_records_snapshot(self, client, db):
        from app.db.snapshots import get_portfolio_snapshots

        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        snapshots = get_portfolio_snapshots(db)
        assert len(snapshots) == 1


class TestHistory:
    def test_history_empty(self, client):
        resp = client.get("/api/portfolio/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_returns_snapshots_chronologically(self, client, db):
        insert_portfolio_snapshot(db, 10000.0)
        insert_portfolio_snapshot(db, 10500.0)
        resp = client.get("/api/portfolio/history")
        body = resp.json()
        assert len(body) == 2
        assert body[0]["total_value"] == 10000.0
        assert body[1]["total_value"] == 10500.0
