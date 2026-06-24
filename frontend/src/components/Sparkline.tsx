'use client';

import { useEffect, useRef } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  /** Stroke color; defaults to amber accent. */
  color?: string;
  className?: string;
}

/**
 * Lightweight canvas sparkline. Renders the accumulated price series; fills in
 * progressively as more SSE ticks arrive. Canvas (not SVG) keeps re-renders
 * cheap when many rows update at ~500ms.
 */
export function Sparkline({
  data,
  width = 96,
  height = 28,
  color,
  className,
}: SparklineProps) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    if (data.length < 2) return;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const stepX = (width - pad * 2) / (data.length - 1);
    const toY = (v: number) => pad + (height - pad * 2) * (1 - (v - min) / range);

    // Trend-aware color: green if up over the window, red if down.
    const trendUp = data[data.length - 1] >= data[0];
    const stroke = color ?? (trendUp ? '#26d07c' : '#f0506e');

    // Area fill under the line for a touch of weight.
    ctx.beginPath();
    ctx.moveTo(pad, toY(data[0]));
    data.forEach((v, i) => ctx.lineTo(pad + i * stepX, toY(v)));
    ctx.lineTo(pad + (data.length - 1) * stepX, height - pad);
    ctx.lineTo(pad, height - pad);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, `${stroke}33`);
    grad.addColorStop(1, `${stroke}00`);
    ctx.fillStyle = grad;
    ctx.fill();

    // Line.
    ctx.beginPath();
    ctx.moveTo(pad, toY(data[0]));
    data.forEach((v, i) => ctx.lineTo(pad + i * stepX, toY(v)));
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = stroke;
    ctx.lineJoin = 'round';
    ctx.stroke();
  }, [data, width, height, color]);

  return (
    <canvas
      ref={ref}
      style={{ width, height }}
      className={className}
      aria-hidden="true"
    />
  );
}
