'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ConnectionStatus, PriceMap, PriceUpdate } from '@/lib/types';

const STREAM_URL = '/api/stream/prices';
/** Max sparkline points retained per ticker (keeps memory bounded). */
const MAX_HISTORY = 240;

export interface PriceStreamState {
  /** Latest price per ticker, updated on every SSE event. */
  prices: PriceMap;
  /** Per-ticker price history accumulated since page load (for sparklines). */
  history: Record<string, number[]>;
  status: ConnectionStatus;
}

/**
 * Subscribes to the `/api/stream/prices` SSE feed.
 *
 * Wire contract (backend `stream.py`): each `message` event's data is a JSON
 * MAP of ticker -> PriceUpdate, e.g. `{"AAPL": {...}, "GOOGL": {...}}`.
 *
 * Responsibilities:
 *  - Maintain the latest price map.
 *  - Accumulate a bounded per-ticker price history for progressive sparklines.
 *  - Track connection status for the header indicator. EventSource reconnects
 *    automatically; we mirror that into 'reconnecting' / 'disconnected' states.
 */
export function usePriceStream(): PriceStreamState {
  const [prices, setPrices] = useState<PriceMap>({});
  const [history, setHistory] = useState<Record<string, number[]>>({});
  const [status, setStatus] = useState<ConnectionStatus>('connecting');

  // Refs avoid stale closures inside the long-lived EventSource handlers.
  const historyRef = useRef<Record<string, number[]>>({});
  const everConnected = useRef(false);

  const ingest = useCallback((map: PriceMap) => {
    setPrices((prev) => ({ ...prev, ...map }));

    const next = { ...historyRef.current };
    for (const [ticker, update] of Object.entries(map)) {
      const series = next[ticker] ? next[ticker].slice() : [];
      series.push(update.price);
      if (series.length > MAX_HISTORY) series.splice(0, series.length - MAX_HISTORY);
      next[ticker] = series;
    }
    historyRef.current = next;
    setHistory(next);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') {
      setStatus('disconnected');
      return;
    }

    let es: EventSource | null = null;
    let closed = false;

    const connect = () => {
      es = new EventSource(STREAM_URL);

      es.onopen = () => {
        everConnected.current = true;
        setStatus('connected');
      };

      es.onmessage = (evt: MessageEvent<string>) => {
        try {
          const data = JSON.parse(evt.data) as PriceMap | PriceUpdate;
          // Tolerate either the map shape (contract) or a single-ticker object.
          if (data && typeof data === 'object' && 'ticker' in data && 'price' in data) {
            const single = data as PriceUpdate;
            ingest({ [single.ticker]: single });
          } else {
            ingest(data as PriceMap);
          }
        } catch {
          /* ignore malformed frame; next event will recover */
        }
      };

      es.onerror = () => {
        // EventSource auto-reconnects while readyState === CONNECTING.
        if (closed) return;
        if (es && es.readyState === EventSource.CLOSED) {
          setStatus('disconnected');
        } else {
          setStatus(everConnected.current ? 'reconnecting' : 'connecting');
        }
      };
    };

    connect();

    return () => {
      closed = true;
      es?.close();
    };
  }, [ingest]);

  return { prices, history, status };
}
