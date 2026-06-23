"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import type { Position } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/format";

interface HeatmapProps {
  positions: Position[];
}

interface TreemapNode {
  name: string;
  size: number;
  pnlPercent: number;
  pnl: number;
  [key: string]: string | number;
}

function pnlColor(pnlPercent: number): string {
  if (pnlPercent > 0) {
    const intensity = Math.min(1, pnlPercent / 10);
    return `rgba(47, 191, 113, ${0.3 + intensity * 0.6})`;
  }
  if (pnlPercent < 0) {
    const intensity = Math.min(1, Math.abs(pnlPercent) / 10);
    return `rgba(240, 68, 68, ${0.3 + intensity * 0.6})`;
  }
  return "rgba(110, 118, 129, 0.4)";
}

function CustomCell(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
  pnl?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, pnlPercent = 0, pnl = 0 } = props;
  if (width < 1 || height < 1) return null;

  const showLabel = width > 50 && height > 30;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={pnlColor(pnlPercent)}
        stroke="#0d1117"
        strokeWidth={2}
      />
      {showLabel && (
        <>
          <text x={x + 6} y={y + 18} fontSize={13} fontWeight={600} fill="#e6edf3">
            {name}
          </text>
          <text x={x + 6} y={y + 34} fontSize={11} fill="#e6edf3">
            {formatSignedPercent(pnlPercent)}
          </text>
          {height > 50 && (
            <text x={x + 6} y={y + 50} fontSize={10} fill="#9ca3af">
              {formatCurrency(pnl)}
            </text>
          )}
        </>
      )}
    </g>
  );
}

function formatSignedPercent(value: number): string {
  return formatPercent(value);
}

export function Heatmap({ positions }: HeatmapProps) {
  const data: TreemapNode[] = positions
    .filter((p) => p.quantity > 0)
    .map((p) => ({
      name: p.ticker,
      size: Math.max(p.quantity * p.current_price, 0.01),
      pnlPercent: p.unrealized_pnl_percent,
      pnl: p.unrealized_pnl,
    }));

  return (
    <section
      className="flex flex-col rounded border border-border-muted bg-background-panel p-3"
      data-testid="heatmap"
    >
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Portfolio Heatmap
      </h2>

      <div className="h-56">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              stroke="#0d1117"
              isAnimationActive={false}
              content={<CustomCell />}
            />
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            No open positions
          </div>
        )}
      </div>
    </section>
  );
}
