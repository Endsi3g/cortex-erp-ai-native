import type { AiDraftItem } from '@/types/intelligence'

export const initialDrafts: AiDraftItem[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-DFT-001',
    draft_type: 'Quote Draft',
    title: 'Proposition Devis — Production Nord (Sept 10-17)',
    ai_state: 'proposed',
    source_evidence_id: 'DEMO-INB-001',
    source_evidence_type: 'Inbound Request (Email)',
    confidence_score: 0.94,
    proposed_payload: {
      customer_id: 'DEMO-CUST-001',
      starts_at: '2026-09-10T08:00:00Z',
      ends_at: '2026-09-17T18:00:00Z',
      items: [
        { item_code: 'DEMO-ITM-ALX35', quantity: 1 },
        { item_code: 'DEMO-ITM-CKE-S4', quantity: 1 },
        { item_code: 'DEMO-ITM-DJI-RS3', quantity: 1 }
      ]
    },
    target_doctype: 'Cortex Rental Transaction',
    created_at: '2026-09-02T08:35:00Z',
    status: 'pending_review'
  }
]
