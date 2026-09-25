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
        '12.5': '3.125rem', // 50px (collapsed rail, ERPNext reference)
        '14': '3.5rem',  // 56px
        '18': '4.5rem',  // 72px
        '55': '13.75rem', // 220px (expanded rail)
        '104': '26rem',  // 416px (copilot drawer)
      },
      colors: {
        // Legacy `cortex-*` names, re-pointed at the Frappe UI (espresso)
        // palette so every screen follows the ERPNext reference. New code
        // uses Frappe UI's semantic classes (bg-surface-*, text-ink-*,
        // border-outline-*) directly.
        cortex: {
          bg: '#F8F8F8',
          surface: '#FFFFFF',
          'surface-subtle': '#F8F8F8',
          'surface-dark': '#171717',
          border: '#EDEDED',
          'border-dark': '#E2E2E2',
          primary: {
            50: '#F2FDF4',
            100: '#E4FAEB',
            200: '#C3F9D3',
            400: '#86E0A8',
            500: '#278F5E',
            600: '#278F5E',
            700: '#137949',
            800: '#075E35',
            900: '#173B2C'
          },
          ink: {
            50: '#F8F8F8',
            100: '#F3F3F3',
            200: '#EDEDED',
            500: '#7C7C7C',
            800: '#383838',
            900: '#171717'
          },
          text: {
            primary: '#171717',
            secondary: '#525252',
            muted: '#7C7C7C',
            inverse: '#FFFFFF'
          },
          status: {
            verified: '#278F5E',
            extracted: '#525252',
            proposed: '#278F5E',
            alert: '#DB7706',
            error: '#CC2929',
            info: '#007BE0'
          }
        },
        // Measured on inspiration/image.png (ERPNext Profit and Loss).
        report: {
          income: '#E789AD',
          expense: '#4B88D2',
          profit: '#69B97A',
          'profit-text': '#72B88E',
          grid: '#F4F5F6'
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
