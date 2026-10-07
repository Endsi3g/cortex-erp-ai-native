"""Valeurs de départ modifiables des abonnements (prix, devise, options, enveloppe d'IA, sociétés exemptées).

Une seule fois, et seulement si rien n'a jamais été configuré. La facturation reste désactivée : aucun frais n'est
possible avant qu'une personne confirme les prix et saisisse les identifiants de prix Stripe."""

import frappe


def execute():
    frappe.reload_doc("cortex_rental", "doctype", "cortex_subscription_item")
    frappe.reload_doc("cortex_rental", "doctype", "cortex_subscription_settings")
    from cortex_rental.services import subscriptions

    subscriptions.seed_defaults()
