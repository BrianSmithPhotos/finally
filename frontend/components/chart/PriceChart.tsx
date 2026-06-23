"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PriceHistoryPoint } from "@/lib/usePriceStream";
import { formatCurrency } from "@/lib/format";

interface PriceChartProps {
  ticker: string | null;
  history: PriceHistoryPoint[];
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function PriceChart({ ticker, history }: PriceChartProps) {
  return (
    <section
      className="flex flex-col rounded border border-border-muted bg-background-panel p-3"
      data-testid="price-chart"
    >
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        {ticker ? `${ticker} — Price` : "Select a ticker"}
      </h2>

      <div className="h-64">
        {ticker && history.length >= 2 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTime}
                stroke="#6e7681"
                fontSize={11}
                minTickGap={40}
              />
              <YAxis
                domain={["auto", "auto"]}
                stroke="#6e7681"
                fontSize={11}
                tickFormatter={(value) => formatCurrency(value, { decimals: 0 })}
                width={70}
              />
              <Tooltip
                contentStyle={{ background: "#161b22", border: "1px solid #30363d" }}
                labelFormatter={(value) => formatTime(value as number)}
                formatter={(value) => formatCurrency(value as number)}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="var(--accent-blue)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            {ticker ? "Waiting for price data..." : "Click a ticker in the watchlist"}
          </div>
        )}
      </div>
    </section>
  );
}
