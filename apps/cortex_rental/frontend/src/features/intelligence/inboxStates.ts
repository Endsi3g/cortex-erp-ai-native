import type { InboxState } from '@/api/contracts/ai'

export type BadgeTheme = 'gray' | 'blue' | 'green' | 'orange' | 'red'

export const INBOX_STATE_THEME: Record<InboxState, BadgeTheme> = {
  processing: 'gray',
  ready: 'blue',
  low_confidence: 'orange',
  needs_review: 'orange',
  extraction_error: 'red',
  validated: 'green',
  applied: 'green',
  rejected: 'gray',
  expired: 'gray'
}

export const CLOSED_STATES: InboxState[] = ['validated', 'applied', 'rejected', 'expired']

/** Model score shown as a raw percentage; the UI always labels it "not calibrated". */
export function formatScore(score: number | null | undefined): string {
  return score === null || score === undefined ? '—' : `${Math.round(score * 100)} %`
}
