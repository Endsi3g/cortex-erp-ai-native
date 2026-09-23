import type { ApprovalRequestItem, AiDraftItem, InboundRequestItem } from '@/api/contracts'

export type AiWorkType = 'inbound' | 'draft' | 'approval'
export type AiWorkState = 'processing' | 'ready' | 'low_confidence' | 'needs_review' | 'validated' | 'rejected' | 'applied' | 'extraction_error' | 'dismissed' | 'expired' | 'edited' | 'superseded'

export interface AiWorkItem {
  id: string
  sourceId: string
  type: AiWorkType
  title: string
  summary: string
  customer: string
  agent: string
  state: AiWorkState
  confidence: number | null
  priority: 'low' | 'normal' | 'high' | 'urgent'
  createdAt: string
  source: InboundRequestItem | AiDraftItem | ApprovalRequestItem
}

export function toAiWorkItem(source: InboundRequestItem | AiDraftItem | ApprovalRequestItem, type: AiWorkType): AiWorkItem {
  if (type === 'inbound') {
    const item = source as InboundRequestItem
    const confidence = item.overall_confidence
    return {
      id: `${type}:${item.id}`, sourceId: item.id, type,
      title: item.subject,
      summary: item.extracted_fields.missing_fields.length
        ? `${item.extracted_fields.missing_fields.length} information(s) à confirmer`
        : `${item.extracted_fields.equipment_mentions?.length ?? 0} équipement(s) détecté(s)`,
      customer: item.extracted_fields.customer_name || item.sender_name || item.sender_email,
      agent: 'Intake documentaire',
      state: confidence < 0.7 ? 'low_confidence' : item.status === 'new' ? 'needs_review' : item.status === 'converted' ? 'applied' : item.status === 'dismissed' ? 'dismissed' : 'ready',
      confidence, priority: confidence < 0.7 ? 'high' : item.extracted_fields.missing_fields.length ? 'normal' : 'low',
      createdAt: item.received_at, source: item
    }
  }

  if (type === 'draft') {
    const item = source as AiDraftItem
    const confidence = item.confidence_score
    return {
      id: `${type}:${item.id}`, sourceId: item.id, type,
      title: item.title,
      summary: item.draft_type,
      customer: String(item.proposed_payload.customer_name || item.target_name || 'Client à confirmer'),
      agent: 'Assistant devis',
      state: confidence < 0.7 ? 'low_confidence' : item.status === 'accepted' ? 'validated' : item.status === 'rejected' ? 'rejected' : item.status === 'submitted_approval' ? 'needs_review' : 'ready',
      confidence, priority: confidence < 0.7 ? 'high' : 'normal',
      createdAt: item.created_at, source: item
    }
  }

  const item = source as ApprovalRequestItem
  return {
    id: `${type}:${item.id}`, sourceId: item.id, type,
    title: item.title,
    summary: item.description,
    customer: item.reference_name,
    agent: item.requested_by_type === 'Agent' ? 'Agent métier' : item.requested_by,
    state: item.status === 'pending' ? 'needs_review' : item.status === 'approved' ? 'validated' : item.status === 'expired' ? 'expired' : 'rejected',
    // Approval records carry no model confidence. Never convert a human workflow
    // state into an invented 100% AI confidence score.
    confidence: null, priority: item.status === 'pending' ? 'high' : 'normal',
    createdAt: item.created_at, source: item
  }
}

export const aiStateLabels: Record<AiWorkState, string> = {
  processing: 'En traitement', ready: 'Prête', low_confidence: 'Confiance faible', needs_review: 'À réviser',
  validated: 'Validée', rejected: 'Refusée', applied: 'Appliquée', extraction_error: "Erreur d’extraction",
  dismissed: 'Ignorée', expired: 'Expirée', edited: 'Modifiée par un humain', superseded: 'Remplacée'
}
