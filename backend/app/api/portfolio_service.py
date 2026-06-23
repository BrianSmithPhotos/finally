"""Shared portfolio valuation logic used by the portfolio and chat routes."""

from __future__ import annotations

from app.db import Database, Position, get_positions, get_user_profile
from app.market import PriceCache

from .schemas import PortfolioResponse, PositionView


def _price_for(price_cache: PriceCache, ticker: str, position: Position) -> float:
    price = price_cache.get_price(ticker)
    return price if price is not None else position.avg_cost


def build_position_view(price_cache: PriceCache, position: Position) -> PositionView:
    current_price = _price_for(price_cache, position.ticker, position)
    market_value = position.quantity * current_price
    cost_basis = position.quantity * position.avg_cost
    unrealized_pnl = market_value - cost_basis
    unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0
    return PositionView(
        ticker=position.ticker,
        quantity=position.quantity,
        avg_cost=position.avg_cost,
        current_price=current_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_percent=unrealized_pnl_percent,
    )


def build_portfolio_response(db: Database, price_cache: PriceCache) -> PortfolioResponse:
    profile = get_user_profile(db)
    cash_balance = profile.cash_balance if profile else 0.0
    positions = [build_position_view(price_cache, p) for p in get_positions(db)]
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
    total_value = cash_balance + sum(p.market_value for p in positions)
    return PortfolioResponse(
        cash_balance=cash_balance,
        positions=positions,
        total_value=total_value,
        total_unrealized_pnl=total_unrealized_pnl,
    )


def portfolio_context_dict(db: Database, price_cache: PriceCache) -> dict:
    """Plain-dict portfolio summary for the LLM prompt context (PLAN.md §9)."""
    response = build_portfolio_response(db, price_cache)
    return response.model_dump()
