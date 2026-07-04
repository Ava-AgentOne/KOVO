/** @type {import('tailwindcss').Config} */
import colors from 'tailwindcss/colors'

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // v2.1 design system: cool slate-tinted grays — dark mode gets
        // blue-tinted elevation layers that match Kovo Blue instead of
        // flat neutral gray panels.
        gray: colors.slate,
        brand: {
          50:  '#e8f4fd',
          100: '#c5e2f9',
          200: '#9ecef4',
          300: '#6eb8ee',
          400: '#4da8ea',
          500: '#378ADD',
          600: '#2d7bc4',
          700: '#236aa8',
          800: '#1a5a8e',
          900: '#042C53',
        },
      },
    },
  },
  plugins: [],
}
