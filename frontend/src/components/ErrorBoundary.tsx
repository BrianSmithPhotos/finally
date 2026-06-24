'use client';

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /** Optional custom fallback; defaults to the terminal error panel. */
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Top-level error boundary. A single malformed API payload (e.g. calling
 * `.map` on an unexpected shape) must not unmount the entire React tree into a
 * blank "Application error" screen — it degrades to a recoverable panel here.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface for debugging; never throw past the boundary.
    // eslint-disable-next-line no-console
    console.error('FinAlly UI error:', error, info.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex h-screen items-center justify-center p-6">
          <div className="panel max-w-md p-6 text-center">
            <p className="eyebrow mb-2 text-down">Terminal fault</p>
            <h1 className="mb-2 font-mono text-lg text-term-text">
              Something went wrong rendering the terminal.
            </h1>
            <p className="mb-4 font-mono text-xs text-term-dim">
              The market feed keeps running in the background. Reload, or retry
              once the backend is reachable.
            </p>
            <div className="flex justify-center gap-2">
              <button
                type="button"
                onClick={this.reset}
                className="rounded border border-primary/40 bg-primary/15 px-4 py-1.5 font-mono text-xs text-primary hover:bg-primary/25"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded bg-secondary px-4 py-1.5 font-mono text-xs font-semibold text-white hover:bg-secondary-bright"
              >
                Reload
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
