import type { ApprovalRequestItem } from '@/types/approval'

export const initialApprovals: ApprovalRequestItem[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-APR-001',
    approval_type: 'Contract Confirmation',
    status: 'pending',
    title: 'Dérogation Assurance — Trequista Events',
    description: 'Attestation d’assurance échue le 30 août. Demande d’approbation pour confirmation de contrat avec engagement écrit de renouvellement sous 24h.',
    reference_doctype: 'Cortex Rental Transaction',
    reference_name: 'DEMO-TRX-2026-003',
    requested_by_type: 'Human',
    requested_by: 'alex.ops@cortex.demo',
    threshold_exceeded_details: 'Insurance coverage verification failed.',
    before_state: {
      rental_state: 'Quote',
      insurance_ready: false
    },
    after_state: {
      rental_state: 'Contract',
      insurance_ready: true,
      override_flag: true
    },
    evidence_ids: ['DEMO-EVD-INS-001'],
    created_at: '2026-09-01T11:45:00Z'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-APR-002',
    approval_type: 'Discount Override',
    status: 'pending',
    title: 'Remise Commerciale 25% — Production Nord',
    description: 'L’agent IA a proposé un rabais de 25% sur le pack Cooke S4/i pour un tournage de 14 jours. Dépasse le seuil d’approbation automatique de 15%.',
    reference_doctype: 'Cortex Rental Transaction',
    reference_name: 'DEMO-TRX-2026-001',
    requested_by_type: 'Agent',
    requested_by: 'Cortex Copilot Agent',
    threshold_exceeded_details: 'Discount 25% > Max Policy Limit 15%',
    before_state: {
      discount_percentage: 0,
      subtotal: 7350
    },
    after_state: {
      discount_percentage: 25,
      subtotal: 5512.50
    },
    evidence_ids: ['DEMO-EVD-POL-002'],
    created_at: '2026-09-02T09:15:00Z'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-APR-003',
    approval_type: 'Dispute Settlement',
    status: 'pending',
    title: 'Règlement Contestation Frais — Studio Lumière',
    description: 'Contestation de frais de nettoyage de capteur de 350,00 $ suite au retour de DEMO-TRX-2026-004. Client conteste la poussière antérieure au tournage.',
    reference_doctype: 'Cortex Rental Transaction',
    reference_name: 'DEMO-TRX-2026-004',
    requested_by_type: 'Human',
    requested_by: 'marc.finance@cortex.demo',
    threshold_exceeded_details: 'Fee waiver exceeds manager threshold ($250.00)',
    before_state: {
      cleaning_fee: 350.00,
      fee_waived: false
    },
    after_state: {
      cleaning_fee: 0.00,
      fee_waived: true
    },
    evidence_ids: ['DEMO-EVD-DISP-003'],
    created_at: '2026-09-02T14:30:00Z'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-APR-004',
    approval_type: 'AI Draft Execution',
    status: 'pending',
    title: 'Exécution Automatique Prolongation — Production Nord',
    description: 'Onyx Copilot a préparé un avenant de prolongation de 3 jours pour le tournage "Lumière d’Hiver". Confirmation humaine requise pour extension de contrat.',
    reference_doctype: 'Cortex Rental Transaction',
    reference_name: 'DEMO-TRX-2026-001',
    requested_by_type: 'Agent',
    requested_by: 'Cortex Copilot Agent',
    threshold_exceeded_details: 'Contract extension requires human supervisor confirmation',
    before_state: {
      ends_at: '2026-09-08T18:00:00Z',
      calendar_days: 7,
      billable_days: 3
    },
    after_state: {
      ends_at: '2026-09-11T18:00:00Z',
      calendar_days: 10,
      billable_days: 5
    },
    evidence_ids: ['DEMO-EVD-AI-004'],
    created_at: '2026-09-02T15:20:00Z'
  }
]
