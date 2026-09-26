import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../markdown'

describe('assistant markdown', () => {
  it('renders the usual formatting', () => {
    const html = renderMarkdown('**Gras**\n\n- un\n- deux\n\n| A | B |\n|---|---|\n| 1 | 2 |')
    expect(html).toContain('<strong>Gras</strong>')
    expect(html).toContain('<li>un</li>')
    expect(html).toContain('<table>')
  })

  it('strips scripts, event handlers, images and javascript: links from model text', () => {
    const html = renderMarkdown('<script>alert(1)</script><img src=x onerror=alert(2)>[x](javascript:alert(3)) <b onclick="alert(4)">b</b>')
    expect(html).not.toMatch(/<script|onerror|onclick|<img|javascript:/i)
  })

  it('opens external links in a new tab and keeps internal ones as app links', () => {
    expect(renderMarkdown('[doc](https://example.com)')).toContain('target="_blank" rel="noopener noreferrer"')
    expect(renderMarkdown('[loc](/rentals/TRX-1)')).toContain('href="/rentals/TRX-1"')
    expect(renderMarkdown('[loc](/rentals/TRX-1)')).not.toContain('target=')
  })
})
