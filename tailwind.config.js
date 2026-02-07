/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'heading': ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
