import { test, expect } from "@playwright/test";
import { waitForFirstPrice } from "./fixtures";

test.describe("AI chat (LLM_MOCK=true)", () => {
  test("sending a buy-style message renders the assistant reply and an inline trade confirmation", async ({
    page,
  }) => {
    await page.goto("/");
    await waitForFirstPrice(page, "NVDA");

    // Per backend/app/llm/mock.py: a message containing "buy" plus an
    // all-caps ticker-like token triggers a deterministic mock buy of 1
    // share of that ticker.
    await page.getByLabel("Chat message").fill("Please buy NVDA for me");

    const cashCell = page.getByTestId("header-cash-balance");
    const cashBefore = Number(((await cashCell.textContent()) ?? "").replace(/[$,]/g, ""));

    await page.getByRole("button", { name: "Send" }).click();

    // Loading indicator appears while waiting, then the assistant message renders.
    await expect(page.getByTestId("chat-loading")).toBeVisible();

    const messages = page.getByTestId("chat-message");
    await expect(messages.last()).toContainText("Mock mode", { timeout: 15_000 });

    // Trade confirmation rendered inline in the assistant's message.
    const confirmation = page.getByTestId("chat-trade-confirmation").last();
    await expect(confirmation).toBeVisible();
    await expect(confirmation).toContainText("NVDA");
    await expect(confirmation).toContainText("Bought");

    // The trade actually executed: cash decreased and a position appeared.
    await expect
      .poll(async () => {
        const text = (await cashCell.textContent()) ?? "";
        return Number(text.replace(/[$,]/g, ""));
      }, { timeout: 10_000 })
      .toBeLessThan(cashBefore);

    await expect(page.getByTestId("position-row-NVDA")).toBeVisible();
  });

  test("a plain question gets a canned analytical response with no actions", async ({ page }) => {
    await page.goto("/");

    await page.getByLabel("Chat message").fill("how is my portfolio doing");
    await page.getByRole("button", { name: "Send" }).click();

    const messages = page.getByTestId("chat-message");
    await expect(messages.last()).toContainText("balanced", { timeout: 15_000 });
    await expect(page.getByTestId("chat-trade-confirmation")).toHaveCount(0);
    await expect(page.getByTestId("chat-watchlist-confirmation")).toHaveCount(0);
  });
});
