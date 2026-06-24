import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from './ChatPanel';
import type { ChatMessage } from '@/lib/types';

describe('MessageBubble', () => {
  it('renders a user message', () => {
    const m: ChatMessage = { id: '1', role: 'user', content: 'Buy 5 NVDA' };
    render(<MessageBubble message={m} />);
    expect(screen.getByText('Buy 5 NVDA')).toBeInTheDocument();
  });

  it('renders an assistant message with inline trade confirmations', () => {
    const m: ChatMessage = {
      id: '2',
      role: 'assistant',
      content: 'Done — bought NVDA.',
      trades: [{ ticker: 'NVDA', side: 'buy', quantity: 5, price: 120.5, status: 'executed' }],
    };
    render(<MessageBubble message={m} />);
    expect(screen.getByText('Done — bought NVDA.')).toBeInTheDocument();
    const confirm = screen.getByTestId('trade-confirm');
    expect(confirm).toHaveTextContent('buy');
    expect(confirm).toHaveTextContent('5 NVDA');
    expect(confirm).toHaveTextContent('@ $120.50');
  });

  it('shows an errored trade with its message', () => {
    const m: ChatMessage = {
      id: '3',
      role: 'assistant',
      content: 'Could not place that trade.',
      trades: [
        { ticker: 'AAPL', side: 'buy', quantity: 1000, status: 'error', error: 'Insufficient cash' },
      ],
    };
    render(<MessageBubble message={m} />);
    const confirm = screen.getByTestId('trade-confirm');
    expect(confirm).toHaveTextContent('Insufficient cash');
    expect(confirm).toHaveTextContent('✕');
  });

  it('renders watchlist-change confirmations', () => {
    const m: ChatMessage = {
      id: '4',
      role: 'assistant',
      content: 'Added PYPL.',
      watchlist_changes: [{ ticker: 'PYPL', action: 'add', status: 'added' }],
    };
    render(<MessageBubble message={m} />);
    const confirm = screen.getByTestId('watch-confirm');
    expect(confirm).toHaveTextContent('watchlist add');
    expect(confirm).toHaveTextContent('PYPL');
  });

  it('marks an errored watchlist change', () => {
    const m: ChatMessage = {
      id: '5',
      role: 'assistant',
      content: 'That ticker is invalid.',
      watchlist_changes: [{ ticker: 'ZZZZ', action: 'add', status: 'error', error: 'Unknown symbol' }],
    };
    render(<MessageBubble message={m} />);
    const confirm = screen.getByTestId('watch-confirm');
    expect(confirm).toHaveTextContent('✕');
    expect(confirm).toHaveTextContent('Unknown symbol');
  });
});
