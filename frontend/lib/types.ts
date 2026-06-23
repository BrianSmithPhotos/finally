export type Direction = "up" | "down" | "flat";

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

export type PriceStreamEvent = Record<string, PriceUpdate>;

export interface WatchlistItem {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: Direction;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
  total_unrealized_pnl: number;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export type TradeSide = "buy" | "sell";

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: TradeSide;
}

export interface TradeResult {
  ticker: string;
  side: TradeSide;
  quantity: number;
  price: number;
  executed_at: string;
}

export interface ChatTrade {
  ticker: string;
  side: TradeSide;
  quantity: number;
  price?: number;
  error?: string;
}

export interface ChatWatchlistChange {
  ticker: string;
  action: "add" | "remove";
  error?: string;
}

export interface ChatResponse {
  message: string;
  trades?: ChatTrade[];
  watchlist_changes?: ChatWatchlistChange[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  trades?: ChatTrade[];
  watchlist_changes?: ChatWatchlistChange[];
  pending?: boolean;
}

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";
