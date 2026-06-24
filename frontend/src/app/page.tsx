'use client';

import { useState } from 'react';
import { TerminalProvider } from '@/hooks/useTerminal';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Header } from '@/components/Header';
import { Watchlist } from '@/components/Watchlist';
import { MainChart } from '@/components/MainChart';
import { Heatmap } from '@/components/Heatmap';
import { PnlChart } from '@/components/PnlChart';
import { PositionsTable } from '@/components/PositionsTable';
import { TradeBar } from '@/components/TradeBar';
import { ChatPanel } from '@/components/ChatPanel';
import { Toast } from '@/components/Toast';

export default function Page() {
  const [chatCollapsed, setChatCollapsed] = useState(false);

  return (
    <ErrorBoundary>
      <TerminalProvider>
        <TerminalShell chatCollapsed={chatCollapsed} setChatCollapsed={setChatCollapsed} />
      </TerminalProvider>
    </ErrorBoundary>
  );
}

function TerminalShell({
  chatCollapsed,
  setChatCollapsed,
}: {
  chatCollapsed: boolean;
  setChatCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
}) {
  return (
    <>
      <div className="flex h-screen min-h-screen flex-col lg:overflow-hidden">
        <Header />

        {/* Desktop terminal grid: watchlist | charts+positions | copilot.
            On < lg it collapses to a single scrolling column. */}
        <main className="grid flex-1 gap-2 p-2 lg:min-h-0 lg:grid-cols-[300px_minmax(0,1fr)_auto]">
          {/* Left rail — watchlist */}
          <div className="min-h-[320px] lg:min-h-0">
            <Watchlist />
          </div>

          {/* Center column */}
          <div className="grid gap-2 lg:min-h-0 lg:grid-rows-[minmax(220px,1.4fr)_minmax(180px,1fr)_auto]">
            <div className="grid gap-2 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] lg:min-h-0">
              <div className="min-h-[260px] lg:min-h-0">
                <MainChart />
              </div>
              <div className="hidden min-h-0 xl:block">
                <Heatmap />
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2 lg:min-h-0">
              <div className="min-h-[200px] lg:min-h-0">
                <PositionsTable />
              </div>
              <div className="min-h-[200px] lg:min-h-0">
                <PnlChart />
              </div>
            </div>
            <TradeBar />
          </div>

          {/* Right rail — AI copilot */}
          <div className={`min-h-[420px] lg:min-h-0 ${chatCollapsed ? 'lg:w-11' : 'lg:w-[340px]'}`}>
            <ChatPanel collapsed={chatCollapsed} onToggle={() => setChatCollapsed((v) => !v)} />
          </div>
        </main>

        <Toast />
      </div>
    </>
  );
}
