import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'kid-blue': '#4CC9F0',
        'kid-pink': '#F72585',
        'kid-yellow': '#FEE440',
        'kid-purple': '#7209B7',
      },
    },
  },
  plugins: [],
}
export default config
