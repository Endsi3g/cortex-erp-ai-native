import type { Config } from 'tailwindcss'
import preset from 'frappe-ui/tailwind'

const config: Config = {
  presets: [preset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      spacing: {
        '13': '3.25rem', // 52px (high-speed scanner)
        '14': '3.5rem',  // 56px (desktop topbar)
        '18': '4.5rem',  // 72px (collapsed sidebar)
        '62': '15.5rem', // 248px (expanded sidebar)
        '104': '26rem',  // 416px (copilot drawer)
      },
      colors: {
        cortex: {
          bg: '#F2F7F4',
          surface: '#FFFFFF',
          'surface-subtle': '#E8F1EC',
          'surface-dark': '#08120D',
          border: '#D0E0D7',
          'border-dark': '#102019',
          primary: {
            50: '#E8F7EE',
            100: '#C8EDD6',
            400: '#14B86A',
            500: '#087A43',
            600: '#066336',
            700: '#044C29',
            900: '#08120D'
          },
          ink: {
            50: '#F2F7F4',
            100: '#E2ECE6',
            200: '#C5D8CD',
            500: '#527563',
            800: '#102019',
            900: '#08120D'
          },
          text: {
            primary: '#08120D',
            secondary: '#365345',
            muted: '#638474',
            inverse: '#FFFFFF'
          },
          status: {
            verified: '#087A43',
            extracted: '#6D28D9',
            proposed: '#059669',
            alert: '#D97706',
            error: '#DC2626',
            info: '#2563EB'
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      }
    }
  },
  plugins: []
}

export default config
