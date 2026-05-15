/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#E8F0FE',
          100: '#C5D8FC',
          500: '#1A56DB',
          600: '#1347CC',
          700: '#003366',
          900: '#001A33',
        },
      },
    },
  },
  plugins: [],
}
