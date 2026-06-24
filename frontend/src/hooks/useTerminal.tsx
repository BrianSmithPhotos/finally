'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { api, ApiError } from '@/lib/api';
import { usePriceStream } from './usePriceStream';
import type {
  ChatMessage,
  Portfolio,
  PortfolioSnapshot,
  Position,
  Side,
  WatchlistEntry,
} from '@/lib/types';

const DEFAULT_TICKERS = [
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
  'NVDA', 'META', 'JPM', 'V', 'NFLX',
];

export interface TerminalState extends ReturnType<typeof useTerminalState> {}

function useTerminalState() {
  const { prices, history, status } = usePriceStream();

  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [selected, setSelected] = useState<string>('AAPL');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [backendUp, setBackendUp] = useState<boolean>(true);

  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showToast = useCallback((msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const wl = await api.getWatchlist();
      setWatchlist(wl);
      setBackendUp(true);
    } catch (err) {
      // Backend not ready — fall back to the documented default seed so the
      // UI is populated and the SSE feed can drive prices.
      if (watchlist.length === 0) {
        setWatchlist(DEFAULT_TICKERS.map((ticker) => ({ ticker })));
      }
      if (err instanceof ApiError && err.status === 0) setBackendUp(false);
    }
  }, [watchlist.length]);

  const refreshPortfolio = useCallback(async () => {
    try {
      const p = await api.getPortfolio();
      setPortfolio(p);
      setBackendUp(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) setBackendUp(false);
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const h = await api.getPortfolioHistory();
      setSnapshots(h.snapshots ?? []);
    } catch {
      /* non-fatal */
    }
  }, []);

  // Initial load + periodic refresh of portfolio/history (prices come via SSE).
  useEffect(() => {
    refreshWatchlist();
    refreshPortfolio();
    refreshHistory();
    const id = setInterval(() => {
      refreshPortfolio();
      refreshHistory();
    }, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addTicker = useCallback(
    async (raw: string) => {
      const ticker = raw.trim().toUpperCase();
      if (!ticker) return;
      try {
        const wl = await api.addWatchlist(ticker);
        setWatchlist(wl);
        setSelected(ticker);
        showToast(`Added ${ticker} to watchlist`);
      } catch (err) {
        showToast(err instanceof Error ? err.message : `Could not add ${ticker}`);
      }
    },
    [showToast],
  );

  const removeTicker = useCallback(
    async (raw: string) => {
      const ticker = raw.trim().toUpperCase();
      // Optimistic removal — restore on failure.
      const prev = watchlist;
      setWatchlist((wl) => wl.filter((e) => e.ticker !== ticker));
      try {
        await api.removeWatchlist(ticker);
        showToast(`Removed ${ticker}`);
      } catch (err) {
        setWatchlist(prev);
        showToast(err instanceof Error ? err.message : `Could not remove ${ticker}`);
      }
    },
    [watchlist, showToast],
  );

  const executeTrade = useCallback(
    async (ticker: string, quantity: number, side: Side) => {
      const sym = ticker.trim().toUpperCase();
      if (!sym || !quantity || quantity <= 0) {
        showToast('Enter a ticker and a positive quantity');
        return;
      }
      try {
        // Trade response nests the updated portfolio under `.portfolio`
        // (alongside the executed `.trade` record).
        const { trade, portfolio: updated } = await api.trade({
          ticker: sym,
          quantity,
          side,
        });
        setPortfolio(updated);
        refreshHistory();
        showToast(
          `${trade.side === 'buy' ? 'Bought' : 'Sold'} ${trade.quantity} ${trade.ticker} @ $${trade.price.toFixed(2)}`,
        );
      } catch (err) {
        showToast(err instanceof Error ? err.message : 'Trade failed');
      }
    },
    [refreshHistory, showToast],
  );

  const sendChat = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || chatLoading) return;
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        content,
      };
      setMessages((m) => [...m, userMsg]);
      setChatLoading(true);
      try {
        const res = await api.chat(content);
        setMessages((m) => [
          ...m,
          {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content: res.message,
            trades: res.trades,
            watchlist_changes: res.watchlist_changes,
          },
        ]);
        // The assistant may have traded or changed the watchlist — resync.
        if (res.trades?.length) {
          refreshPortfolio();
          refreshHistory();
        }
        if (res.watchlist_changes?.length) refreshWatchlist();
      } catch (err) {
        setMessages((m) => [
          ...m,
          {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content:
              err instanceof Error
                ? `Couldn't reach the assistant: ${err.message}`
                : 'The assistant is unavailable right now.',
            error: true,
          },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [chatLoading, refreshPortfolio, refreshHistory, refreshWatchlist],
  );

  // Live total value: prefer SSE prices for instant updates, fall back to the
  // last portfolio snapshot's figures.
  const liveTotalValue = useMemo(() => {
    if (!portfolio) return null;
    const positionsValue = portfolio.positions.reduce((sum, pos) => {
      const live = prices[pos.ticker]?.price ?? pos.current_price;
      return sum + live * pos.quantity;
    }, 0);
    return portfolio.cash_balance + positionsValue;
  }, [portfolio, prices]);

  // Positions enriched with live prices for the table/heatmap.
  const livePositions = useMemo<Position[]>(() => {
    if (!portfolio) return [];
    return portfolio.positions.map((pos) => {
      const live = prices[pos.ticker]?.price ?? pos.current_price;
      const value = live * pos.quantity;
      const cost = pos.avg_cost * pos.quantity;
      const pnl = value - cost;
      const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
      return {
        ...pos,
        current_price: live,
        unrealized_pnl: pnl,
        pnl_percent: pnlPct,
      };
    });
  }, [portfolio, prices]);

  return {
    prices,
    history,
    status,
    watchlist,
    portfolio,
    livePositions,
    liveTotalValue,
    snapshots,
    selected,
    setSelected,
    messages,
    chatLoading,
    toast,
    backendUp,
    addTicker,
    removeTicker,
    executeTrade,
    sendChat,
  };
}

const TerminalContext = createContext<TerminalState | null>(null);

export function TerminalProvider({ children }: { children: ReactNode }) {
  const value = useTerminalState();
  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminal(): TerminalState {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error('useTerminal must be used within <TerminalProvider>');
  return ctx;
}
