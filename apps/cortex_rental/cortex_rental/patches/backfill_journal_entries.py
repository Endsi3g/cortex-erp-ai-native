"""Generate the accounting entries of invoices and payments issued before the ledger existed (idempotent)."""

import frappe

from cortex_rental.services import ledger


def execute():
    for doctype in (
        "cortex_journal_entry_line",
        "cortex_journal_entry",
        "cortex_rental_invoice_line",
        "cortex_finance_settings",
    ):
        frappe.reload_doc("cortex_rental", "doctype", doctype)
    # Lignes émises avant l'existence de `line_kind` : on les classe d'après leur facture et leur description.
    frappe.db.sql(
        """UPDATE `tabCortex Rental Invoice Line` l JOIN `tabCortex Rental Invoice` i ON i.name = l.parent
           SET l.line_kind = CASE
               WHEN i.invoice_type = 'Deposit' THEN 'Deposit'
               WHEN l.description LIKE 'Frais de retard%%' THEN 'Late Fee'
               WHEN l.description LIKE 'Moins : acompte%%' THEN 'Deposit Credit'
               ELSE 'Rental' END
           WHERE l.parenttype = 'Cortex Rental Invoice'"""
    )
    for name in frappe.get_all("Cortex Rental Invoice", order_by="creation asc", pluck="name"):
        invoice = frappe.get_doc("Cortex Rental Invoice", name)
        ledger.post_invoice(invoice)
        if invoice.status == "Cancelled" and invoice.invoice_type == "Deposit":
            ledger.post_reversal(invoice)
    for name in frappe.get_all("Cortex Rental Payment", order_by="creation asc", pluck="name"):
        ledger.post_payment(frappe.get_doc("Cortex Rental Payment", name))
