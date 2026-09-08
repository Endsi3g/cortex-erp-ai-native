import type { InboundRequestItem } from '@/types/intelligence'

export const initialInboundRequests: InboundRequestItem[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-INB-001',
    source: 'email',
    sender_email: 'production@nord-film.demo',
    sender_name: 'Marc-André (Production Nord)',
    subject: 'Demande de location caméra pour tournage 10-17 septembre',
    raw_body: 'Bonjour l’équipe Cortex,\n\nNous préparons notre prochain tournage dans les Laurentides du 10 au 17 septembre 2026. Auriez-vous un package ARRI Alexa 35 disponible avec la série de primes Cooke S4/i et un kit DJI Ronin 2 ?\n\nMerci,\nMarc-André\nProduction Nord Inc.',
    received_at: '2026-09-02T08:30:00Z',
    overall_confidence: 0.94,
    extracted_fields: {
      customer_name: 'Production Nord Inc.',
      start_date: '2026-09-10T08:00:00Z',
      end_date: '2026-09-17T18:00:00Z',
      equipment_mentions: [
        { raw_text: 'ARRI Alexa 35', matched_item_code: 'DEMO-ITM-ALX35', quantity: 1, confidence: 0.98 },
        { raw_text: 'série de primes Cooke S4/i', matched_item_code: 'DEMO-ITM-CKE-S4', quantity: 1, confidence: 0.95 },
        { raw_text: 'DJI Ronin 2', matched_item_code: 'DEMO-ITM-DJI-RS3', quantity: 1, confidence: 0.92 }
      ],
      missing_fields: []
    },
    status: 'new'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    id: 'DEMO-INB-002',
    source: 'pdf',
    sender_email: 'events@trequista.demo',
    sender_name: 'Trequista Events Desk',
    subject: 'Devis technique Festival 2026 — Annexes PDF',
    raw_body: '[Document PDF extrait: Appel d’offres éclairage et captation multi-caméras pour événement extérieur 18-20 septembre]',
    received_at: '2026-09-01T15:20:00Z',
    overall_confidence: 0.78,
    extracted_fields: {
      customer_name: 'Trequista Events',
      start_date: '2026-09-18T08:00:00Z',
      end_date: '2026-09-20T22:00:00Z',
      equipment_mentions: [
        { raw_text: '4 projecteurs LED haute puissance', matched_item_code: 'DEMO-ITM-APU-600', quantity: 4, confidence: 0.85 }
      ],
      missing_fields: ['Détail accessoires caméras', 'Coordonnées du régisseur général']
    },
    status: 'reviewed'
  }
]
