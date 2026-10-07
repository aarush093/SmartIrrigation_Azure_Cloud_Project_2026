/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // One colour per tile, used consistently on screen and on the
        // laminated card so the two teach each other.
        water: '#3b82f6',
        power: '#f59e0b',
        rain: '#38bdf8',
        ink: '#0f1115'
      },
      fontSize: {
        // The primary number on each tile. Deliberately enormous: it must be
        // readable at arm's length in sunlight by someone with poor eyesight.
        tile: ['4.5rem', { lineHeight: '1' }]
      },
      minHeight: { touch: '4rem' }
    }
  },
  plugins: []
}
