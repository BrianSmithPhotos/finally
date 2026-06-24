import { test, expect } from "@playwright/test";

test.describe("Watchlist management", () => {
  test("can add and then remove a ticker", async ({ page }) => {
    await page.goto("/");

    const ticker = "PYPL";

    // Sanity: not present initially.
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toHaveCount(0);

    // Add via the inline form.
    await page.getByLabel("Add ticker to watchlist").fill(ticker);
    await page.getByRole("button", { name: "Add" }).click();

    const row = page.getByTestId(`watchlist-row-${ticker}`);
    await expect(row).toBeVisible();

    // Remove it again.
    await page.getByLabel(`Remove ${ticker} from watchlist`).click();
    await expect(row).toHaveCount(0);
  });
});
