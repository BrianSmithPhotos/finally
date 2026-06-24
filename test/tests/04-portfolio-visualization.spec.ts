import { test, expect } from "@playwright/test";
import { waitForFirstPrice } from "./fixtures";

// Uses MSFT, distinct from the AAPL/NVDA used by the trading and chat specs,
// so this test doesn't depend on (or disturb) state from other spec files
// sharing the same backend/DB instance.
const TICKER = "MSFT";

test.describe("Portfolio visualization", () => {
  test("heatmap renders a position and the P&L chart gains data points after a trade", async ({
    page,
  }) => {
    await page.goto("/");
    await waitForFirstPrice(page, TICKER);

    // Execute a trade to create a position and a fresh portfolio snapshot.
    const tradeBar = page.getByTestId("trade-bar");
    await tradeBar.getByLabel("Ticker").fill(TICKER);
    await tradeBar.getByLabel("Quantity").fill("3");
    await tradeBar.getByRole("button", { name: "Buy" }).click();

    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

    // Heatmap: the empty-state message is gone and a treemap cell with the
    // ticker label is rendered (recharts renders SVG <text>, not a DOM
    // element with a stable test id, so we assert on rendered text).
    const heatmap = page.getByTestId("heatmap");
    await expect(heatmap).not.toContainText("No open positions");
    await expect(heatmap.locator("svg")).toBeVisible();
    await expect(heatmap.locator("text", { hasText: TICKER })).toBeVisible();

    // P&L chart: a snapshot is recorded immediately after trade execution
    // (PLAN.md §7), but the chart only renders once it has >= 2 snapshots.
    // Execute a second small trade to force another snapshot directly
    // rather than waiting on the 30s periodic background snapshot.
    await tradeBar.getByLabel("Ticker").fill(TICKER);
    await tradeBar.getByLabel("Quantity").fill("1");
    await tradeBar.getByRole("button", { name: "Buy" }).click();
    await expect(page.getByTestId(`position-row-${TICKER}`)).toBeVisible();

    const pnlChart = page.getByTestId("pnl-chart");
    await expect(pnlChart).not.toContainText("Not enough history yet", { timeout: 15_000 });
    await expect(pnlChart.locator("svg")).toBeVisible();
  });
});
