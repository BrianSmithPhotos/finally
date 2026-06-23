import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "../ChatPanel";
import type { ChatMessage } from "@/lib/types";

describe("ChatPanel", () => {
  it("renders a placeholder when there are no messages", () => {
    render(<ChatPanel messages={[]} isLoading={false} onSend={vi.fn()} />);
    expect(screen.getByText(/Ask FinAlly about your portfolio/)).toBeInTheDocument();
  });

  it("renders user and assistant messages", () => {
    const messages: ChatMessage[] = [
      { id: "1", role: "user", content: "What's my portfolio worth?" },
      { id: "2", role: "assistant", content: "Your portfolio is worth $12,000." },
    ];

    render(<ChatPanel messages={messages} isLoading={false} onSend={vi.fn()} />);

    expect(screen.getByText("What's my portfolio worth?")).toBeInTheDocument();
    expect(screen.getByText("Your portfolio is worth $12,000.")).toBeInTheDocument();
  });

  it("shows a loading indicator while awaiting a response", () => {
    render(<ChatPanel messages={[]} isLoading={true} onSend={vi.fn()} />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
  });

  it("calls onSend with the trimmed input and clears the field", async () => {
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} isLoading={false} onSend={onSend} />);

    const input = screen.getByLabelText("Chat message");
    await userEvent.type(input, "  Buy 5 AAPL  ");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("Buy 5 AAPL");
    expect(input).toHaveValue("");
  });

  it("does not call onSend while loading", async () => {
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} isLoading={true} onSend={onSend} />);

    const input = screen.getByLabelText("Chat message");
    expect(input).toBeDisabled();
  });

  it("collapses and expands the panel", async () => {
    render(<ChatPanel messages={[]} isLoading={false} onSend={vi.fn()} />);

    await userEvent.click(screen.getByTestId("chat-collapse"));
    expect(screen.getByTestId("chat-expand")).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("chat-expand"));
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  it("renders inline trade confirmations from the assistant", () => {
    const messages: ChatMessage[] = [
      {
        id: "1",
        role: "assistant",
        content: "Done.",
        trades: [{ ticker: "AAPL", side: "buy", quantity: 10, price: 190.5 }],
      },
    ];

    render(<ChatPanel messages={messages} isLoading={false} onSend={vi.fn()} />);
    expect(screen.getByTestId("chat-trade-confirmation")).toHaveTextContent(
      "Bought 10 AAPL @ $190.50"
    );
  });

  it("renders inline watchlist change confirmations from the assistant", () => {
    const messages: ChatMessage[] = [
      {
        id: "1",
        role: "assistant",
        content: "Done.",
        watchlist_changes: [{ ticker: "PYPL", action: "add" }],
      },
    ];

    render(<ChatPanel messages={messages} isLoading={false} onSend={vi.fn()} />);
    expect(screen.getByTestId("chat-watchlist-confirmation")).toHaveTextContent(
      "Added PYPL to watchlist"
    );
  });
});
