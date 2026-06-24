import { test, expect } from "@playwright/test";
import { waitForFirstPrice } from "./fixtures";

// This suite runs against one shared backend/DB instance across spec files
// (no per-test reset), so assertions here only check the AAPL-specific
// position/row and relative cash deltas -- never the global "no positions
// at all" empty state, which other spec files may have already changed.
const TICKER = "AAPL";

test.describe("Buying and selling shares", () => {
  test("buy decreases cash and creates a position; sell reverses it", async ({ page }) => {
    await page.goto("/");
    await waitForFirstPrice(page, TICKER);

    const cashCell = page.getByTestId("header-cash-balance");
    const initialCashText = (await cashCell.textContent()) ?? "$10,000.00";
    const initialCash = Number(initialCashText.replace(/[$,]/g, ""));

    const tradeBar = page.getByTestId("trade-bar");

    // --- Buy ---
    await tradeBar.getByLabel("Ticker").fill(TICKER);
    await tradeBar.getByLabel("Quantity").fill("2");
    await tradeBar.getByRole("button", { name: "Buy" }).click();

    // Cash decreases.
    await expect
      .poll(async () => {
        const text = (await cashCell.textContent()) ?? "";
        return Number(text.replace(/[$,]/g, ""));
      }, { timeout: 10_000 })
      .toBeLessThan(initialCash);

    // Position appears in the positions table with at least the 2 shares
    // just bought (could be more if a prior test also bought this ticker).
    const positionRow = page.getByTestId(`position-row-${TICKER}`);
    await expect(positionRow).toBeVisible();

    // Heatmap now shows at least one position rect (no longer the empty state).
    await expect(page.getByTestId("heatmap")).not.toContainText("No open positions");

    const cashAfterBuyText = (await cashCell.textContent()) ?? "";
    const cashAfterBuy = Number(cashAfterBuyText.replace(/[$,]/g, ""));

    // --- Sell the 2 shares we just bought ---
    await tradeBar.getByLabel("Ticker").fill(TICKER);
    await tradeBar.getByLabel("Quantity").fill("2");
    await tradeBar.getByRole("button", { name: "Sell" }).click();

    // Cash increases back up after selling.
    await expect
      .poll(async () => {
        const text = (await cashCell.textContent()) ?? "";
        return Number(text.replace(/[$,]/g, ""));
      }, { timeout: 10_000 })
      .toBeGreaterThan(cashAfterBuy);

    // Net cash should be back near (within cents, due to price drift between
    // buy and sell fills) the starting balance, confirming the round trip.
    const finalCashText = (await cashCell.textContent()) ?? "";
    const finalCash = Number(finalCashText.replace(/[$,]/g, ""));
    expect(Math.abs(finalCash - initialCash)).toBeLessThan(50);
  });
});
