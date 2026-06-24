import type { Page } from "@playwright/test";

export const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

/**
 * Waits for at least one watchlist row to show a real price (i.e. the SSE
 * stream has delivered at least one update for it). Used as a readiness gate
 * before assertions that depend on live prices.
 */
export async function waitForFirstPrice(page: Page, ticker: string) {
  const priceCell = page.getByTestId(`watchlist-price-${ticker}`);
  await priceCell.waitFor({ state: "visible" });
  // eslint-disable-next-line no-restricted-syntax
  await page.waitForFunction(
    (testId) => {
      const el = document.querySelector(`[data-testid="${testId}"]`);
      return !!el && el.textContent !== "—" && el.textContent !== "";
    },
    `watchlist-price-${ticker}`,
    { timeout: 15_000 }
  );
}

export function priceText(page: Page, ticker: string) {
  return page.getByTestId(`watchlist-price-${ticker}`);
}
