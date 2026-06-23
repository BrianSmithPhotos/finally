"use client";

import type { ConnectionStatus } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: "bg-up", label: "Connected" },
  reconnecting: { color: "bg-accent-yellow", label: "Reconnecting" },
  disconnected: { color: "bg-down", label: "Disconnected" },
};

interface HeaderProps {
  totalValue: number;
  cashBalance: number;
  connectionStatus: ConnectionStatus;
}

export function Header({ totalValue, cashBalance, connectionStatus }: HeaderProps) {
  const status = STATUS_CONFIG[connectionStatus];

  return (
    <header className="flex items-center justify-between border-b border-border-muted bg-background-panel px-6 py-3">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-tight text-accent-yellow">FinAlly</span>
        <span className="text-xs text-gray-500">AI Trading Workstation</span>
      </div>

      <div className="flex items-center gap-8">
        <div className="text-right">
          <div className="text-xs uppercase tracking-wide text-gray-500">Portfolio Value</div>
          <div className="text-lg font-semibold" data-testid="header-total-value">
            {formatCurrency(totalValue)}
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs uppercase tracking-wide text-gray-500">Cash</div>
          <div className="text-lg font-semibold text-accent-blue" data-testid="header-cash-balance">
            {formatCurrency(cashBalance)}
          </div>
        </div>

        <div className="flex items-center gap-2" data-testid="connection-status" data-status={connectionStatus}>
          <span
            className={`h-2.5 w-2.5 rounded-full ${status.color}`}
            aria-label={status.label}
            title={status.label}
          />
          <span className="text-xs text-gray-400">{status.label}</span>
        </div>
      </div>
    </header>
  );
}
