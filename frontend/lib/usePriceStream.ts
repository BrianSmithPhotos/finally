"use client";

import { useEffect, useState } from "react";
import type { ConnectionStatus, PriceStreamEvent, PriceUpdate } from "./types";

const DISCONNECTED_AFTER_MS = 8000;

export interface PriceHistoryPoint {
  timestamp: number;
  price: number;
}

export interface PriceStreamState {
  prices: Record<string, PriceUpdate>;
  history: Record<string, PriceHistoryPoint[]>;
  status: ConnectionStatus;
}

const MAX_HISTORY_POINTS = 300;

export function usePriceStream(url = "/api/stream/prices"): PriceStreamState {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const [history, setHistory] = useState<Record<string, PriceHistoryPoint[]>>({});

  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }

    let reconnectingTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const source = new EventSource(url);

    const clearTimers = () => {
      if (reconnectingTimer) clearTimeout(reconnectingTimer);
      reconnectingTimer = null;
    };

    source.onopen = () => {
      clearTimers();
      setStatus("connected");
    };

    source.onmessage = (event: MessageEvent) => {
      clearTimers();
      setStatus("connected");

      try {
        const data: PriceStreamEvent = JSON.parse(event.data);
        setPrices((prev) => ({ ...prev, ...data }));

        setHistory((prev) => {
          const next = { ...prev };
          for (const [ticker, update] of Object.entries(data)) {
            const existing = next[ticker] ?? [];
            const updated = [...existing, { timestamp: update.timestamp, price: update.price }];
            next[ticker] =
              updated.length > MAX_HISTORY_POINTS
                ? updated.slice(updated.length - MAX_HISTORY_POINTS)
                : updated;
          }
          return next;
        });
      } catch {
        // ignore malformed payloads
      }
    };

    source.onerror = () => {
      if (closed) return;
      setStatus("reconnecting");

      reconnectingTimer = setTimeout(() => {
        setStatus("disconnected");
      }, DISCONNECTED_AFTER_MS);
    };

    return () => {
      closed = true;
      clearTimers();
      source.close();
    };
  }, [url]);

  return { prices, history, status };
}
