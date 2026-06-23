import type {
  ChatResponse,
  Portfolio,
  PortfolioSnapshot,
  TradeRequest,
  TradeResult,
  WatchlistItem,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export function getPortfolio(): Promise<Portfolio> {
  return request<Portfolio>("/api/portfolio");
}

export function executeTrade(trade: TradeRequest): Promise<TradeResult> {
  return request<TradeResult>("/api/portfolio/trade", {
    method: "POST",
    body: JSON.stringify(trade),
  });
}

export function getPortfolioHistory(): Promise<PortfolioSnapshot[]> {
  return request<PortfolioSnapshot[]>("/api/portfolio/history");
}

export function getWatchlist(): Promise<WatchlistItem[]> {
  return request<WatchlistItem[]>("/api/watchlist");
}

export function addWatchlistTicker(ticker: string): Promise<WatchlistItem> {
  return request<WatchlistItem>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export function removeWatchlistTicker(ticker: string): Promise<void> {
  return request<void>(`/api/watchlist/${encodeURIComponent(ticker)}`, {
    method: "DELETE",
  });
}

export function sendChatMessage(message: string): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/health");
}
