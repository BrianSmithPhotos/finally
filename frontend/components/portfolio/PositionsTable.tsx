"use client";

import type { Position } from "@/lib/types";
import { formatCurrency, formatPercent, formatQuantity, formatSignedCurrency } from "@/lib/format";

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  return (
    <section
      className="flex flex-col rounded border border-border-muted bg-background-panel"
      data-testid="positions-table"
    >
      <div className="border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Positions</h2>
      </div>

      {positions.length === 0 ? (
        <div className="p-4 text-sm text-gray-500">No open positions</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-3 py-2">Ticker</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2 text-right">Avg Cost</th>
              <th className="px-3 py-2 text-right">Price</th>
              <th className="px-3 py-2 text-right">P&amp;L</th>
              <th className="px-3 py-2 text-right">% Chg</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const pnlColor = position.unrealized_pnl >= 0 ? "text-up" : "text-down";
              return (
                <tr
                  key={position.ticker}
                  className="border-b border-border-muted/60"
                  data-testid={`position-row-${position.ticker}`}
                >
                  <td className="px-3 py-2 font-mono font-semibold">{position.ticker}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatQuantity(position.quantity)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrency(position.avg_cost)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrency(position.current_price)}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${pnlColor}`}>
                    {formatSignedCurrency(position.unrealized_pnl)}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${pnlColor}`}>
                    {formatPercent(position.unrealized_pnl_percent)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
