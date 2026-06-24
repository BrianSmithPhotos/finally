'use client';

import { useState } from 'react';
import { useTerminal } from '@/hooks/useTerminal';
import { WatchlistRow } from './WatchlistRow';

export function Watchlist() {
  const {
    watchlist,
    prices,
    history,
    selected,
    setSelected,
    addTicker,
    removeTicker,
  } = useTerminal();
  const [input, setInput] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    addTicker(input);
    setInput('');
  };

  return (
    <section className="panel flex h-full flex-col" aria-label="Watchlist">
      <div className="panel-head">
        <span className="eyebrow">Watchlist</span>
        <span className="font-mono text-2xs text-term-faint">{watchlist.length} symbols</span>
      </div>

      <form onSubmit={submit} className="flex gap-2 border-b border-term-line px-3 py-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add ticker to watchlist"
          className="min-w-0 flex-1 rounded border border-term-border bg-term-void/70 px-2 py-1 font-mono text-xs uppercase text-term-text placeholder:text-term-faint placeholder:normal-case focus:border-primary"
        />
        <button
          type="submit"
          className="rounded border border-primary/40 bg-primary/15 px-2.5 py-1 font-mono text-xs text-primary transition-colors hover:bg-primary/25"
        >
          + Add
        </button>
      </form>

      <div role="table" className="flex-1 overflow-y-auto">
        {watchlist.length === 0 ? (
          <p className="px-3 py-6 text-center font-mono text-xs text-term-faint">
            Waiting for market feed…
          </p>
        ) : (
          watchlist.map((entry) => {
            const live = prices[entry.ticker];
            return (
              <WatchlistRow
                key={entry.ticker}
                ticker={entry.ticker}
                price={live?.price ?? entry.price}
                changePercent={live?.change_percent ?? entry.change_percent}
                history={history[entry.ticker] ?? []}
                selected={selected === entry.ticker}
                onSelect={setSelected}
                onRemove={removeTicker}
              />
            );
          })
        )}
      </div>
    </section>
  );
}
