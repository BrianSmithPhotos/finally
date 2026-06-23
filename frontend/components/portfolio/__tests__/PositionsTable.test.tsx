import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PositionsTable } from "../PositionsTable";
import type { Position } from "@/lib/types";

describe("PositionsTable", () => {
  it("renders an empty state when there are no positions", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByText("No open positions")).toBeInTheDocument();
  });

  it("renders position rows with correctly formatted P&L and percentages", () => {
    const positions: Position[] = [
      {
        ticker: "AAPL",
        quantity: 10,
        avg_cost: 150,
        current_price: 190,
        unrealized_pnl: 400,
        unrealized_pnl_percent: 26.6667,
      },
      {
        ticker: "TSLA",
        quantity: 5,
        avg_cost: 300,
        current_price: 250,
        unrealized_pnl: -250,
        unrealized_pnl_percent: -16.6667,
      },
    ];

    render(<PositionsTable positions={positions} />);

    const aaplRow = screen.getByTestId("position-row-AAPL");
    expect(aaplRow).toHaveTextContent("AAPL");
    expect(aaplRow).toHaveTextContent("$150.00");
    expect(aaplRow).toHaveTextContent("$190.00");
    expect(aaplRow).toHaveTextContent("+$400.00");
    expect(aaplRow).toHaveTextContent("+26.67%");

    const tslaRow = screen.getByTestId("position-row-TSLA");
    expect(tslaRow).toHaveTextContent("-$250.00");
    expect(tslaRow).toHaveTextContent("-16.67%");
  });
});
