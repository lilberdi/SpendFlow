/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        page: '#F8F9FA',
        ink: '#1A1D1F',
        muted: '#6F767E',
        mint: {
          DEFAULT: '#A7D7C5',
          soft: 'rgba(167, 215, 197, 0.35)',
          strong: 'rgba(167, 215, 197, 0.55)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 4px 15px rgba(0, 0, 0, 0.03)',
        bar: '0 10px 25px rgba(0, 0, 0, 0.03)',
      },
    },
  },
  plugins: [],
}
