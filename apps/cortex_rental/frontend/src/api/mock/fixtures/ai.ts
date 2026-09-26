import type { AgentRun, InboundDetail, InboxItem } from '@/api/contracts/ai'

// DEMO data in the api/v1/ai.py shapes. Approval rows are derived from the
// approvals fixture at read time so decisions show up in the inbox.

export const initialInboxRows: InboxItem[] = [
  {
    id: 'inbound:DEMO-INB-001',
    kind: 'inbound',
    source_id: 'DEMO-INB-001',
    title: 'Demande de location caméra pour tournage 10-17 septembre',
    summary: '',
    reference: 'Email',
    customer: 'Production Nord Inc.',
    agent: 'cortex-intake',
    requested_by: 'production@nord-film.demo',
    requested_by_type: 'External',
    state: 'ready',
    confidence: 0.94,
    priority: 'normal',
    created_at: '2026-09-02 08:30:00'
  },
  {
    id: 'inbound:DEMO-INB-002',
    kind: 'inbound',
    source_id: 'DEMO-INB-002',
    title: 'Devis technique Festival 2026 — Annexes PDF',
    summary: 'customer.email, items[0].matched_item_code',
    reference: 'Email',
    customer: 'Trequista Events',
    agent: 'cortex-intake',
    requested_by: 'events@trequista.demo',
    requested_by_type: 'External',
    state: 'low_confidence',
    confidence: 0.58,
    priority: 'high',
    created_at: '2026-09-01 15:20:00'
  },
  {
    id: 'draft:DEMO-TRX-2026-003',
    kind: 'draft',
    source_id: 'DEMO-TRX-2026-003',
    title: 'DEMO-TRX-2026-003',
    summary: '',
    reference: 'Cortex Rental Transaction',
    customer: 'Trequista Events',
    agent: 'cortex-intake',
    requested_by: 'cortex-intake',
    requested_by_type: 'Agent',
    state: 'ready',
    confidence: null,
    priority: 'normal',
    created_at: '2026-09-01 16:05:00',
    amount: 4280
  }
]

export const initialInboundDetails: InboundDetail[] = [
  {
    kind: 'inbound',
    id: 'DEMO-INB-001',
    status: 'Received',
    subject: 'Demande de location caméra pour tournage 10-17 septembre',
    sender_email: 'production@nord-film.demo',
    source_channel: 'Email',
    received_at: '2026-09-02 08:30:00',
    raw_text: 'Bonjour l’équipe Cortex,\n\nNous préparons notre prochain tournage dans les Laurentides du 10 au 17 septembre 2026. Auriez-vous un package ARRI Alexa 35 disponible avec la série de primes Cooke S4/i et un kit DJI Ronin 2 ?\n\nMerci,\nMarc-André\nProduction Nord Inc.',
    extracted_transaction: null,
    evidence: [
      { id: 'DEMO-EVD-001', channel: 'Email', excerpt: 'du 10 au 17 septembre 2026 … ARRI Alexa 35 … Cooke S4/i … DJI Ronin 2', sha256: 'demo', mime_type: 'text/plain', scanned_clean: true, has_file: false }
    ],
    extraction: {
      id: 'DEMO-EXT-001',
      schema_version: '1.0',
      validation_status: 'Valid',
      validation_errors: [],
      overall_confidence: 0.94,
      calibrated: false,
      review_required: false,
      model: 'demo-model',
      agent: 'cortex-intake',
      extracted_at: '2026-09-02 08:35:00',
      payload: {
        customer: { name: 'Marc-André', company_name: 'Production Nord Inc.', email: 'production@nord-film.demo', confidence: 0.97 },
        rental_period: { starts_at: '2026-09-10T08:00:00', ends_at: '2026-09-17T18:00:00', confidence: 0.95 },
        items: [
          { raw_text: 'ARRI Alexa 35', quantity: 1, matched_item_code: 'DEMO-ITM-ALX35', confidence: 0.98 },
          { raw_text: 'série de primes Cooke S4/i', quantity: 1, matched_item_code: 'DEMO-ITM-CKE-S4', confidence: 0.95 },
          { raw_text: 'DJI Ronin 2', quantity: 1, matched_item_code: 'DEMO-ITM-DJI-RS3', confidence: 0.82 }
        ]
      },
      missing_fields: []
    }
  },
  {
    kind: 'inbound',
    id: 'DEMO-INB-002',
    status: 'Received',
    subject: 'Devis technique Festival 2026 — Annexes PDF',
    sender_email: 'events@trequista.demo',
    source_channel: 'Email',
    received_at: '2026-09-01 15:20:00',
    raw_text: '[Document PDF extrait : appel d’offres éclairage et captation multi-caméras pour événement extérieur 18-20 septembre — 4 projecteurs LED haute puissance]',
    extracted_transaction: null,
    evidence: [
      { id: 'DEMO-EVD-002', channel: 'Email', excerpt: 'appel d’offres éclairage … 18-20 septembre', sha256: 'demo', mime_type: 'application/pdf', scanned_clean: true, has_file: true }
    ],
    extraction: {
      id: 'DEMO-EXT-002',
      schema_version: '1.0',
      validation_status: 'Valid',
      validation_errors: [],
      overall_confidence: 0.58,
      calibrated: false,
      review_required: true,
      model: 'demo-model',
      agent: 'cortex-intake',
      extracted_at: '2026-09-01 15:24:00',
      payload: {
        customer: { name: 'Trequista Events', company_name: 'Trequista Events', email: null, confidence: 0.7 },
        rental_period: { starts_at: '2026-09-18T08:00:00', ends_at: '2026-09-20T22:00:00', confidence: 0.8 },
        items: [{ raw_text: '4 projecteurs LED haute puissance', quantity: 4, matched_item_code: null, confidence: 0.41 }]
      },
      missing_fields: ['customer.email', 'items[0].matched_item_code']
    }
  }
]

export const initialAgentRuns: AgentRun[] = [
  {
    id: 'DEMO-RUN-001',
    agent: 'cortex-intake',
    request_id: 'demo-req-001',
    actor: 'agent:cortex-intake',
    model: 'demo-model',
    status: 'Completed',
    tool_call_count: 3,
    started_at: '2026-09-02 08:34:50',
    last_seen_at: '2026-09-02 08:35:00',
    tool_calls: [
      { tool_name: 'search_customers', scope: 'agent:customer:read', status: 'Success', started_at: '2026-09-02 08:34:51', duration_ms: 120, error: null },
      { tool_name: 'check_inventory_availability', scope: 'agent:availability:read', status: 'Success', started_at: '2026-09-02 08:34:53', duration_ms: 410, error: null },
      { tool_name: 'create_quote_draft', scope: 'agent:quote:draft', status: 'Success', started_at: '2026-09-02 08:34:58', duration_ms: 690, error: null }
    ]
  },
  {
    id: 'DEMO-RUN-002',
    agent: 'cortex-availability',
    request_id: 'demo-req-002',
    actor: 'agent:cortex-availability',
    model: 'demo-model',
    status: 'Failed',
    tool_call_count: 1,
    started_at: '2026-09-02 09:12:00',
    last_seen_at: '2026-09-02 09:12:04',
    tool_calls: [
      { tool_name: 'create_quote_draft', scope: 'agent:quote:draft', status: 'Denied', started_at: '2026-09-02 09:12:02', duration_ms: 35, error: 'Scope agent:quote:draft non accordé.' }
    ]
  }
]
