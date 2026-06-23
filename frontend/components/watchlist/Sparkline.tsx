"use client";

import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import type { PriceHistoryPoint } from "@/lib/usePriceStream";

interface SparklineProps {
  data: PriceHistoryPoint[];
  direction: "up" | "down" | "flat";
}

export function Sparkline({ data, direction }: SparklineProps) {
  if (data.length < 2) {
    return <div className="h-8 w-20" data-testid="sparkline-empty" />;
  }

  const color = direction === "down" ? "var(--down)" : "var(--up)";

  return (
    <div className="h-8 w-20" data-testid="sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis domain={["dataMin", "dataMax"]} hide />
          <Line
            type="monotone"
            dataKey="price"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
