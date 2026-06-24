'use client';

import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
  YAxis,
} from 'recharts';
import { useTerminal } from '@/hooks/useTerminal';
import { fmtMoney } from '@/lib/format';

const STARTING = 10000;

export function PnlChart() {
  const { snapshots, liveTotalValue } = useTerminal();

  const data = useMemo(() => {
    const points = snapshots.map((s, i) => ({ i, value: s.total_value }));
    // Append the live total as the trailing point for an always-fresh tail.
    if (liveTotalValue != null) {
      points.push({ i: points.length, value: liveTotalValue });
    }
    return points;
  }, [snapshots, liveTotalValue]);

  const last = data.length ? data[data.length - 1].value : STARTING;
  const up = last >= STARTING;
  const stroke = up ? '#26d07c' : '#f0506e';

  return (
    <section className="panel flex h-full flex-col" aria-label="Portfolio value over time">
      <div className="panel-head">
        <span className="eyebrow">Portfolio Value</span>
        <span className="font-mono text-2xs text-term-faint">vs. ${STARTING.toLocaleString()} start</span>
      </div>
      <div className="min-h-0 flex-1 px-1 py-2">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center font-mono text-xs text-term-faint">
            Recording portfolio snapshots…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id="pnlfill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis
                domain={['auto', 'auto']}
                width={56}
                tick={{ fill: '#5a6675', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
                axisLine={false}
                tickLine={false}
              />
              <ReferenceLine y={STARTING} stroke="#ecad0a" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Tooltip
                contentStyle={{
                  background: '#0a0e14',
                  border: '1px solid #2a3340',
                  borderRadius: 6,
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                }}
                labelFormatter={() => ''}
                formatter={(v: number) => [fmtMoney(v), 'Value']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={stroke}
                strokeWidth={1.6}
                fill="url(#pnlfill)"
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
