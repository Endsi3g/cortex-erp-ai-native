"""Délais d'attente des niveaux Gemma (90 s) et Local (600 s), seulement si rien n'a jamais été saisi."""

import frappe

DOCTYPE = "Cortex AI Settings"
VALUES = {"tier_gemma_timeout_seconds": 90, "tier_local_timeout_seconds": 600}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, value in VALUES.items():
        stored = frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field=%s", (DOCTYPE, field))
        if not stored:
            frappe.db.set_single_value(DOCTYPE, field, value)
