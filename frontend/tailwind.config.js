/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0d1117',
        panel: '#161b22',
        'panel-2': '#1c2230',
        border: '#21262d',
        'border-2': '#30363d',
        accent: '#58a6ff',
        'accent-2': '#388bfd',
        danger: '#f85149',
        warning: '#d29922',
        success: '#3fb950',
        muted: '#8b949e',
        subtle: '#484f58',
      },
    },
  },
  plugins: [],
}
