"""Tests for the portfolio router and trade-execution service."""

from __future__ import annotations


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestPortfolioRead:
    def test_empty_portfolio(self, client):
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cash_balance"] == 10000.0
        assert body["positions"] == []
        assert body["positions_value"] == 0.0
        assert body["total_value"] == 10000.0
        assert body["total_unrealized_pnl"] == 0.0


class TestBuy:
    def test_buy_happy_path(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "aapl", "quantity": 10, "side": "buy"},
        )
        assert resp.status_code == 200
        body = resp.json()
        trade = body["trade"]
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 190.0

        portfolio = body["portfolio"]
        assert portfolio["cash_balance"] == 10000.0 - 1900.0
        assert len(portfolio["positions"]) == 1
        pos = portfolio["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10
        assert pos["avg_cost"] == 190.0
        assert pos["current_price"] == 190.0
        assert pos["unrealized_pnl"] == 0.0
        # cash + market value preserved at the fill price
        assert portfolio["total_value"] == 10000.0

    def test_buy_insufficient_cash(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "MSFT", "quantity": 1000, "side": "buy"},
        )
        assert resp.status_code == 400
        assert "Insufficient cash" in resp.json()["detail"]
        # No state mutated.
        assert client.get("/api/portfolio").json()["cash_balance"] == 10000.0

    def test_weighted_average_cost(self, client, cache):
        # First buy at 190.
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
        )
        # Price moves to 210, buy 10 more.
        cache.update("AAPL", 210.0)
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
        )
        portfolio = client.get("/api/portfolio").json()
        pos = portfolio["positions"][0]
        assert pos["quantity"] == 20
        # (10*190 + 10*210) / 20 = 200
        assert pos["avg_cost"] == 200.0
        # market value 20*210 = 4200, cost 4000 -> pnl 200
        assert pos["current_price"] == 210.0
        assert abs(pos["unrealized_pnl"] - 200.0) < 1e-6

    def test_buy_unknown_ticker_no_price(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
        )
        assert resp.status_code == 400
        assert "No live price" in resp.json()["detail"]


class TestSell:
    def _buy(self, client, ticker, qty):
        return client.post(
            "/api/portfolio/trade",
            json={"ticker": ticker, "quantity": qty, "side": "buy"},
        )

    def test_sell_partial(self, client, cache):
        self._buy(client, "AAPL", 10)
        cache.update("AAPL", 200.0)
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 4, "side": "sell"},
        )
        assert resp.status_code == 200
        portfolio = resp.json()["portfolio"]
        pos = portfolio["positions"][0]
        assert pos["quantity"] == 6
        assert pos["avg_cost"] == 190.0  # unchanged on partial sell
        # cash: 10000 - 1900 (buy) + 4*200 (sell) = 8900
        assert portfolio["cash_balance"] == 8900.0

    def test_sell_to_zero_removes_position(self, client):
        self._buy(client, "AAPL", 5)
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
        )
        assert resp.status_code == 200
        portfolio = resp.json()["portfolio"]
        assert portfolio["positions"] == []
        # cash restored to 10000 (bought and sold at same price)
        assert portfolio["cash_balance"] == 10000.0

    def test_sell_insufficient_shares(self, client):
        self._buy(client, "AAPL", 2)
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
        )
        assert resp.status_code == 400
        assert "Insufficient shares" in resp.json()["detail"]

    def test_sell_no_position(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "sell"},
        )
        assert resp.status_code == 400
        assert "No position" in resp.json()["detail"]


class TestValidation:
    def test_zero_quantity_rejected(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
        )
        assert resp.status_code == 422  # pydantic gt=0

    def test_bad_side_rejected(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "hold"},
        )
        assert resp.status_code == 422


class TestHistory:
    def test_history_records_after_trades(self, client):
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "sell"},
        )
        resp = client.get("/api/portfolio/history")
        assert resp.status_code == 200
        snapshots = resp.json()["snapshots"]
        # One snapshot per trade.
        assert len(snapshots) == 2
        assert all("total_value" in s for s in snapshots)
