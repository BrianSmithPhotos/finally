import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { WatchlistRow, type WatchlistRowProps } from './WatchlistRow';

function setup(overrides: Partial<WatchlistRowProps> = {}) {
  const props: WatchlistRowProps = {
    ticker: 'AAPL',
    price: 190,
    changePercent: 1.2,
    history: [188, 189, 190],
    selected: false,
    onSelect: vi.fn(),
    onRemove: vi.fn(),
    ...overrides,
  };
  const utils = render(<WatchlistRow {...props} />);
  return { props, ...utils };
}

describe('WatchlistRow', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('renders ticker, price and change', () => {
    setup();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('$190.00')).toBeInTheDocument();
    expect(screen.getByText('+1.20%')).toBeInTheDocument();
  });

  it('applies flash-up class when price rises, then clears it', () => {
    const { rerender, props } = setup({ price: 190 });
    const row = screen.getByTestId('watch-row-AAPL');
    expect(row.className).not.toContain('flash-up');

    rerender(<WatchlistRow {...props} price={191} />);
    expect(screen.getByTestId('watch-row-AAPL').getAttribute('data-flash')).toBe('flash-up');

    act(() => {
      vi.advanceTimersByTime(600);
    });
    expect(screen.getByTestId('watch-row-AAPL').getAttribute('data-flash')).toBeNull();
  });

  it('applies flash-down class when price falls', () => {
    const { rerender, props } = setup({ price: 190 });
    rerender(<WatchlistRow {...props} price={189} />);
    expect(screen.getByTestId('watch-row-AAPL').getAttribute('data-flash')).toBe('flash-down');
  });

  it('does not flash when price is unchanged', () => {
    const { rerender, props } = setup({ price: 190 });
    rerender(<WatchlistRow {...props} changePercent={2} />);
    expect(screen.getByTestId('watch-row-AAPL').getAttribute('data-flash')).toBeNull();
  });

  it('selects on click and removes via the remove button', () => {
    const { props } = setup();
    fireEvent.click(screen.getByTestId('watch-row-AAPL'));
    expect(props.onSelect).toHaveBeenCalledWith('AAPL');

    fireEvent.click(screen.getByLabelText('Remove AAPL from watchlist'));
    expect(props.onRemove).toHaveBeenCalledWith('AAPL');
  });
});
