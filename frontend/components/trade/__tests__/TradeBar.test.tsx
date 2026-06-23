import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeBar } from "../TradeBar";

describe("TradeBar", () => {
  it("calls onTrade with buy side when Buy is clicked", async () => {
    const onTrade = vi.fn().mockResolvedValue(undefined);
    render(<TradeBar onTrade={onTrade} />);

    await userEvent.type(screen.getByLabelText("Ticker"), "aapl");
    await userEvent.type(screen.getByLabelText("Quantity"), "10");
    await userEvent.click(screen.getByRole("button", { name: "Buy" }));

    expect(onTrade).toHaveBeenCalledWith("AAPL", 10, "buy");
  });

  it("calls onTrade with sell side when Sell is clicked", async () => {
    const onTrade = vi.fn().mockResolvedValue(undefined);
    render(<TradeBar onTrade={onTrade} />);

    await userEvent.type(screen.getByLabelText("Ticker"), "tsla");
    await userEvent.type(screen.getByLabelText("Quantity"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Sell" }));

    expect(onTrade).toHaveBeenCalledWith("TSLA", 3, "sell");
  });

  it("shows a validation error and skips onTrade for an invalid quantity", async () => {
    const onTrade = vi.fn();
    render(<TradeBar onTrade={onTrade} />);

    await userEvent.type(screen.getByLabelText("Ticker"), "AAPL");
    await userEvent.click(screen.getByRole("button", { name: "Buy" }));

    expect(onTrade).not.toHaveBeenCalled();
    expect(screen.getByText(/Enter a ticker and a positive quantity/)).toBeInTheDocument();
  });

  it("surfaces an error message when the trade fails", async () => {
    const onTrade = vi.fn().mockRejectedValue(new Error("Insufficient cash"));
    render(<TradeBar onTrade={onTrade} />);

    await userEvent.type(screen.getByLabelText("Ticker"), "AAPL");
    await userEvent.type(screen.getByLabelText("Quantity"), "1000");
    await userEvent.click(screen.getByRole("button", { name: "Buy" }));

    expect(await screen.findByText("Insufficient cash")).toBeInTheDocument();
  });
});
