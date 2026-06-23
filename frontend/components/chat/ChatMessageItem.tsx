"use client";

import type { ChatMessage } from "@/lib/types";
import { formatCurrency, formatQuantity } from "@/lib/format";

interface ChatMessageItemProps {
  message: ChatMessage;
}

export function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={`mb-3 flex ${isUser ? "justify-end" : "justify-start"}`} data-testid="chat-message">
      <div
        className={`max-w-[90%] rounded px-3 py-2 text-sm ${
          isUser ? "bg-accent-blue/20 text-foreground" : "bg-background-elevated text-foreground"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {message.trades && message.trades.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-border-muted pt-2">
            {message.trades.map((trade, idx) => (
              <div
                key={idx}
                className={`text-xs ${trade.error ? "text-down" : "text-up"}`}
                data-testid="chat-trade-confirmation"
              >
                {trade.error
                  ? `Failed to ${trade.side} ${formatQuantity(trade.quantity)} ${trade.ticker}: ${trade.error}`
                  : `${trade.side === "buy" ? "Bought" : "Sold"} ${formatQuantity(trade.quantity)} ${trade.ticker}${
                      trade.price ? ` @ ${formatCurrency(trade.price)}` : ""
                    }`}
              </div>
            ))}
          </div>
        )}

        {message.watchlist_changes && message.watchlist_changes.length > 0 && (
          <div className="mt-2 space-y-1 border-t border-border-muted pt-2">
            {message.watchlist_changes.map((change, idx) => (
              <div
                key={idx}
                className={`text-xs ${change.error ? "text-down" : "text-accent-yellow"}`}
                data-testid="chat-watchlist-confirmation"
              >
                {change.error
                  ? `Failed to ${change.action} ${change.ticker}: ${change.error}`
                  : `${change.action === "add" ? "Added" : "Removed"} ${change.ticker} ${
                      change.action === "add" ? "to" : "from"
                    } watchlist`}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
