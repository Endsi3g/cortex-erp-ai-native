// Single source of truth for business-state → {label, glyph, tokenPrefix}.
// Consumed by CortexStatusBadge.vue and CortexRiskBadge.vue so every
// screen renders the same color + icon + label for the same state
// instead of each page inventing its own mapping (see
// docs/design-system.md "États — wired vs. reserved").
//
// `wired: true` means an actual DocType value produces this state today
// (Cortex Rental Transaction.rental_state or Serial No.cortex_status).
// `wired: false` is defined for forward compatibility with the design
// spec but nothing in the backend emits it yet — CortexStatusBadge
// still renders it (so the component contract doesn't silently break
// when a real state arrives later), but callers should not present a
// `wired: false` state as something a user can currently reach.

export const STATE_META = {
	quote: { label: "Soumission", glyph: "○", tokenPrefix: "state-quote", wired: true },
	draft: { label: "Brouillon", glyph: "○", tokenPrefix: "state-draft", wired: false },
	reservation: { label: "Réservation", glyph: "●", tokenPrefix: "state-reservation", wired: true },
	contract: { label: "Contrat", glyph: "✓", tokenPrefix: "state-contract", wired: true },
	checked_out: { label: "Sorti", glyph: "↗", tokenPrefix: "state-checked-out", wired: true },
	partial_return: { label: "Retour partiel", glyph: "↗", tokenPrefix: "state-partial-return", wired: false },
	returned: { label: "Retourné", glyph: "✓", tokenPrefix: "state-returned", wired: true },
	invoice_prepared: { label: "Facture préparée", glyph: "✓", tokenPrefix: "state-invoice-prepared", wired: false },
	invoiced: { label: "Facturé", glyph: "✓", tokenPrefix: "state-invoiced", wired: false },
	closed: { label: "Clôturé", glyph: "✓", tokenPrefix: "state-closed", wired: true },
	cancelled: { label: "Annulé", glyph: "✕", tokenPrefix: "state-cancelled", wired: true },
	disputed: { label: "Contesté", glyph: "!", tokenPrefix: "state-disputed", wired: true },
	conflict: { label: "Conflit", glyph: "!", tokenPrefix: "state-conflict", wired: true },
	quarantine: { label: "Quarantaine", glyph: "!", tokenPrefix: "state-quarantine", wired: true },
	repair: { label: "En réparation", glyph: "!", tokenPrefix: "state-repair", wired: true },
	missing: { label: "Manquant", glyph: "?", tokenPrefix: "state-missing", wired: true },
};

// Maps the real values Frappe stores (rental_state / cortex_status) to
// the design-token keys above — kept separate from STATE_META itself so
// a doctype rename only changes one small table, not every component.
export const RENTAL_STATE_KEY = {
	Quote: "quote",
	Reservation: "reservation",
	Contract: "contract",
	"Checked Out": "checked_out",
	Returned: "returned",
	Closed: "closed",
	Cancelled: "cancelled",
	Disputed: "disputed",
	Quarantine: "quarantine",
};

export const SERIAL_STATUS_KEY = {
	Active: null, // no badge — "available" has no dedicated state token
	Quarantine: "quarantine",
	"Under Repair": "repair",
	Missing: "missing",
	Decommissioned: "cancelled",
};

export const RISK_META = {
	low: { label: "Risque faible", tokenPrefix: "state-returned" },
	medium: { label: "Risque moyen", tokenPrefix: "state-reservation" },
	high: { label: "Risque élevé", tokenPrefix: "state-conflict" },
};

export function stateKeyForRentalState(rentalState) {
	return RENTAL_STATE_KEY[rentalState] || null;
}

export function stateKeyForSerialStatus(cortexStatus) {
	return SERIAL_STATUS_KEY[cortexStatus] ?? null;
}
