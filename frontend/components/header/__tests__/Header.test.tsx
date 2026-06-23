import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "../Header";

describe("Header", () => {
  it("renders the formatted total value and cash balance", () => {
    render(<Header totalValue={12345.67} cashBalance={5000} connectionStatus="connected" />);

    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$12,345.67");
    expect(screen.getByTestId("header-cash-balance")).toHaveTextContent("$5,000.00");
  });

  it.each([
    ["connected", "Connected"],
    ["reconnecting", "Reconnecting"],
    ["disconnected", "Disconnected"],
  ] as const)("shows the %s status label", (status, label) => {
    render(<Header totalValue={0} cashBalance={0} connectionStatus={status} />);
    const indicator = screen.getByTestId("connection-status");
    expect(indicator).toHaveAttribute("data-status", status);
    expect(indicator).toHaveTextContent(label);
  });
});
