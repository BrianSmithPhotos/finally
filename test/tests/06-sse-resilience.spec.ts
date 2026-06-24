import { test, expect } from "@playwright/test";

test.describe("SSE connection status", () => {
  test("connection indicator reflects a live SSE connection on load", async ({ page }) => {
    await page.goto("/");

    // Indicator starts in "reconnecting" (initial state before EventSource
    // opens) and should settle to "connected" quickly once the SSE stream
    // from /api/stream/prices is established.
    const status = page.getByTestId("connection-status");
    await expect(status).toHaveAttribute("data-status", "connected", { timeout: 15_000 });

    // Sanity: the visual dot reflects the same "connected" state via its label.
    await expect(status).toContainText("Connected");
  });

  // NOTE (stretch goal, not implemented): a full disconnect/reconnect
  // simulation — e.g. killing the backend container mid-test and asserting
  // the indicator flips to "disconnected" then back to "connected" on
  // restart — is out of scope for this pass. Playwright can't drop a
  // server-side EventSource connection without controlling the container
  // lifecycle (docker stop/start) or proxying the request, which is more
  // infrastructure than this suite currently sets up. The frontend's retry
  // logic in lib/usePriceStream.ts (8s "disconnected" threshold, relying on
  // the browser's native EventSource auto-retry) is otherwise unexercised
  // by this suite.
  test.skip(true, "full disconnect/reconnect simulation is a stretch goal, see note above");
});
