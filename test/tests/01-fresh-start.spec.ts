import { test, expect } from "@playwright/test";
import { DEFAULT_TICKERS, waitForFirstPrice } from "./fixtures";

test.describe("Fresh start", () => {
  test("shows default watchlist, $10,000 cash, and streaming prices", async ({ page }) => {
    await page.goto("/");

    // Header shows starting cash balance and total portfolio value.
    await expect(page.getByTestId("header-cash-balance")).toHaveText("$10,000.00");
    await expect(page.getByTestId("header-total-value")).toHaveText("$10,000.00");

    // All 10 default tickers are present in the watchlist.
    for (const ticker of DEFAULT_TICKERS) {
      await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
    }

    // Connection status should reach "connected" once the SSE stream opens.
    await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected", {
      timeout: 15_000,
    });

    // Prices stream in: wait for the first tick on AAPL, then capture it...
    await waitForFirstPrice(page, "AAPL");
    const firstPriceText = await page.getByTestId("watchlist-price-AAPL").textContent();
    expect(firstPriceText).toMatch(/^\$\d/);

    // ...then wait for at least one more update, confirming live polling/streaming
    // (PLAN.md: simulator updates ~every 500ms) rather than a single static value.
    await expect
      .poll(
        async () => page.getByTestId("watchlist-price-AAPL").textContent(),
        { timeout: 15_000, intervals: [500] }
      )
      .not.toBe(firstPriceText);

    // Positions table starts empty.
    await expect(page.getByTestId("positions-table")).toContainText("No open positions");
  });
});
