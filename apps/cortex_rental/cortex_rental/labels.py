"""French labels for stored English values, for messages shown to people (the stored values never change)."""

RENTAL_STATES = {
    "Quote": "Devis",
    "Reservation": "Réservation",
    "Contract": "Contrat",
    "Checked Out": "Sorti",
    "Returned": "Retourné",
    "Closed": "Clos",
    "Cancelled": "Annulé",
    "Disputed": "Litige",
    "Quarantine": "Quarantaine",
}

APPROVAL_STATES = {"Pending": "En attente", "Approved": "Approuvée", "Rejected": "Refusée", "Expired": "Expirée"}


def state_label(state):
    """French label of a rental state (falls back to the stored value)."""
    return RENTAL_STATES.get(state, state)


def approval_label(status):
    return APPROVAL_STATES.get(status, status)
