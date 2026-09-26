import { marked } from 'marked'
import DOMPurify from 'dompurify'

/** Model text → safe HTML. No images, forms or styles; external links open in a new tab. */
export function renderMarkdown(text: string): string {
  const raw = marked.parse(text || '', { async: false, gfm: true, breaks: true }) as string
  const clean = DOMPurify.sanitize(raw, { USE_PROFILES: { html: true }, FORBID_TAGS: ['style', 'img', 'iframe', 'form', 'input'] })
  return clean.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a href="$1" target="_blank" rel="noopener noreferrer"')
}
