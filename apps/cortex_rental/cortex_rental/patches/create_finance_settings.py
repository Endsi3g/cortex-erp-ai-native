"""Give every existing company its finance settings (Québec taxes, deposit, late-fee rule disabled)."""

import frappe

from cortex_rental.services import billing


def execute():
    frappe.reload_doc("cortex_rental", "doctype", "cortex_finance_settings")
    for company in frappe.get_all("Company", pluck="name"):
        billing.ensure_settings(company)
