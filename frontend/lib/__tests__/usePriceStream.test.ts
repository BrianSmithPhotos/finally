import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { usePriceStream } from "../usePriceStream";

class MockEventSource {
  static instances: MockEventSource[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  emitOpen() {
    this.onopen?.();
  }

  emitError() {
    this.onerror?.();
  }
}

describe("usePriceStream", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("starts in the reconnecting status before any events arrive", () => {
    const { result } = renderHook(() => usePriceStream());
    expect(result.current.status).toBe("reconnecting");
  });

  it("transitions to connected on open and merges incoming price updates", async () => {
    const { result } = renderHook(() => usePriceStream());
    const source = MockEventSource.instances[0];

    act(() => {
      source.emitOpen();
    });
    expect(result.current.status).toBe("connected");

    act(() => {
      source.emitMessage({
        AAPL: {
          ticker: "AAPL",
          price: 190.5,
          previous_price: 189.5,
          timestamp: 1000,
          change: 1,
          change_percent: 0.53,
          direction: "up",
        },
      });
    });

    expect(result.current.prices.AAPL?.price).toBe(190.5);
    expect(result.current.history.AAPL).toEqual([{ timestamp: 1000, price: 190.5 }]);
  });

  it("accumulates history across multiple messages", async () => {
    const { result } = renderHook(() => usePriceStream());
    const source = MockEventSource.instances[0];

    const update = (price: number, timestamp: number) => ({
      AAPL: {
        ticker: "AAPL",
        price,
        previous_price: price - 1,
        timestamp,
        change: 1,
        change_percent: 0.5,
        direction: "up",
      },
    });

    act(() => {
      source.emitMessage(update(100, 1));
      source.emitMessage(update(101, 2));
      source.emitMessage(update(102, 3));
    });

    expect(result.current.history.AAPL).toHaveLength(3);
    expect(result.current.history.AAPL.map((p) => p.price)).toEqual([100, 101, 102]);
  });

  it("moves to disconnected after sustained errors without recovery", () => {
    const { result } = renderHook(() => usePriceStream());
    const source = MockEventSource.instances[0];

    act(() => {
      source.emitError();
    });
    expect(result.current.status).toBe("reconnecting");

    act(() => {
      vi.advanceTimersByTime(8001);
    });
    expect(result.current.status).toBe("disconnected");
  });

  it("recovers to connected status if a message arrives after an error", () => {
    const { result } = renderHook(() => usePriceStream());
    const source = MockEventSource.instances[0];

    act(() => {
      source.emitError();
    });
    expect(result.current.status).toBe("reconnecting");

    act(() => {
      source.emitMessage({
        AAPL: {
          ticker: "AAPL",
          price: 100,
          previous_price: 99,
          timestamp: 1,
          change: 1,
          change_percent: 1,
          direction: "up",
        },
      });
    });
    expect(result.current.status).toBe("connected");
  });
});
