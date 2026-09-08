export interface DiffEntry {
  field: string
  oldValue: unknown
  newValue: unknown
}

export function computeObjectDiff(before: Record<string, unknown> = {}, after: Record<string, unknown> = {}): DiffEntry[] {
  const diffs: DiffEntry[] = []
  const allKeys = new Set([...Object.keys(before), ...Object.keys(after)])

  allKeys.forEach((key) => {
    const valBefore = before[key]
    const valAfter = after[key]

    if (JSON.stringify(valBefore) !== JSON.stringify(valAfter)) {
      diffs.push({
        field: key,
        oldValue: valBefore,
        newValue: valAfter
      })
    }
  })

  return diffs
}

export async function computeSha256(content: string): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const encoder = new TextEncoder()
    const data = encoder.encode(content)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  }
  // Fallback simple deterministic hash if subtle crypto not in environment
  let hash = 0
  for (let i = 0; i < content.length; i++) {
    hash = (hash << 5) - hash + content.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash).toString(16).padStart(64, '0')
}

export function formatAuditActionTitle(action: string): string {
  const map: Record<string, string> = {
    'cortex.rental.quote_created': 'Création du devis',
    'cortex.rental.quote_updated': 'Mise à jour du devis',
    'cortex.rental.reservation_confirmed': 'Confirmation de réservation',
    'cortex.rental.contract_approved': 'Approbation du contrat',
    'cortex.rental.checkout_completed': 'Sortie d’équipement (Check-out)',
    'cortex.rental.partial_return_completed': 'Retour partiel de matériel',
    'cortex.rental.checkin_completed': 'Clôture de retour (Check-in)',
    'cortex.scanner.checkout_item': 'Scan d’équipement en sortie',
    'cortex.scanner.checkin_item': 'Scan d’équipement au retour',
    'cortex.scanner.serial_marked_missing': 'Équipement marqué manquant',
    'cortex.scanner.damage_evidence_added': 'Déclaration d’anomalie / bris',
    'cortex.consignment.statement_exported': 'Export du relevé propriétaire',
    'cortex.approval.request_approved': 'Approbation validée',
    'cortex.approval.request_rejected': 'Approbation refusée'
  }
  return map[action] || action
}
