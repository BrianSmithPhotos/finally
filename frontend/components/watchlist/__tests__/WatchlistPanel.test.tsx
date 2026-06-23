import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WatchlistPanel } from "../WatchlistPanel";

describe("WatchlistPanel", () => {
  it("renders a row for every ticker", () => {
    render(
      <WatchlistPanel
        tickers={["AAPL", "GOOGL"]}
        prices={{}}
        history={{}}
        selectedTicker={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
      />
    );

    expect(screen.getByTestId("watchlist-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-row-GOOGL")).toBeInTheDocument();
  });

  it("calls onAdd with the uppercased, trimmed ticker on submit", async () => {
    const onAdd = vi.fn();
    render(
      <WatchlistPanel
        tickers={[]}
        prices={{}}
        history={{}}
        selectedTicker={null}
        onSelect={vi.fn()}
        onAdd={onAdd}
        onRemove={vi.fn()}
      />
    );

    const input = screen.getByLabelText("Add ticker to watchlist");
    await userEvent.type(input, "  pypl  ");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(onAdd).toHaveBeenCalledWith("PYPL");
  });

  it("does not call onAdd for an empty submission", async () => {
    const onAdd = vi.fn();
    render(
      <WatchlistPanel
        tickers={[]}
        prices={{}}
        history={{}}
        selectedTicker={null}
        onSelect={vi.fn()}
        onAdd={onAdd}
        onRemove={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("calls onRemove when a row's remove button is clicked", async () => {
    const onRemove = vi.fn();
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{}}
        history={{}}
        selectedTicker={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={onRemove}
      />
    );

    await userEvent.click(screen.getByLabelText("Remove AAPL from watchlist"));
    expect(onRemove).toHaveBeenCalledWith("AAPL");
  });
});
