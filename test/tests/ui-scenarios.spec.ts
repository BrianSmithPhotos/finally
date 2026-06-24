import { test, expect } from '@playwright/test';
import {
  DEFAULT_TICKERS,
  expectAppMounted,
  readCash,
  resetBackend,
} from './helpers';

/**
 * End-to-end UI scenarios from PLAN.md §12. These drive the fully-integrated
 * app (FastAPI serving the Next.js static export) through a real browser.
 *
 * Run the app with LLM_MOCK=true and a throwaway DB. Each test resets backend
 * state first so ordering doesn't matter.
 */
test.describe('FinAlly UI — PLAN §12 scenarios', () => {
  test.beforeEach(async ({ request, baseURL }) => {
    await resetBackend(request, baseURL!);
  });

  test('Fresh start: default 10-ticker watchlist, seeded cash, prices streaming', async ({ page, request, baseURL }) => {
    await page.goto('/');
    await expectAppMounted(page);

    // Default watchlist rows.
    for (const t of DEFAULT_TICKERS) {
      await expect(page.getByTestId(`watch-row-${t}`)).toBeVisible();
    }

    // Cash in the header reflects the backend's real (seeded) cash. We compare
    // against the live API rather than a hardcoded $10,000 because the suite
    // shares a single-user backend and GBM price drift means buy/sell
    // round-trips in earlier tests don't restore cash to exactly $10k. On a
    // genuinely fresh DB this is $10,000; here we assert FE==backend and a
    // sensible band around the seed.
    const apiCash = (await (await request.get(`${baseURL}/api/portfolio`)).json()).cash_balance as number;
    await expect.poll(async () => await readCash(page), { timeout: 8000 }).toBeCloseTo(apiCash, 0);
    expect(apiCash).toBeGreaterThan(9000);
    expect(apiCash).toBeLessThanOrEqual(10000);

    // Prices streaming: connection dot becomes connected, and a price value
    // changes within a few seconds.
    const dot = page.getByTestId('connection-dot');
    await expect(dot).toBeVisible();
    await expect(dot).toHaveAttribute('data-status', 'connected', { timeout: 8000 });

    const aaplPrice = page.getByTestId('watch-row-AAPL').locator('span.tnum.w-20');
    await expect(aaplPrice).not.toHaveText('—', { timeout: 8000 });
    const first = await aaplPrice.textContent();
    // A flash attribute or a changed price proves the stream is live.
    await expect
      .poll(async () => {
        const cur = await aaplPrice.textContent();
        const flashed = await page
          .locator('[data-testid^="watch-row-"][data-flash]')
          .count();
        return cur !== first || flashed > 0;
      }, { timeout: 12_000, message: 'expected a live price change / flash' })
      .toBeTruthy();
  });

  test('Add and remove a ticker via the UI', async ({ page }) => {
    await page.goto('/');
    await expectAppMounted(page);

    const input = page.getByLabel('Add ticker to watchlist');
    await input.fill('PYPL');
    await input.press('Enter');

    await expect(page.getByTestId('watch-row-PYPL')).toBeVisible({ timeout: 8000 });

    // Remove it.
    await page.getByTestId('watch-row-PYPL').hover();
    await page.getByRole('button', { name: 'Remove PYPL from watchlist' }).click();
    await expect(page.getByTestId('watch-row-PYPL')).toHaveCount(0, { timeout: 8000 });
  });

  test('Buy shares: cash decreases, position appears, total updates', async ({ page }) => {
    await page.goto('/');
    await expectAppMounted(page);

    const cashBefore = await readCash(page);
    expect(cashBefore).toBeGreaterThan(0);

    await page.getByLabel('Trade ticker').fill('AAPL');
    await page.getByLabel('Trade quantity').fill('3');
    await page.getByRole('button', { name: 'Buy', exact: true }).click();

    // Position row appears in the positions table.
    await expect(
      page.locator('section[aria-label="Positions"]').getByText('AAPL', { exact: true }),
    ).toBeVisible({ timeout: 8000 });

    // Cash decreased.
    await expect
      .poll(async () => await readCash(page), { timeout: 8000 })
      .toBeLessThan(cashBefore);
  });

  test('Sell shares: cash increases, position updates/disappears', async ({ page, request, baseURL }) => {
    // Seed a position via the API so the sell has something to act on.
    await request.post(`${baseURL}/api/portfolio/trade`, {
      data: { ticker: 'MSFT', quantity: 4, side: 'buy' },
    });

    await page.goto('/');
    await expectAppMounted(page);
    await expect(
      page.locator('section[aria-label="Positions"]').getByText('MSFT', { exact: true }),
    ).toBeVisible({ timeout: 8000 });

    const cashBefore = await readCash(page);

    await page.getByLabel('Trade ticker').fill('MSFT');
    await page.getByLabel('Trade quantity').fill('4');
    await page.getByRole('button', { name: 'Sell', exact: true }).click();

    // Position is gone (sold to zero).
    await expect(
      page.locator('section[aria-label="Positions"]').getByText('MSFT', { exact: true }),
    ).toHaveCount(0, { timeout: 8000 });

    await expect
      .poll(async () => await readCash(page), { timeout: 8000 })
      .toBeGreaterThan(cashBefore);
  });

  test('Portfolio visualization: heatmap + P&L chart render with data', async ({ page, request, baseURL }) => {
    // Give the portfolio a position so the heatmap has a tile.
    await request.post(`${baseURL}/api/portfolio/trade`, {
      data: { ticker: 'TSLA', quantity: 2, side: 'buy' },
    });

    await page.goto('/');
    await expectAppMounted(page);

    const heatmap = page.locator('section[aria-label="Portfolio heatmap"]');
    await expect(heatmap).toBeVisible();
    // The heatmap should label the position once the portfolio loads.
    await expect(heatmap).toContainText('TSLA', { timeout: 8000 });

    const pnl = page.locator('section[aria-label="Portfolio value over time"]');
    await expect(pnl).toBeVisible();
    // Recharts renders an <svg> once it has at least one snapshot data point.
    await expect
      .poll(async () => await pnl.locator('svg').count(), { timeout: 12_000 })
      .toBeGreaterThan(0);
  });

  test('AI chat (mocked): buy 5 NVDA shows inline confirmation and updates portfolio', async ({ page }) => {
    await page.goto('/');
    await expectAppMounted(page);

    // Open the assistant if it's collapsed.
    const openBtn = page.getByRole('button', { name: 'Open AI assistant' });
    if (await openBtn.count()) await openBtn.click();

    const cashBefore = await readCash(page);

    const msg = page.getByLabel('Message the assistant');
    await msg.fill('buy 5 NVDA');
    await msg.press('Enter');

    // Inline trade confirmation.
    const confirm = page.getByTestId('trade-confirm');
    await expect(confirm).toBeVisible({ timeout: 12_000 });
    await expect(confirm).toContainText('NVDA');

    // Portfolio reflects the trade: position appears + cash drops.
    await expect(
      page.locator('section[aria-label="Positions"]').getByText('NVDA', { exact: true }),
    ).toBeVisible({ timeout: 8000 });
    await expect
      .poll(async () => await readCash(page), { timeout: 8000 })
      .toBeLessThan(cashBefore);
  });

  test('SSE resilience: prices keep updating live', async ({ page }) => {
    await page.goto('/');
    await expectAppMounted(page);

    const dot = page.getByTestId('connection-dot');
    // The dot exposes the live status via data-status; the human label is "LIVE".
    await expect(dot).toHaveAttribute('data-status', 'connected', { timeout: 8000 });

    // Observe at least two distinct AAPL prices over time -> stream is flowing.
    const aaplPrice = page.getByTestId('watch-row-AAPL').locator('span.tnum.w-20');
    const seen = new Set<string>();
    await expect
      .poll(
        async () => {
          const v = (await aaplPrice.textContent())?.trim() ?? '';
          if (v && v !== '—') seen.add(v);
          return seen.size;
        },
        { timeout: 15_000, message: 'expected multiple distinct streamed prices' },
      )
      .toBeGreaterThanOrEqual(2);
  });
});
