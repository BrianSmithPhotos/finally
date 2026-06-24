import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TerminalProvider, useTerminal } from './useTerminal';
import type { Portfolio } from '@/lib/types';

// Mock the SSE hook so the provider mounts without a live EventSource.
vi.mock('./usePriceStream', () => ({
  usePriceStream: () => ({
    prices: { AAPL: { ticker: 'AAPL', price: 200, previous_price: 190, timestamp: 0, change: 10, change_percent: 5.2, direction: 'up' } },
    history: { AAPL: [190, 195, 200] },
    status: 'connected',
  }),
}));

// Mock the API client. These are the NORMALIZED shapes the client returns
// (envelope unwrapping happens inside the real client, which we mock out).
const portfolio: Portfolio = {
  cash_balance: 5000,
  total_value: 11000,
  positions_value: 6000,
  unrealized_pnl: 200,
  positions: [
    { ticker: 'AAPL', quantity: 10, avg_cost: 180, current_price: 200, unrealized_pnl: 200, pnl_percent: 11.1 },
  ],
};

const tradeResult = {
  trade: { id: 't1', ticker: 'AAPL', side: 'buy' as const, quantity: 1, price: 200, executed_at: '2026-06-24T00:00:00Z' },
  portfolio,
};

const mocks = vi.hoisted(() => ({
  getWatchlist: vi.fn(),
  getPortfolio: vi.fn(),
  getPortfolioHistory: vi.fn(),
  addWatchlist: vi.fn(),
  removeWatchlist: vi.fn(),
  trade: vi.fn(),
  chat: vi.fn(),
  health: vi.fn(),
}));

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  return { ...actual, api: mocks };
});

function Harness() {
  const t = useTerminal();
  return (
    <div>
      <span data-testid="cash">{t.portfolio?.cash_balance ?? 'none'}</span>
      <span data-testid="wl-count">{t.watchlist.length}</span>
      <span data-testid="positions">{t.livePositions.length}</span>
      <span data-testid="pnl">{t.livePositions[0]?.unrealized_pnl ?? ''}</span>
      <span data-testid="loading">{t.chatLoading ? 'yes' : 'no'}</span>
      <span data-testid="messages">{t.messages.length}</span>
      <button onClick={() => t.addTicker('TSLA')}>add</button>
      <button onClick={() => t.removeTicker('AAPL')}>remove</button>
      <button onClick={() => t.sendChat('buy aapl')}>chat</button>
    </div>
  );
}

function renderHarness() {
  return render(
    <TerminalProvider>
      <Harness />
    </TerminalProvider>,
  );
}

describe('useTerminal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getWatchlist.mockResolvedValue([{ ticker: 'AAPL' }]);
    mocks.getPortfolio.mockResolvedValue(portfolio);
    mocks.getPortfolioHistory.mockResolvedValue({ snapshots: [] });
    mocks.addWatchlist.mockResolvedValue([{ ticker: 'AAPL' }, { ticker: 'TSLA' }]);
    mocks.removeWatchlist.mockResolvedValue(undefined);
    mocks.trade.mockResolvedValue(tradeResult);
    mocks.chat.mockResolvedValue({
      message: 'Bought it.',
      trades: [{ ticker: 'AAPL', side: 'buy', quantity: 1, price: 200, status: 'executed' }],
    });
  });

  it('loads portfolio and watchlist on mount', async () => {
    renderHarness();
    await waitFor(() => expect(screen.getByTestId('cash')).toHaveTextContent('5000'));
    expect(screen.getByTestId('wl-count')).toHaveTextContent('1');
    expect(screen.getByTestId('positions')).toHaveTextContent('1');
  });

  it('recomputes live P&L from streamed prices', async () => {
    renderHarness();
    // avg_cost 180 * 10 = 1800 cost; live 200 * 10 = 2000 value -> +200 P&L.
    await waitFor(() => expect(screen.getByTestId('pnl')).toHaveTextContent('200'));
  });

  it('adds a ticker to the watchlist', async () => {
    renderHarness();
    await waitFor(() => expect(screen.getByTestId('wl-count')).toHaveTextContent('1'));
    fireEvent.click(screen.getByText('add'));
    await waitFor(() => expect(mocks.addWatchlist).toHaveBeenCalledWith('TSLA'));
    await waitFor(() => expect(screen.getByTestId('wl-count')).toHaveTextContent('2'));
  });

  it('optimistically removes a ticker', async () => {
    renderHarness();
    await waitFor(() => expect(screen.getByTestId('wl-count')).toHaveTextContent('1'));
    fireEvent.click(screen.getByText('remove'));
    await waitFor(() => expect(screen.getByTestId('wl-count')).toHaveTextContent('0'));
    expect(mocks.removeWatchlist).toHaveBeenCalledWith('AAPL');
  });

  it('runs the chat flow and appends user + assistant messages', async () => {
    renderHarness();
    await waitFor(() => expect(screen.getByTestId('cash')).toHaveTextContent('5000'));
    fireEvent.click(screen.getByText('chat'));
    // user message appears immediately
    await waitFor(() => expect(Number(screen.getByTestId('messages').textContent)).toBeGreaterThanOrEqual(1));
    // assistant reply lands -> 2 messages, loading back to no
    await waitFor(() => expect(screen.getByTestId('messages')).toHaveTextContent('2'));
    expect(screen.getByTestId('loading')).toHaveTextContent('no');
    expect(mocks.chat).toHaveBeenCalledWith('buy aapl');
  });
});
