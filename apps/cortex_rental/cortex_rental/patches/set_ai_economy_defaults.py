"""Modèle économique de repli au plafond (docs/architecture/COUTS_API.md), seulement si rien n'est encore saisi."""

import frappe

DOCTYPE = "Cortex AI Settings"
VALUES = {
    "economy_model": "gemini-3.1-flash-lite",
    "economy_price_input_per_mtok": 0.25,
    "economy_price_output_per_mtok": 1.5,
    "economy_cap_percent": 150,
}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, value in VALUES.items():
        if not frappe.db.get_single_value(DOCTYPE, field):
            frappe.db.set_single_value(DOCTYPE, field, value)
