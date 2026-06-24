'use client';

import type { ConnectionStatus } from '@/lib/types';

const MAP: Record<ConnectionStatus, { color: string; label: string; pulse: boolean }> = {
  connected: { color: '#26d07c', label: 'LIVE', pulse: false },
  connecting: { color: '#ecad0a', label: 'CONNECTING', pulse: true },
  reconnecting: { color: '#ecad0a', label: 'RECONNECTING', pulse: true },
  disconnected: { color: '#f0506e', label: 'OFFLINE', pulse: false },
};

export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const { color, label, pulse } = MAP[status];
  return (
    <div
      className="flex items-center gap-2"
      role="status"
      aria-label={`Connection ${label.toLowerCase()}`}
    >
      <span
        data-testid="connection-dot"
        data-status={status}
        className={`h-2 w-2 rounded-full ${pulse ? 'animate-pulse-dot' : ''}`}
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
      <span className="font-mono text-2xs tracking-[0.18em]" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
