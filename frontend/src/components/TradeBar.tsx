'use client';

import { useEffect, useState } from 'react';
import { useTerminal } from '@/hooks/useTerminal';
import { fmtPrice } from '@/lib/format';

export function TradeBar() {
  const { selected, prices, executeTrade } = useTerminal();
  const [ticker, setTicker] = useState(selected);
  const [qty, setQty] = useState('1');

  // Keep the trade ticker synced with the selected chart, but let the user
  // override it freely afterward.
  useEffect(() => {
    setTicker(selected);
  }, [selected]);

  const live = prices[ticker.toUpperCase()]?.price;
  const quantity = Number(qty);
  const estimate = live != null && quantity > 0 ? live * quantity : null;

  const place = (side: 'buy' | 'sell') => {
    executeTrade(ticker, quantity, side);
  };

  return (
    <section className="panel" aria-label="Trade">
      <div className="flex flex-wrap items-end gap-3 p-3">
        <Field label="Symbol">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            aria-label="Trade ticker"
            className="w-24 rounded border border-term-border bg-term-void/70 px-2 py-1.5 font-mono text-sm uppercase text-term-text focus:border-primary"
          />
        </Field>
        <Field label="Quantity">
          <input
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            inputMode="decimal"
            aria-label="Trade quantity"
            className="tnum w-24 rounded border border-term-border bg-term-void/70 px-2 py-1.5 font-mono text-sm text-term-text focus:border-primary"
          />
        </Field>

        <div className="flex flex-col">
          <span className="eyebrow">Est. Cost</span>
          <span className="tnum py-1.5 font-mono text-sm text-term-dim">
            {estimate != null ? fmtPrice(estimate) : '—'}
          </span>
        </div>

        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={() => place('buy')}
            className="rounded border border-up/50 bg-up/15 px-5 py-1.5 font-mono text-sm font-semibold text-up transition-colors hover:bg-up/25"
          >
            Buy
          </button>
          <button
            type="button"
            onClick={() => place('sell')}
            className="rounded border border-down/50 bg-down/15 px-5 py-1.5 font-mono text-sm font-semibold text-down transition-colors hover:bg-down/25"
          >
            Sell
          </button>
        </div>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col">
      <span className="eyebrow mb-1">{label}</span>
      {children}
    </label>
  );
}
