'use client';

import { useTerminal } from '@/hooks/useTerminal';

export function Toast() {
  const { toast, backendUp } = useTerminal();

  return (
    <>
      {!backendUp && (
        <div className="pointer-events-none fixed left-1/2 top-2 z-50 -translate-x-1/2 rounded border border-accent/40 bg-term-void/95 px-3 py-1.5 font-mono text-2xs text-accent shadow-glow-amber">
          Backend unreachable — showing live feed only. Reconnecting…
        </div>
      )}
      {toast && (
        <div
          role="status"
          className="pointer-events-none fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded border border-term-border bg-term-void/95 px-4 py-2 font-mono text-xs text-term-text shadow-lg"
        >
          {toast}
        </div>
      )}
    </>
  );
}
