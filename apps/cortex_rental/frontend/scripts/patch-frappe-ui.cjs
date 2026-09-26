const fs = require('fs')
const path = require('path')

const baseDir = path.resolve(__dirname, '..')

// 1. Patch frappe-ui/tailwind/plugin.js
const pluginPath = path.join(baseDir, 'node_modules/frappe-ui/tailwind/plugin.js')
if (fs.existsSync(pluginPath)) {
  let content = fs.readFileSync(pluginPath, 'utf8')
  if (content.includes("from 'tailwindcss/plugin'")) {
    content = content.replace("from 'tailwindcss/plugin'", "from 'tailwindcss/plugin.js'")
    fs.writeFileSync(pluginPath, content, 'utf8')
  }
}

// 2. Patch frappe-ui/tailwind/lucideIconsPlugin.js
const lucidePath = path.join(baseDir, 'node_modules/frappe-ui/tailwind/lucideIconsPlugin.js')
if (fs.existsSync(lucidePath)) {
  let content = fs.readFileSync(lucidePath, 'utf8')
  if (content.includes("from 'tailwindcss/plugin'")) {
    content = content.replace("from 'tailwindcss/plugin'", "from 'tailwindcss/plugin.js'")
    fs.writeFileSync(lucidePath, content, 'utf8')
  }
}

// 3. Patch frappe-ui/tailwind/colorPalette.js
const colorPalettePath = path.join(baseDir, 'node_modules/frappe-ui/tailwind/colorPalette.js')
if (fs.existsSync(colorPalettePath)) {
  let content = fs.readFileSync(colorPalettePath, 'utf8')
  if (content.includes("from 'tailwindcss/colors'")) {
    content = content.replace("from 'tailwindcss/colors'", "from 'tailwindcss/colors.js'")
  }
  if (content.includes("import colorsData from './colors.json'")) {
    content = content.replace(
      "import colorsData from './colors.json'",
      "import { createRequire } from 'node:module'\nconst require = createRequire(import.meta.url)\nconst colorsData = require('./colors.json')"
    )
  }
  fs.writeFileSync(colorPalettePath, content, 'utf8')
}
