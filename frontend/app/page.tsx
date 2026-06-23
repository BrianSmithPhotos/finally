"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addWatchlistTicker,
  executeTrade,
  getPortfolio,
  getPortfolioHistory,
  getWatchlist,
  removeWatchlistTicker,
  sendChatMessage,
} from "@/lib/api";
import { usePriceStream } from "@/lib/usePriceStream";
import type { ChatMessage, Portfolio, PortfolioSnapshot, TradeSide } from "@/lib/types";
import { Header } from "@/components/header/Header";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PriceChart } from "@/components/chart/PriceChart";
import { Heatmap } from "@/components/portfolio/Heatmap";
import { PnlChart } from "@/components/portfolio/PnlChart";
import { PositionsTable } from "@/components/portfolio/PositionsTable";
import { TradeBar } from "@/components/trade/TradeBar";
import { ChatPanel } from "@/components/chat/ChatPanel";

const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

export default function Home() {
  const { prices, history, status } = usePriceStream();

  const [tickers, setTickers] = useState<string[]>(DEFAULT_TICKERS);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const refreshPortfolio = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPortfolio(data);
    } catch {
      // backend unavailable; UI falls back to loading/empty state
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const items = await getWatchlist();
      if (items.length > 0) {
        setTickers(items.map((item) => item.ticker));
      }
    } catch {
      // keep default watchlist if the backend isn't reachable yet
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const data = await getPortfolioHistory();
      setSnapshots(data);
    } catch {
      // no history available yet
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      await Promise.all([refreshPortfolio(), refreshWatchlist(), refreshHistory()]);
    };
    if (!cancelled) load();

    const interval = setInterval(() => {
      if (!cancelled) {
        refreshPortfolio();
        refreshHistory();
      }
    }, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refreshPortfolio, refreshWatchlist, refreshHistory]);

  const effectiveSelectedTicker = selectedTicker ?? tickers[0] ?? null;

  const handleAddTicker = useCallback(async (ticker: string) => {
    setTickers((prev) => (prev.includes(ticker) ? prev : [...prev, ticker]));
    try {
      await addWatchlistTicker(ticker);
    } catch {
      setTickers((prev) => prev.filter((t) => t !== ticker));
    }
  }, []);

  const handleRemoveTicker = useCallback(
    async (ticker: string) => {
      setTickers((prev) => prev.filter((t) => t !== ticker));
      if (selectedTicker === ticker) {
        setSelectedTicker(null);
      }
      try {
        await removeWatchlistTicker(ticker);
      } catch {
        setTickers((prev) => [...prev, ticker]);
      }
    },
    [selectedTicker]
  );

  const handleTrade = useCallback(
    async (ticker: string, quantity: number, side: TradeSide) => {
      await executeTrade({ ticker, quantity, side });
      await refreshPortfolio();
      await refreshHistory();
    },
    [refreshPortfolio, refreshHistory]
  );

  const handleSendChat = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
      };
      setMessages((prev) => [...prev, userMessage]);
      setChatLoading(true);

      try {
        const response = await sendChatMessage(content);
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.message,
          trades: response.trades,
          watchlist_changes: response.watchlist_changes,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        if (response.trades?.length || response.watchlist_changes?.length) {
          await refreshPortfolio();
          await refreshWatchlist();
          await refreshHistory();
        }
      } catch (err) {
        const errorMessage: ChatMessage = {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: err instanceof Error ? `Error: ${err.message}` : "Something went wrong.",
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setChatLoading(false);
      }
    },
    [refreshPortfolio, refreshWatchlist, refreshHistory]
  );

  const totalValue = portfolio?.total_value ?? 0;
  const cashBalance = portfolio?.cash_balance ?? 0;
  const positions = portfolio?.positions ?? [];

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <Header totalValue={totalValue} cashBalance={cashBalance} connectionStatus={status} />

      <main className="flex flex-1 gap-3 overflow-hidden p-3">
        <div className="flex w-80 flex-col gap-3 overflow-y-auto">
          <WatchlistPanel
            tickers={tickers}
            prices={prices}
            history={history}
            selectedTicker={effectiveSelectedTicker}
            onSelect={setSelectedTicker}
            onAdd={handleAddTicker}
            onRemove={handleRemoveTicker}
          />
          <TradeBar defaultTicker={effectiveSelectedTicker ?? undefined} onTrade={handleTrade} />
        </div>

        <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
          <PriceChart
            ticker={effectiveSelectedTicker}
            history={effectiveSelectedTicker ? history[effectiveSelectedTicker] ?? [] : []}
          />
          <div className="grid grid-cols-2 gap-3">
            <Heatmap positions={positions} />
            <PnlChart snapshots={snapshots} />
          </div>
          <PositionsTable positions={positions} />
        </div>

        <ChatPanel messages={messages} isLoading={chatLoading} onSend={handleSendChat} />
      </main>
    </div>
  );
}
