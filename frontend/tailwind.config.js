/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface:      '#f8fafc',
        panel:        '#ffffff',
        'panel-2':    '#f1f5f9',
        border:       '#e2e8f0',
        'border-2':   '#cbd5e1',
        accent:       '#6366f1',
        'accent-2':   '#4f46e5',
        danger:       '#ef4444',
        warning:      '#f59e0b',
        success:      '#10b981',
        muted:        '#64748b',
        subtle:       '#94a3b8',
        foreground:   '#0f172a',
      },
    },
  },
  plugins: [],
}
