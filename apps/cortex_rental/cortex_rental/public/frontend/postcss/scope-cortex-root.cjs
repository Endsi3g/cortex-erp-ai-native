/**
 * Confines every rule of the Desk build under `.cortex-root` so Cortex styles cannot change the
 * Desk (navbar, sidebar, forms). Tailwind utilities are already scoped by `important`;
 * this plugin scopes the rest (frappe-ui base layer, Cortex design-system CSS) and leaves
 * at-rules such as @font-face and @keyframes untouched.
 */
const SCOPE = '.cortex-root'

function scopeSelector(selector) {
  const trimmed = selector.trim()
  if (trimmed.startsWith(SCOPE)) return trimmed
  if (trimmed === ':root' || trimmed === 'html' || trimmed === 'body') return SCOPE
  return `${SCOPE} ${trimmed.replace(/^(:root|html|body)\s+/, '')}`
}

module.exports = () => ({
  postcssPlugin: 'scope-cortex-root',
  Rule(rule) {
    if (rule.__cortexScoped) return
    const parent = rule.parent
    if (parent && parent.type === 'atrule' && /keyframes$/i.test(parent.name)) return
    rule.selectors = rule.selectors.map(scopeSelector)
    rule.__cortexScoped = true
  }
})
module.exports.postcss = true
