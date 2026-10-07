"""Prix de gemini-3.8-flash et plafond mensuel proposé (docs/architecture/COUTS_API.md), seulement si rien n'est encore saisi."""

import frappe

DOCTYPE = "Cortex AI Settings"
VALUES = {"price_input_per_mtok": 0.75, "price_output_per_mtok": 3.75, "default_monthly_budget": 60.0}


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_ai_settings")
    for field, value in VALUES.items():
        current = frappe.db.get_single_value(DOCTYPE, field)
        if not current:
            frappe.db.set_single_value(DOCTYPE, field, value)
    if not frappe.db.get_single_value(DOCTYPE, "model"):
        frappe.db.set_single_value(DOCTYPE, "model", "gemini-3.8-flash")
