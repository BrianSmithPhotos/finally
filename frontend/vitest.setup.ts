import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// jsdom lacks canvas — stub getContext so Sparkline renders without throwing.
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as never;
}

// jsdom lacks ResizeObserver (used by the heatmap).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// @ts-expect-error assigning test stub
global.ResizeObserver = global.ResizeObserver || ResizeObserverStub;
