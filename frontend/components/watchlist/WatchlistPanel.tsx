"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { PriceUpdate } from "@/lib/types";
import type { PriceHistoryPoint } from "@/lib/usePriceStream";
import { WatchlistRow } from "./WatchlistRow";

interface WatchlistPanelProps {
  tickers: string[];
  prices: Record<string, PriceUpdate>;
  history: Record<string, PriceHistoryPoint[]>;
  selectedTicker: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export function WatchlistPanel({
  tickers,
  prices,
  history,
  selectedTicker,
  onSelect,
  onAdd,
  onRemove,
}: WatchlistPanelProps) {
  const [newTicker, setNewTicker] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = newTicker.trim().toUpperCase();
    if (!trimmed) return;
    onAdd(trimmed);
    setNewTicker("");
  };

  return (
    <section className="flex flex-col rounded border border-border-muted bg-background-panel" data-testid="watchlist-panel">
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Watchlist</h2>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">Chg %</th>
            <th className="px-3 py-2">Trend</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {tickers.map((ticker) => (
            <WatchlistRow
              key={ticker}
              ticker={ticker}
              update={prices[ticker]}
              history={history[ticker] ?? []}
              isSelected={ticker === selectedTicker}
              onSelect={onSelect}
              onRemove={onRemove}
            />
          ))}
        </tbody>
      </table>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border-muted p-2">
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          placeholder="Add ticker..."
          aria-label="Add ticker to watchlist"
          className="flex-1 rounded border border-border-muted bg-background px-2 py-1 text-sm uppercase outline-none focus:border-accent-blue"
        />
        <button
          type="submit"
          className="rounded bg-accent-blue px-3 py-1 text-sm font-medium text-white hover:opacity-90"
        >
          Add
        </button>
      </form>
    </section>
  );
}
