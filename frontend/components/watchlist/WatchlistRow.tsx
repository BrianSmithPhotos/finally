"use client";

import { useEffect, useRef, useState } from "react";
import type { Direction, PriceUpdate } from "@/lib/types";
import type { PriceHistoryPoint } from "@/lib/usePriceStream";
import { formatCurrency, formatPercent } from "@/lib/format";
import { Sparkline } from "./Sparkline";

interface WatchlistRowProps {
  ticker: string;
  update: PriceUpdate | undefined;
  history: PriceHistoryPoint[];
  isSelected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export function WatchlistRow({
  ticker,
  update,
  history,
  isSelected,
  onSelect,
  onRemove,
}: WatchlistRowProps) {
  const [flashClass, setFlashClass] = useState<string>("");
  const lastPriceRef = useRef<number | null>(null);

  useEffect(() => {
    if (update === undefined) return;
    if (lastPriceRef.current !== null && update.price !== lastPriceRef.current) {
      setFlashClass(update.price > lastPriceRef.current ? "flash-up" : "flash-down");
    }
    lastPriceRef.current = update.price;
  }, [update]);

  const direction: Direction = update?.direction ?? "flat";
  const changePercent = update?.change_percent ?? 0;
  const changeColor =
    direction === "up" ? "text-up" : direction === "down" ? "text-down" : "text-gray-400";

  return (
    <tr
      className={`cursor-pointer border-b border-border-muted/60 transition-colors hover:bg-background-elevated ${
        isSelected ? "bg-background-elevated" : ""
      }`}
      onClick={() => onSelect(ticker)}
      data-testid={`watchlist-row-${ticker}`}
    >
      <td className="px-3 py-2 font-mono font-semibold">{ticker}</td>
      <td
        className={`px-3 py-2 text-right font-mono tabular-nums ${flashClass}`}
        data-testid={`watchlist-price-${ticker}`}
        onAnimationEnd={() => setFlashClass("")}
      >
        {update ? formatCurrency(update.price) : "—"}
      </td>
      <td className={`px-3 py-2 text-right font-mono tabular-nums ${changeColor}`}>
        {update ? formatPercent(changePercent) : "—"}
      </td>
      <td className="px-3 py-2">
        <Sparkline data={history} direction={direction} />
      </td>
      <td className="px-3 py-2 text-right">
        <button
          type="button"
          className="text-xs text-gray-500 hover:text-down"
          aria-label={`Remove ${ticker} from watchlist`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(ticker);
          }}
        >
          ✕
        </button>
      </td>
    </tr>
  );
}
