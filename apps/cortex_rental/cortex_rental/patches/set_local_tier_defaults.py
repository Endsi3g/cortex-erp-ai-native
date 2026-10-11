"""Niveau Cortex Local (Gemma 4 qui tourne chez nous, Docker Model Runner) : valeurs de départ, seulement si rien n'a jamais été
saisi (une case jamais enregistrée se lit « 0 »). Le niveau n'est offert que si la clé de site `cortex_ai_local_base_url` est réglée."""

import frappe

DOCTYPE = "Cortex AI Settings"
VALUES = {
    "tier_local_enabled": 1,
    "tier_local_model": "ai/gemma4",
    "tier_local_price_input": 0,
    "tier_local_price_output": 0,
}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, value in VALUES.items():
        stored = frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field=%s", (DOCTYPE, field))
        if not stored:
            frappe.db.set_single_value(DOCTYPE, field, value)
