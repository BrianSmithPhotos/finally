import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WatchlistRow } from "../WatchlistRow";
import type { PriceUpdate } from "@/lib/types";

function makeUpdate(price: number, direction: PriceUpdate["direction"] = "flat"): PriceUpdate {
  return {
    ticker: "AAPL",
    price,
    previous_price: price,
    timestamp: Date.now() / 1000,
    change: 0,
    change_percent: 0,
    direction,
  };
}

describe("WatchlistRow", () => {
  it("renders the ticker, price, and change percent", () => {
    render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={{ ...makeUpdate(190.5, "up"), change_percent: 1.25 }}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("$190.50");
    expect(screen.getByText("+1.25%")).toBeInTheDocument();
  });

  it("renders a placeholder when no price update has arrived yet", () => {
    render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={undefined}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveTextContent("—");
  });

  it("applies a flash-up class when the price increases between renders", () => {
    const { rerender } = render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(100)}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    rerender(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(101, "up")}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveClass("flash-up");
  });

  it("applies a flash-down class when the price decreases between renders", () => {
    const { rerender } = render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(100)}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    rerender(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(99, "down")}
            history={[]}
            isSelected={false}
            onSelect={vi.fn()}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    expect(screen.getByTestId("watchlist-price-AAPL")).toHaveClass("flash-down");
  });

  it("calls onSelect when the row is clicked", async () => {
    const onSelect = vi.fn();
    render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(100)}
            history={[]}
            isSelected={false}
            onSelect={onSelect}
            onRemove={vi.fn()}
          />
        </tbody>
      </table>
    );

    await userEvent.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(onSelect).toHaveBeenCalledWith("AAPL");
  });

  it("calls onRemove without triggering onSelect when the remove button is clicked", async () => {
    const onSelect = vi.fn();
    const onRemove = vi.fn();
    render(
      <table>
        <tbody>
          <WatchlistRow
            ticker="AAPL"
            update={makeUpdate(100)}
            history={[]}
            isSelected={false}
            onSelect={onSelect}
            onRemove={onRemove}
          />
        </tbody>
      </table>
    );

    await userEvent.click(screen.getByLabelText("Remove AAPL from watchlist"));
    expect(onRemove).toHaveBeenCalledWith("AAPL");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
