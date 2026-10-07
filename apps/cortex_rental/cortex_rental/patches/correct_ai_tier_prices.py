"""Corrige les prix par million de jetons des niveaux Équilibré et Avancé (vérifiés sur la page tarifaire d'Anthropic le
2026-10-07 : Sonnet 5.5 = 2 $ / 10 $, Opus 5.5 = 4 $ / 20 $). Les anciens défauts (3 $ / 15 $ et 15 $ / 75 $)
surestimaient la dépense dans le budget IA. Une valeur que quelqu'un a saisie à la main n'est jamais touchée."""

import frappe

DOCTYPE = "Cortex AI Settings"
OLD_NEW = {
    "tier_equilibre_price_input": (3.0, 2.0),
    "tier_equilibre_price_output": (15.0, 10.0),
    "tier_avance_price_input": (15.0, 4.0),
    "tier_avance_price_output": (75.0, 20.0),
}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, (old, new) in OLD_NEW.items():
        current = frappe.db.get_single_value(DOCTYPE, field)
        if current is not None and float(current or 0) == old:
            frappe.db.set_single_value(DOCTYPE, field, new)
