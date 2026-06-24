'use client';

import { useEffect, useRef, useState } from 'react';
import { useTerminal } from '@/hooks/useTerminal';
import { fmtQty } from '@/lib/format';
import type { ChatMessage, ExecutedTrade, WatchlistChange } from '@/lib/types';

const SUGGESTIONS = [
  'Analyze my portfolio risk',
  'Buy 5 shares of NVDA',
  'Add PYPL to my watchlist',
];

export function ChatPanel({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const { messages, chatLoading, sendChat } = useTerminal();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, chatLoading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendChat(input);
    setInput('');
  };

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-label="Open AI assistant"
        className="flex h-full w-11 flex-col items-center justify-center gap-3 rounded-md border border-term-border bg-term-panel/70 text-accent"
      >
        <span className="font-mono text-sm">AI</span>
        <span className="font-mono text-2xs uppercase [writing-mode:vertical-rl] tracking-[0.3em] text-term-dim">
          Copilot
        </span>
      </button>
    );
  }

  return (
    <section className="panel flex h-full flex-col" aria-label="AI assistant">
      <div className="panel-head">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent shadow-glow-amber" />
          <span className="eyebrow">FinAlly Copilot</span>
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse assistant"
          className="font-mono text-xs text-term-faint hover:text-term-text"
        >
          ⟩
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="font-mono text-xs leading-relaxed text-term-dim">
              I&apos;m your trading copilot. Ask me to analyze your portfolio, place
              trades, or manage your watchlist — I act on it directly.
            </p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => sendChat(s)}
                  className="rounded border border-term-border bg-term-void/40 px-2.5 py-1.5 text-left font-mono text-2xs text-term-dim transition-colors hover:border-primary/50 hover:text-term-text"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {chatLoading && (
          <div className="flex items-center gap-2 font-mono text-2xs text-term-faint" data-testid="chat-loading">
            <span className="flex gap-1">
              <Dot delay={0} />
              <Dot delay={150} />
              <Dot delay={300} />
            </span>
            analyzing…
          </div>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-term-line p-2">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask or instruct…"
            aria-label="Message the assistant"
            disabled={chatLoading}
            className="min-w-0 flex-1 rounded border border-term-border bg-term-void/70 px-2.5 py-2 font-mono text-xs text-term-text placeholder:text-term-faint focus:border-primary disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={chatLoading || !input.trim()}
            className="rounded bg-secondary px-3 py-2 font-mono text-xs font-semibold text-white transition-colors hover:bg-secondary-bright disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[92%] rounded-md px-3 py-2 font-mono text-xs leading-relaxed ${
          isUser
            ? 'bg-primary/15 text-term-text'
            : message.error
              ? 'border border-down/40 bg-down/10 text-down'
              : 'bg-term-raised/70 text-term-text'
        }`}
      >
        {message.content}
      </div>

      {!!message.trades?.length && (
        <div className="mt-1.5 flex flex-col gap-1">
          {message.trades.map((t, i) => (
            <TradeConfirm key={i} trade={t} />
          ))}
        </div>
      )}
      {!!message.watchlist_changes?.length && (
        <div className="mt-1.5 flex flex-col gap-1">
          {message.watchlist_changes.map((w, i) => (
            <WatchConfirm key={i} change={w} />
          ))}
        </div>
      )}
    </div>
  );
}

function TradeConfirm({ trade }: { trade: ExecutedTrade }) {
  // Backend status enum (TradeResult): "executed" | "error".
  const failed = trade.status === 'error' || !!trade.error;
  return (
    <div
      data-testid="trade-confirm"
      className={`flex items-center gap-2 rounded border px-2 py-1 font-mono text-2xs ${
        failed
          ? 'border-down/40 bg-down/10 text-down'
          : trade.side === 'buy'
            ? 'border-up/40 bg-up/10 text-up'
            : 'border-down/40 bg-down/10 text-down'
      }`}
    >
      <span className="uppercase">{failed ? '✕' : '✓'} {trade.side}</span>
      <span className="text-term-text">
        {fmtQty(trade.quantity)} {trade.ticker}
        {trade.price != null ? ` @ $${trade.price.toFixed(2)}` : ''}
      </span>
      {failed && trade.error && <span className="text-down">— {trade.error}</span>}
    </div>
  );
}

function WatchConfirm({ change }: { change: WatchlistChange }) {
  // Backend status enum (WatchlistResult): "added" | "removed" | "noop" | "error".
  const failed = change.status === 'error' || !!change.error;
  return (
    <div
      data-testid="watch-confirm"
      className={`flex items-center gap-2 rounded border px-2 py-1 font-mono text-2xs ${
        failed ? 'border-down/40 bg-down/10 text-down' : 'border-primary/40 bg-primary/10 text-primary'
      }`}
    >
      <span className="uppercase">
        {failed ? '✕' : '✓'} watchlist {change.action}
      </span>
      <span className="text-term-text">{change.ticker}</span>
      {failed && change.error && <span className="text-down">— {change.error}</span>}
    </div>
  );
}
