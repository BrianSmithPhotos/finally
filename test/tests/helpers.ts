import { Page, expect, APIRequestContext } from '@playwright/test';

export const DEFAULT_TICKERS = [
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA',
  'NVDA', 'META', 'JPM', 'V', 'NFLX',
];

/**
 * True if the SPA rendered its real shell rather than Next.js's client-side
 * error screen. Used to fail fast (with a clear message) when an unhandled
 * exception tears down the React tree.
 */
export async function appMounted(page: Page): Promise<boolean> {
  const errBanner = page.getByRole('heading', {
    name: /Application error: a client-side exception/i,
  });
  if (await errBanner.count()) return false;
  // The header brand is always present when the shell mounts.
  return (await page.getByText('FinAlly', { exact: false }).count()) > 0
    ? true
    // brand is split across spans ("Fin" + "Ally"); fall back to the Watchlist panel.
    : (await page.locator('section[aria-label="Watchlist"]').count()) > 0;
}

/** Assert the SPA shell is present; throws with a helpful message if it crashed. */
export async function expectAppMounted(page: Page) {
  const ok = await appMounted(page);
  expect(
    ok,
    'SPA failed to mount — Next.js client-side exception screen is showing. ' +
      'See INTEGRATION_REPORT.md: watchlist nested-shape mismatch crashes the app on load.',
  ).toBeTruthy();
}

/** Parse a "$1,234.56" style money string to a number. */
export function parseMoney(text: string | null): number {
  if (!text) return NaN;
  return Number(text.replace(/[^0-9.\-]/g, ''));
}

/** Read the header Cash stat value as a number. */
export async function readCash(page: Page): Promise<number> {
  const cash = page.locator('span:has-text("Cash")').locator('xpath=following-sibling::span[1]');
  return parseMoney(await cash.first().textContent());
}

/** Reset the backend to a clean seeded state via the API (sell all, restore watchlist). */
export async function resetBackend(request: APIRequestContext, baseURL: string) {
  // Liquidate every position so cash returns toward the seed.
  const pf = await (await request.get(`${baseURL}/api/portfolio`)).json();
  for (const pos of pf.positions ?? []) {
    if (pos.quantity > 0) {
      await request.post(`${baseURL}/api/portfolio/trade`, {
        data: { ticker: pos.ticker, quantity: pos.quantity, side: 'sell' },
      });
    }
  }
  // Restore the default watchlist (add any missing defaults, remove extras).
  const wlRes = await (await request.get(`${baseURL}/api/watchlist`)).json();
  const current: string[] = (wlRes.watchlist ?? wlRes).map((w: any) => w.ticker);
  for (const t of DEFAULT_TICKERS) {
    if (!current.includes(t)) {
      await request.post(`${baseURL}/api/watchlist`, { data: { ticker: t } });
    }
  }
  for (const t of current) {
    if (!DEFAULT_TICKERS.includes(t)) {
      await request.delete(`${baseURL}/api/watchlist/${t}`);
    }
  }
}
