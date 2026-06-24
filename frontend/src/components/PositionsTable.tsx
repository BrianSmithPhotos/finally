'use client';

import { useTerminal } from '@/hooks/useTerminal';
import {
  fmtPrice,
  fmtQty,
  fmtSignedMoney,
  fmtPercent,
  directionClass,
} from '@/lib/format';

export function PositionsTable() {
  const { livePositions, setSelected, selected } = useTerminal();

  return (
    <section className="panel flex h-full flex-col" aria-label="Positions">
      <div className="panel-head">
        <span className="eyebrow">Positions</span>
        <span className="font-mono text-2xs text-term-faint">{livePositions.length} open</span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse font-mono text-xs">
          <thead className="sticky top-0 bg-term-panel">
            <tr className="text-left text-2xs uppercase tracking-wider text-term-faint">
              <th className="px-3 py-1.5 font-normal">Sym</th>
              <th className="px-2 py-1.5 text-right font-normal">Qty</th>
              <th className="px-2 py-1.5 text-right font-normal">Avg</th>
              <th className="px-2 py-1.5 text-right font-normal">Last</th>
              <th className="px-2 py-1.5 text-right font-normal">P&amp;L</th>
              <th className="px-3 py-1.5 text-right font-normal">%</th>
            </tr>
          </thead>
          <tbody>
            {livePositions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-term-faint">
                  No positions yet — place a trade below.
                </td>
              </tr>
            ) : (
              livePositions.map((p) => (
                <tr
                  key={p.ticker}
                  onClick={() => setSelected(p.ticker)}
                  className={`tnum cursor-pointer border-t border-term-line/60 transition-colors hover:bg-term-raised/40 ${
                    selected === p.ticker ? 'bg-term-raised/40' : ''
                  }`}
                >
                  <td className="px-3 py-1.5 font-semibold text-term-text">{p.ticker}</td>
                  <td className="px-2 py-1.5 text-right text-term-dim">{fmtQty(p.quantity)}</td>
                  <td className="px-2 py-1.5 text-right text-term-dim">{fmtPrice(p.avg_cost)}</td>
                  <td className="px-2 py-1.5 text-right text-term-text">{fmtPrice(p.current_price)}</td>
                  <td className={`px-2 py-1.5 text-right ${directionClass(p.unrealized_pnl)}`}>
                    {fmtSignedMoney(p.unrealized_pnl)}
                  </td>
                  <td className={`px-3 py-1.5 text-right ${directionClass(p.pnl_percent)}`}>
                    {fmtPercent(p.pnl_percent)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
