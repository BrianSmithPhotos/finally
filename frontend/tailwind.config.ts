import type { Config } from 'tailwindcss';

/**
 * FinAlly terminal theme.
 *
 * Identity: a phosphor-amber trading desk. Amber (`accent`) is reserved as the
 * "live data" signature glow; blue is structural/interactive; purple is submit.
 * No pure black — the deepest surface is `term-void` (#0a0e14).
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Surfaces (deepest -> highest)
        'term-void': '#0a0e14',
        'term-bg': '#0d1117',
        'term-panel': '#141a23',
        'term-raised': '#1a2230',
        'term-border': '#2a3340',
        'term-line': '#222b36',
        // Text
        'term-text': '#d7e0ea',
        'term-dim': '#8a97a8',
        'term-faint': '#5a6675',
        // Brand (from PLAN.md §2)
        accent: '#ecad0a', // amber — the live/data signature
        'accent-dim': '#9a7307',
        primary: '#209dd7', // blue — interactive/structural
        'primary-dim': '#16678e',
        secondary: '#753991', // purple — submit
        'secondary-bright': '#9249b4',
        // Market tape
        'up': '#26d07c',
        'up-glow': 'rgba(38, 208, 124, 0.18)',
        'down': '#f0506e',
        'down-glow': 'rgba(240, 80, 110, 0.18)',
      },
      fontFamily: {
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        'glow-amber': '0 0 12px rgba(236, 173, 10, 0.35)',
      },
      keyframes: {
        'flash-up': {
          '0%': { backgroundColor: 'var(--up-glow)' },
          '100%': { backgroundColor: 'transparent' },
        },
        'flash-down': {
          '0%': { backgroundColor: 'var(--down-glow)' },
          '100%': { backgroundColor: 'transparent' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
      },
      animation: {
        'flash-up': 'flash-up 500ms ease-out',
        'flash-down': 'flash-down 500ms ease-out',
        'pulse-dot': 'pulse-dot 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
