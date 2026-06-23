import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, executeTrade, getPortfolio, sendChatMessage } from "../api";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETs /api/portfolio and returns parsed JSON", async () => {
    const payload = { cash_balance: 10000, positions: [], total_value: 10000, total_unrealized_pnl: 0 };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });

    const result = await getPortfolio();
    expect(fetch).toHaveBeenCalledWith("/api/portfolio", expect.objectContaining({ headers: expect.any(Object) }));
    expect(result).toEqual(payload);
  });

  it("POSTs a trade request with the correct body", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ticker: "AAPL", side: "buy", quantity: 10, price: 190, executed_at: "now" }),
    });

    await executeTrade({ ticker: "AAPL", quantity: 10, side: "buy" });

    expect(fetch).toHaveBeenCalledWith(
      "/api/portfolio/trade",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ ticker: "AAPL", quantity: 10, side: "buy" }),
      })
    );
  });

  it("POSTs a chat message and returns the structured response", async () => {
    const payload = { message: "Hi there", trades: [], watchlist_changes: [] };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });

    const result = await sendChatMessage("Hello");
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ message: "Hello" }) })
    );
    expect(result).toEqual(payload);
  });

  it("throws an ApiError with the response status on failure", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Insufficient cash" }),
    });

    await expect(getPortfolio()).rejects.toMatchObject({
      name: "ApiError",
      message: "Insufficient cash",
      status: 400,
    });
  });

  it("ApiError is an instance of Error", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server Error",
      json: async () => {
        throw new Error("no body");
      },
    });

    try {
      await getPortfolio();
      expect.fail("expected getPortfolio to throw");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err).toBeInstanceOf(Error);
    }
  });
});
