"""Niveau Cortex Gemma (Gemma 4 par l'API Gemini) : valeurs de départ, seulement si rien n'a jamais été saisi.

Une case à cocher d'un réglage unique jamais enregistré se lit « 0 » : sans ce patch, le niveau (activé par défaut) resterait
éteint sur les sites existants. Les prix restent à 0 : le tarif n'est pas confirmé (voir settings.VERIFIED_MODELS)."""

import frappe

DOCTYPE = "Cortex AI Settings"
VALUES = {
    "tier_gemma_enabled": 1,
    "tier_gemma_model": "gemma-4-26b-a4b-it",
    "tier_gemma_price_input": 0,
    "tier_gemma_price_output": 0,
}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, value in VALUES.items():
        stored = frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field=%s", (DOCTYPE, field))
        if not stored:
            frappe.db.set_single_value(DOCTYPE, field, value)
