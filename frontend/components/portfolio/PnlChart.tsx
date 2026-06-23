"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PortfolioSnapshot } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface PnlChartProps {
  snapshots: PortfolioSnapshot[];
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export function PnlChart({ snapshots }: PnlChartProps) {
  return (
    <section
      className="flex flex-col rounded border border-border-muted bg-background-panel p-3"
      data-testid="pnl-chart"
    >
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Portfolio Value
      </h2>

      <div className="h-48">
        {snapshots.length >= 2 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={snapshots}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
              <XAxis
                dataKey="recorded_at"
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
                labelFormatter={(value) => formatTime(value as string)}
                formatter={(value) => formatCurrency(value as number)}
              />
              <Line
                type="monotone"
                dataKey="total_value"
                stroke="var(--accent-yellow)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            Not enough history yet
          </div>
        )}
      </div>
    </section>
  );
}
