/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        rivian: {
          yellow: '#FFC800',
          cyan: '#00D1FF',
          dark: '#1C1C1C',
          darker: '#121212',
          panel: '#242424',
          wood: '#3e2723'
        }
      }
    },
  },
  plugins: [],
}
