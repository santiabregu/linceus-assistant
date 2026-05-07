/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'us-red': '#be0f2e',
        'us-red-dark': '#9e1c3f',
        'us-red-deep': '#7a1631',
      },
      fontFamily: {
        sans: ['"Open Sans"', '"Segoe UI"', 'Roboto', 'sans-serif'],
        display: ['Raleway', '"Open Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
