'use client';

import { memo, useEffect, useRef, useState } from 'react';
import { Sparkline } from './Sparkline';
import { fmtPrice, fmtPercent, directionClass } from '@/lib/format';

export interface WatchlistRowProps {
  ticker: string;
  price?: number | null;
  changePercent?: number | null;
  history: number[];
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

/**
 * A single watchlist row. Owns the price-flash effect: when `price` changes,
 * it toggles a `flash-up` / `flash-down` class (background highlight fading
 * over ~500ms via CSS animation), then clears it.
 *
 * Exported standalone so the flash behavior is unit-testable in isolation.
 */
function WatchlistRowImpl({
  ticker,
  price,
  changePercent,
  history,
  selected,
  onSelect,
  onRemove,
}: WatchlistRowProps) {
  const prevPrice = useRef<number | null | undefined>(price);
  const [flash, setFlash] = useState<'' | 'flash-up' | 'flash-down'>('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const prev = prevPrice.current;
    if (prev != null && price != null && price !== prev) {
      setFlash(price > prev ? 'flash-up' : 'flash-down');
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setFlash(''), 520);
    }
    prevPrice.current = price;
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [price]);

  return (
    <div
      role="row"
      data-testid={`watch-row-${ticker}`}
      data-flash={flash || undefined}
      onClick={() => onSelect(ticker)}
      className={`group grid cursor-pointer grid-cols-[1fr_auto_auto] items-center gap-2 border-l-2 px-3 py-2 transition-colors ${flash} ${
        selected
          ? 'border-l-accent bg-term-raised/60'
          : 'border-l-transparent hover:bg-term-raised/30'
      }`}
    >
      <div className="flex min-w-0 flex-col">
        <span className="truncate font-mono text-sm font-semibold text-term-text">
          {ticker}
        </span>
        <span className={`tnum font-mono text-2xs ${directionClass(changePercent)}`}>
          {fmtPercent(changePercent)}
        </span>
      </div>

      <Sparkline data={history} width={84} height={26} />

      <div className="flex items-center gap-2">
        <span
          className={`tnum w-20 text-right font-mono text-sm ${directionClass(
            changePercent,
          )}`}
        >
          {fmtPrice(price)}
        </span>
        <button
          type="button"
          aria-label={`Remove ${ticker} from watchlist`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove(ticker);
          }}
          className="text-term-faint opacity-0 transition-opacity hover:text-down focus:opacity-100 group-hover:opacity-100"
        >
          ×
        </button>
      </div>
    </div>
  );
}

export const WatchlistRow = memo(WatchlistRowImpl);
