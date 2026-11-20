/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1117',
        panel: '#1a1d27',
        border: '#2a2d3a',
        accent: '#6366f1',
        danger: '#ef4444',
        warning: '#f59e0b',
        success: '#10b981',
      },
    },
  },
  plugins: [],
}
