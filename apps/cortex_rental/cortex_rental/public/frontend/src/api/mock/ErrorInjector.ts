import type { MutationResponse } from '../contracts'

export class ErrorInjector {
  private static forcedError: string | null = null

  public static setForcedError(errorType: 'stale' | 'policy_denied' | 'conflict' | 'failed' | null) {
    this.forcedError = errorType
  }

  public static checkAndInject(requestId: string): MutationResponse | null {
    if (!this.forcedError) return null

    const err = this.forcedError
    this.forcedError = null // one-time trigger

    if (err === 'stale') {
      return {
        request_id: requestId,
        status: 'stale',
        stale_context: true,
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'STALE_STATE', message: 'Les données ont été modifiées par un autre utilisateur. Veuillez actualiser.' }]
      }
    }

    if (err === 'policy_denied') {
      return {
        request_id: requestId,
        status: 'policy_denied',
        approval_required: false,
        mutation_performed: false,
        policy_result: {
          policy_name: 'Insurance Minimum Requirement',
          policy_version: 'v2.0',
          explanation: 'Attestation d’assurance invalide ou manquante.',
          next_allowed_action: 'Soumettre une demande de dérogation au superviseur.'
        },
        errors: [{ code: 'POLICY_BLOCKED', message: 'Action bloquée par la politique d’assurance.' }]
      }
    }

    if (err === 'conflict') {
      return {
        request_id: requestId,
        status: 'conflict',
        approval_required: false,
        mutation_performed: false,
        errors: [{ code: 'AVAILABILITY_CONFLICT', message: 'Conflit de réservation sur la période demandée.' }]
      }
    }

    return {
      request_id: requestId,
      status: 'failed',
      approval_required: false,
      mutation_performed: false,
      errors: [{ code: 'INTERNAL_ERROR', message: 'Erreur inattendue lors de l’exécution.' }]
    }
  }
}
