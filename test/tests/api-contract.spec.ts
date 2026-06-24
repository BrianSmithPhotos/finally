import { test, expect } from '@playwright/test';

/**
 * Contract tests hit the backend REST/SSE API directly (no browser). They pin
 * down the exact response shapes the frontend is coded against, so the two
 * suspected nesting mismatches are documented unambiguously and machine-checked.
 *
 * NOTE: These tests assert the *backend's actual* shapes (nested), which differ
 * from what the frontend expects (bare). They PASS — their job is to be the
 * authoritative evidence for the bug reports, not to enforce the FE assumption.
 */
test.describe('API contract', () => {
  test('GET /api/health → {status:"ok"}', async ({ request, baseURL }) => {
    const res = await request.get(`${baseURL}/api/health`);
    expect(res.status()).toBe(200);
    expect(await res.json()).toMatchObject({ status: 'ok' });
  });

  test('GET /api/portfolio → bare PortfolioResponse (matches FE)', async ({ request, baseURL }) => {
    const res = await request.get(`${baseURL}/api/portfolio`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('cash_balance');
    expect(body).toHaveProperty('positions');
    expect(Array.isArray(body.positions)).toBeTruthy();
  });

  test('GET /api/watchlist → NESTED {watchlist:[...]} (FE expects bare array)', async ({ request, baseURL }) => {
    const res = await request.get(`${baseURL}/api/watchlist`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    // Documents the mismatch: backend nests under `watchlist`; FE's
    // api.getWatchlist() types it as a bare array and calls .map() on it.
    expect(Array.isArray(body)).toBeFalsy();
    expect(body).toHaveProperty('watchlist');
    expect(Array.isArray(body.watchlist)).toBeTruthy();
  });

  test('POST /api/portfolio/trade → NESTED {trade, portfolio} (FE expects bare Portfolio)', async ({ request, baseURL }) => {
    const res = await request.post(`${baseURL}/api/portfolio/trade`, {
      data: { ticker: 'AAPL', quantity: 1, side: 'buy' },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    // Documents the mismatch: cash_balance/positions live under `.portfolio`,
    // not at the top level where the FE reads them.
    expect(body).toHaveProperty('trade');
    expect(body).toHaveProperty('portfolio');
    expect(body.cash_balance).toBeUndefined();
    expect(body.portfolio).toHaveProperty('cash_balance');
    // cleanup
    await request.post(`${baseURL}/api/portfolio/trade`, {
      data: { ticker: 'AAPL', quantity: 1, side: 'sell' },
    });
  });

  test('POST /api/watchlist → NESTED {watchlist:[...]}', async ({ request, baseURL }) => {
    const res = await request.post(`${baseURL}/api/watchlist`, { data: { ticker: 'PYPL' } });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    expect(Array.isArray(body)).toBeFalsy();
    expect(body).toHaveProperty('watchlist');
    expect(body.watchlist.some((w: any) => w.ticker === 'PYPL')).toBeTruthy();
    await request.delete(`${baseURL}/api/watchlist/PYPL`);
  });

  test('POST /api/chat (LLM_MOCK) buy 5 NVDA → trade executed, status enum is "executed"', async ({ request, baseURL }) => {
    const before = await (await request.get(`${baseURL}/api/portfolio`)).json();
    const res = await request.post(`${baseURL}/api/chat`, { data: { message: 'buy 5 NVDA' } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('message');
    expect(Array.isArray(body.trades)).toBeTruthy();
    expect(body.trades.length).toBe(1);
    expect(body.trades[0].ticker).toBe('NVDA');
    expect(body.trades[0].quantity).toBe(5);
    // Backend emits status:"executed" (FE TradeConfirm checks for "rejected" /
    // "filled"; it still renders ✓ because it falls back to !error). Documented.
    expect(body.trades[0].status).toBe('executed');
    const after = await (await request.get(`${baseURL}/api/portfolio`)).json();
    expect(after.cash_balance).toBeLessThan(before.cash_balance);
    // cleanup
    await request.post(`${baseURL}/api/portfolio/trade`, { data: { ticker: 'NVDA', quantity: 5, side: 'sell' } });
  });

  test('POST /api/chat insufficient funds → inline error, not 500', async ({ request, baseURL }) => {
    const res = await request.post(`${baseURL}/api/chat`, { data: { message: 'buy 100000 AAPL' } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.trades[0].status).toBe('error');
    expect(body.trades[0].error).toBeTruthy();
  });

  test('GET /api/stream/prices → SSE map keyed by ticker (read in-browser)', async ({ page, baseURL }) => {
    // EventSource is long-lived; drive it from a real browser context and
    // resolve after the first parseable frame. This also exercises the exact
    // client API the frontend uses.
    await page.goto(`${baseURL}/`);
    const sample = await page.evaluate(() => {
      return new Promise<any>((resolve, reject) => {
        const es = new EventSource('/api/stream/prices');
        const timer = setTimeout(() => { es.close(); reject(new Error('no SSE frame in 8s')); }, 8000);
        es.onmessage = (e) => {
          try {
            const data = JSON.parse((e as MessageEvent).data);
            clearTimeout(timer);
            es.close();
            const first = Object.values(data)[0];
            resolve({ isArray: Array.isArray(data), first });
          } catch { /* keep waiting */ }
        };
        es.onerror = () => {};
      });
    });
    expect(sample.isArray).toBeFalsy();
    expect(sample.first).toHaveProperty('ticker');
    expect(sample.first).toHaveProperty('price');
    expect(sample.first).toHaveProperty('direction');
  });
});
