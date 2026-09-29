import type { Config } from 'tailwindcss'
import base from './tailwind.config'

// Desk build: utilities are scoped under .cortex-root and the global reset (preflight) is off,
// so the Desk keeps its own base styles.
const config: Config = {
  ...base,
  important: '.cortex-root',
  corePlugins: { preflight: false }
}

export default config
