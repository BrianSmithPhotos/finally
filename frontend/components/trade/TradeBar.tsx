"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { TradeSide } from "@/lib/types";

interface TradeBarProps {
  defaultTicker?: string;
  onTrade: (ticker: string, quantity: number, side: TradeSide) => Promise<void>;
}

export function TradeBar({ defaultTicker, onTrade }: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker ?? "");
  const [quantity, setQuantity] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent, side: TradeSide) => {
    e.preventDefault();
    setError(null);

    const trimmedTicker = ticker.trim().toUpperCase();
    const qty = Number(quantity);

    if (!trimmedTicker || !Number.isFinite(qty) || qty <= 0) {
      setError("Enter a ticker and a positive quantity");
      return;
    }

    setSubmitting(true);
    try {
      await onTrade(trimmedTicker, qty, side);
      setQuantity("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section
      className="flex flex-col gap-2 rounded border border-border-muted bg-background-panel p-3"
      data-testid="trade-bar"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Trade</h2>
      <form className="flex items-end gap-2">
        <div className="flex flex-col gap-1">
          <label htmlFor="trade-ticker" className="text-xs text-gray-500">
            Ticker
          </label>
          <input
            id="trade-ticker"
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="w-24 rounded border border-border-muted bg-background px-2 py-1 text-sm uppercase outline-none focus:border-accent-blue"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="trade-quantity" className="text-xs text-gray-500">
            Quantity
          </label>
          <input
            id="trade-quantity"
            type="number"
            min="0"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-24 rounded border border-border-muted bg-background px-2 py-1 text-sm outline-none focus:border-accent-blue"
          />
        </div>

        <button
          type="button"
          disabled={submitting}
          onClick={(e) => handleSubmit(e, "buy")}
          className="rounded bg-accent-purple px-4 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          Buy
        </button>

        <button
          type="button"
          disabled={submitting}
          onClick={(e) => handleSubmit(e, "sell")}
          className="rounded border border-down px-4 py-1.5 text-sm font-medium text-down hover:bg-down/10 disabled:opacity-50"
        >
          Sell
        </button>
      </form>

      {error && <p className="text-xs text-down">{error}</p>}
    </section>
  );
}
