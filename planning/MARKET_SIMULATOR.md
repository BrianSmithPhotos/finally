# Market Simulator Design

Approach and code structure for simulating realistic stock prices when no `MASSIVE_API_KEY` is configured (the default, recommended path for most FinAlly users — see [MARKET_INTERFACE.md](MARKET_INTERFACE.md) for how this plugs into the unified interface, and [MASSIVE_API.md](MASSIVE_API.md) for the real-data alternative).

## Overview

The simulator uses **Geometric Brownian Motion (GBM)** to generate realistic stock price paths. GBM is the standard model underlying Black-Scholes option pricing — prices evolve continuously with random noise, can't go negative, and exhibit the lognormal return distribution seen in real markets.

Updates run at ~500ms intervals, producing a continuous stream of price changes that feels alive on the watchlist UI without needing any external dependency.

## GBM Math

At each time step, a stock price evolves as:

```
S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)
```

Where:
- `S(t)` = current price
- `mu` = annualized drift (expected return), e.g. 0.05 (5%)
- `sigma` = annualized volatility, e.g. 0.20 (20%)
- `dt` = time step as a fraction of a trading year
- `Z` = standard normal random variable, `Z ~ N(0,1)`

For 500ms updates with ~252 trading days/year and ~6.5 trading hours/day:

```
dt = 0.5 / (252 * 6.5 * 3600) ≈ 8.5e-8
```

This tiny `dt` keeps per-tick moves small and realistic — large enough to be visible, small enough not to look absurd over a few minutes of watching the screen.

## Correlated Moves

Real stocks don't move independently — tech stocks tend to move together, financials move together, etc. We generate correlated random draws via **Cholesky decomposition** of a correlation matrix.

Given a correlation matrix `C`, compute `L = cholesky(C)` (lower-triangular). Then for independent standard normals `Z_independent`:

```
Z_correlated = L @ Z_independent
```

`Z_correlated` has exactly the target covariance structure while each component remains marginally `N(0,1)`.

Default correlation groups:
- **Tech**: AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX — corr ≈ 0.6 within group
- **Finance**: JPM, V — corr ≈ 0.5 within group
- **Cross-group**: ≈ 0.3 baseline correlation
- **TSLA**: lower correlation with everything (≈ 0.3) — treated as its own thing rather than forced into a sector

## Random Events

Every step, each ticker has a small probability (~0.001) of a random "event" — a sudden 2-5% move, in either direction. This adds drama and keeps a multi-minute demo visually interesting instead of flatlining.

```python
if random.random() < event_probability:
    shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
    price *= (1 + shock)
```

At ~0.1% probability per 500ms tick, that's roughly one event every ~500 seconds per ticker — with 10 tickers watched simultaneously, expect a noticeable event every ~50 seconds.

## Seed Prices

Realistic starting prices for the default watchlist:

```python
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.0,
    "GOOGL": 175.0,
    "MSFT": 420.0,
    "AMZN": 185.0,
    "TSLA": 250.0,
    "NVDA": 800.0,
    "META": 500.0,
    "JPM": 195.0,
    "V": 280.0,
    "NFLX": 600.0,
}
```

Tickers added dynamically (not in the seed list) start at a random price between $50-$300 — good enough for a simulated environment where the absolute level doesn't matter, only that it's plausible.

## Per-Ticker Parameters

Each ticker carries its own drift/volatility to reflect real-world behavior — high-growth/high-beta names swing more than banks:

```python
TICKER_PARAMS: dict[str, dict] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},   # high vol
    "NVDA":  {"sigma": 0.40, "mu": 0.08},   # high vol, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},   # low vol (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},   # low vol (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

DEFAULT_PARAMS = {"sigma": 0.25, "mu": 0.05}  # for unknown/dynamically added tickers
```

## Implementation

```python
import math
import random
import numpy as np

class GBMSimulator:
    """Generates correlated GBM price paths for multiple tickers."""

    def __init__(
        self,
        tickers: list[str],
        dt: float = 8.5e-8,
        event_probability: float = 0.001,
    ):
        self._dt = dt
        self._event_prob = event_probability
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict] = {}
        self._tickers: list[str] = []
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self.add_ticker(ticker)

    def add_ticker(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50, 300))
        self._params[ticker] = TICKER_PARAMS.get(ticker, DEFAULT_PARAMS)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance one time step. Returns {ticker: new_price}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        z_independent = np.random.standard_normal(n)
        z = self._cholesky @ z_independent if self._cholesky is not None else z_independent

        result = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu, sigma = params["mu"], params["sigma"]

            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= (1 + shock)

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    def _rebuild_cholesky(self) -> None:
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._get_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    def _get_correlation(self, t1: str, t2: str) -> float:
        tech = {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"}
        finance = {"JPM", "V"}

        if t1 in tech and t2 in tech:
            return 0.6
        if t1 in finance and t2 in finance:
            return 0.5
        if t1 == "TSLA" or t2 == "TSLA":
            return 0.3
        return 0.3  # cross-sector / unknown default
```

## File Structure

```
backend/
  app/
    market/
      simulator.py       # GBMSimulator + SimulatorDataSource (async wrapper, see MARKET_INTERFACE.md)
      seed_prices.py      # SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS constants
```

`seed_prices.py` holds just the constant dictionaries so they're easy to tune without touching simulation logic. `simulator.py` holds `GBMSimulator` plus the `SimulatorDataSource` adapter that runs it in an `asyncio` loop and writes results into the shared `PriceCache`.

## Behavior Notes

- Prices never go negative — GBM is multiplicative (`exp()` is always positive), so there's no clamping logic needed
- The tiny `dt` produces sub-cent moves per tick that accumulate naturally into realistic intraday ranges over minutes of runtime
- The correlation matrix must be positive semi-definite for Cholesky to succeed — true for any matrix built from valid pairwise correlations in `[-1, 1]` the way `_get_correlation` constructs it
- Adding a ticker mid-session rebuilds the Cholesky decomposition — O(n³) for the decomposition itself, but trivial at the scale of a watchlist (tens of tickers, not thousands)
- Removing a ticker mid-session also rebuilds it, dropping that ticker's row/column from the correlation matrix
