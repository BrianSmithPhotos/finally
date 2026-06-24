'use client';

import { useTerminal } from '@/hooks/useTerminal';
import { ConnectionDot } from './ConnectionDot';
import { fmtMoney, fmtSignedMoney, fmtPercent, directionClass } from '@/lib/format';

export function Header() {
  const { status, liveTotalValue, portfolio } = useTerminal();

  const cash = portfolio?.cash_balance ?? null;
  const total = liveTotalValue ?? portfolio?.total_value ?? null;
  // Day P&L proxy: total vs. the $10k starting stake (no auth = single session).
  const pnl = total != null ? total - 10000 : null;
  const pnlPct = pnl != null ? (pnl / 10000) * 100 : null;

  return (
    <header className="flex items-center justify-between border-b border-term-border bg-term-void/60 px-4 py-2.5">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-lg font-bold tracking-tight text-term-text">
          Fin<span className="text-accent">Ally</span>
        </span>
        <span className="eyebrow hidden sm:inline">AI Trading Workstation</span>
      </div>

      <div className="flex items-center gap-5 sm:gap-8">
        <Stat label="Cash" value={fmtMoney(cash)} />
        <Stat
          label="Net Liq"
          value={fmtMoney(total)}
          emphasis
        />
        <div className="hidden flex-col items-end md:flex">
          <span className="eyebrow">Session P&amp;L</span>
          <span className={`tnum font-mono text-sm ${directionClass(pnl)}`}>
            {fmtSignedMoney(pnl)}{' '}
            <span className="text-2xs">{pnlPct != null ? `(${fmtPercent(pnlPct)})` : ''}</span>
          </span>
        </div>
        <ConnectionDot status={status} />
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div className="flex flex-col items-end">
      <span className="eyebrow">{label}</span>
      <span
        className={`tnum font-mono ${
          emphasis ? 'text-base font-semibold text-accent' : 'text-sm text-term-text'
        }`}
      >
        {value}
      </span>
    </div>
  );
}
