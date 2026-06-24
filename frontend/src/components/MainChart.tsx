'use client';

import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from 'recharts';
import { useTerminal } from '@/hooks/useTerminal';
import { fmtPrice, fmtPercent, directionClass } from '@/lib/format';

export function MainChart() {
  const { selected, prices, history } = useTerminal();
  const series = useMemo(() => history[selected] ?? [], [history, selected]);
  const live = prices[selected];

  const data = useMemo(() => series.map((price, i) => ({ i, price })), [series]);

  const first = series[0];
  const last = series[series.length - 1];
  const sessionPct =
    first != null && last != null && first !== 0 ? ((last - first) / first) * 100 : null;
  const up = sessionPct == null ? true : sessionPct >= 0;
  const stroke = up ? '#26d07c' : '#f0506e';

  const min = series.length ? Math.min(...series) : 0;
  const max = series.length ? Math.max(...series) : 1;
  const pad = (max - min || 1) * 0.08;

  return (
    <section className="panel flex h-full flex-col" aria-label="Price chart">
      <div className="panel-head">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-base font-bold text-term-text">{selected}</span>
          <span className={`tnum font-mono text-sm ${directionClass(live?.change_percent)}`}>
            {fmtPrice(live?.price)}
          </span>
          <span className={`tnum font-mono text-xs ${directionClass(sessionPct)}`}>
            {sessionPct != null ? `${fmtPercent(sessionPct)} since open` : ''}
          </span>
        </div>
        <span className="eyebrow">Session · live</span>
      </div>

      <div className="min-h-0 flex-1 px-1 py-2">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center font-mono text-xs text-term-faint">
            Accumulating ticks for {selected}…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id="mainfill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.32} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis
                domain={[min - pad, max + pad]}
                width={56}
                tick={{ fill: '#5a6675', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(v: number) => v.toFixed(2)}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: '#0a0e14',
                  border: '1px solid #2a3340',
                  borderRadius: 6,
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                }}
                labelFormatter={() => ''}
                formatter={(v: number) => [fmtPrice(v), 'Price']}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke={stroke}
                strokeWidth={1.6}
                fill="url(#mainfill)"
                isAnimationActive={false}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
