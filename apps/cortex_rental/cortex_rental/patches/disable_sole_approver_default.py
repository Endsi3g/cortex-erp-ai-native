"""L'auto-approbation du propriétaire seul est désactivée par défaut : on remet à zéro ce qui avait été activé par défaut."""

import frappe


def execute():
    if not frappe.db.exists("DocType", "Cortex Finance Settings"):
        return
    frappe.reload_doc("cortex_rental", "doctype", "cortex_finance_settings")
    frappe.db.sql("UPDATE `tabCortex Finance Settings` SET allow_sole_approver_self_approval = 0")
