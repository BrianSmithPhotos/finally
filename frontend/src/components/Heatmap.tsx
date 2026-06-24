'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTerminal } from '@/hooks/useTerminal';
import { squarify } from '@/lib/treemap';
import { fmtPercent } from '@/lib/format';
import type { Position } from '@/lib/types';

/** Map a P&L % to a green/red heat color. Clamped at ±5%. */
function heatColor(pnlPct: number): string {
  const clamped = Math.max(-5, Math.min(5, pnlPct));
  const intensity = Math.abs(clamped) / 5; // 0..1
  if (clamped >= 0) {
    // green family
    const l = 18 + intensity * 26;
    return `hsl(152 60% ${l}%)`;
  }
  const l = 18 + intensity * 26;
  return `hsl(348 70% ${l}%)`;
}

export function Heatmap() {
  const { livePositions, setSelected, selected } = useTerminal();
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const rects = useMemo(() => {
    if (size.w === 0 || size.h === 0) return [];
    const items = livePositions
      .map((p) => ({ value: Math.abs(p.current_price * p.quantity), data: p }))
      .filter((it) => it.value > 0);
    return squarify<Position>(items, size.w, size.h);
  }, [livePositions, size]);

  return (
    <section className="panel flex h-full flex-col" aria-label="Portfolio heatmap">
      <div className="panel-head">
        <span className="eyebrow">Position Heatmap</span>
        <span className="font-mono text-2xs text-term-faint">size = weight · color = P&amp;L</span>
      </div>
      <div ref={ref} className="relative min-h-0 flex-1">
        {livePositions.length === 0 ? (
          <div className="flex h-full items-center justify-center font-mono text-xs text-term-faint">
            No open positions
          </div>
        ) : (
          rects.map((r) => {
            const p = r.data;
            const isSel = selected === p.ticker;
            const showLabel = r.w > 44 && r.h > 26;
            return (
              <button
                key={p.ticker}
                type="button"
                onClick={() => setSelected(p.ticker)}
                title={`${p.ticker} · ${fmtPercent(p.pnl_percent)}`}
                className="absolute overflow-hidden border border-term-void/70 text-left transition-[outline] focus:outline focus:outline-2 focus:outline-primary"
                style={{
                  left: r.x,
                  top: r.y,
                  width: Math.max(0, r.w - 1),
                  height: Math.max(0, r.h - 1),
                  background: heatColor(p.pnl_percent),
                  outline: isSel ? '2px solid #ecad0a' : undefined,
                }}
              >
                {showLabel && (
                  <span className="pointer-events-none absolute inset-0 flex flex-col justify-center p-1.5 leading-tight">
                    <span className="font-mono text-xs font-bold text-white drop-shadow">
                      {p.ticker}
                    </span>
                    <span className="tnum font-mono text-2xs text-white/90 drop-shadow">
                      {fmtPercent(p.pnl_percent)}
                    </span>
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
