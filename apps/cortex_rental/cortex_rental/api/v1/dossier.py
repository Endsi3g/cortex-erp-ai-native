"""Dossier relié d'une fiche (location, facture, paiement) : liens et historique. Voir services/dossier.py."""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services import defense
from cortex_rental.permissions.agent_scopes import require_human_staff_role
from cortex_rental.services import dossier

if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get(doctype: str, name: str):
        require_human_staff_role()
        return dossier.get(doctype, name)
