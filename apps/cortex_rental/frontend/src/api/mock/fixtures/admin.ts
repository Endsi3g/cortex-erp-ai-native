import type { RentalPolicy, MigrationBatch } from '@/types/domain'

export const initialPolicies: RentalPolicy[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    name: 'POL-PRICING-7D-3D',
    policy_name: 'Tarification Standard 7 Jours = 3 Jours Facturés',
    version: 'v1.4',
    description: 'Une location de 7 jours calendaires consécutifs est facturée au tarif équivalent de 3 jours journaliers.',
    rules: [
      { rule_key: 'WEEKLY_RATE_RATIO', rule_description: 'Facteur multiplicateur semaine', value: '3.0' },
      { rule_key: 'MONTHLY_RATE_RATIO', rule_description: 'Facteur multiplicateur mois (28j)', value: '9.0' },
      { rule_key: 'WEEKEND_RULE', rule_description: 'Vendredi 16h au Lundi 10h = 1 jour', value: '1.0' }
    ],
    effective_from: '2026-01-01',
    is_active: true
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    name: 'POL-INSURANCE-THRESHOLD',
    policy_name: 'Exigences d’Assurance et Caution',
    version: 'v2.0',
    description: 'Toute transaction supérieure à 5 000 $ CAD exige une attestation d’assurance avec responsabilité civile de 2 000 000 $ minimum.',
    rules: [
      { rule_key: 'MIN_INSURANCE_AMOUNT', rule_description: 'Montant minimal requis', value: '2000000 CAD' },
      { rule_key: 'OVERRIDE_ROLE', rule_description: 'Rôle autorisé pour dérogation', value: 'Operations Lead' }
    ],
    effective_from: '2026-01-01',
    is_active: true
  }
]

export const initialMigrationBatches: MigrationBatch[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    batch_id: 'DEMO-MIG-001',
    legacy_system: 'Current-RMS',
    started_at: '2026-08-15T10:00:00Z',
    total_records: 1250,
    imported_records: 1242,
    quarantined_records: 8,
    status: 'imported',
    quarantine_reasons: [
      { record_ref: 'CUR-EQ-991', reason: 'Missing serial number barcode mapping' },
      { record_ref: 'CUR-CUST-402', reason: 'Invalid tax ID formatting' }
    ]
  }
]
