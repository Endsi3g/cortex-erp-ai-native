"""Vue 360° d'un client : tout ce que le système sait de lui, tiré des dossiers réels (locations, devis, factures).

Rien n'est estimé ni inventé. Chaque bloc respecte les droits de la personne connectée
(les montants de facturation ne sont lus que si elle a accès aux factures).
"""

from typing import Any, Dict

try:
    import frappe
    from frappe.utils import flt, getdate, today
except ImportError:
    frappe = None

TRANSACTION = "Cortex Rental Transaction"
ACTIVE_STATES = ("Reservation", "Contract", "Checked Out", "Partially Returned")


def summary(customer: str, company: str) -> Dict[str, Any]:
    if not frappe.db.exists("Customer", {"name": customer, "cortex_company": company}):
        frappe.throw("Ce client n'est pas disponible pour la société active.", frappe.PermissionError)
    if not frappe.has_permission("Customer", "read", customer):
        frappe.throw("Accès refusé à ce client.", frappe.PermissionError)

    result: Dict[str, Any] = {"customer": customer, "quotes": [], "active": [], "last_rental": None}
    if frappe.has_permission(TRANSACTION, "read"):
        rows = frappe.get_list(
            TRANSACTION,
            filters={"company": company, "customer": customer},
            fields=["name", "rental_state", "starts_at", "ends_at", "grand_total", "hold_status", "hold_until"],
            order_by="starts_at desc",
            limit_page_length=200,
        )
        result["rentals_count"] = len(rows)
        result["quotes"] = [
            {
                "name": r.name,
                "total": flt(r.grand_total, 2),
                "starts_at": str(r.starts_at),
                "hold_status": r.hold_status or "",
            }
            for r in rows
            if r.rental_state == "Quote"
        ][:10]
        result["active"] = [
            {"name": r.name, "state": r.rental_state, "starts_at": str(r.starts_at), "ends_at": str(r.ends_at)}
            for r in rows
            if r.rental_state in ACTIVE_STATES
        ][:10]
        past = [r for r in rows if r.rental_state in ("Returned", "Closed")]
        if past:
            result["last_rental"] = {"name": past[0].name, "ends_at": str(past[0].ends_at)}
        result["late_returns"] = sum(
            1
            for r in rows
            if r.rental_state in ("Checked Out", "Partially Returned")
            and r.ends_at
            and getdate(r.ends_at) < getdate(today())
        )

    if frappe.has_permission("Cortex Rental Invoice", "read"):
        invoices = frappe.get_list(
            "Cortex Rental Invoice",
            filters={"company": company, "customer": customer, "status": ["!=", "Cancelled"]},
            fields=["total", "balance", "status", "due_date"],
            limit_page_length=500,
        )
        open_rows = [i for i in invoices if i.status in ("Issued", "Partially Paid")]
        result["billing"] = {
            "billed_total": flt(sum(flt(i.total) for i in invoices), 2),
            "balance_due": flt(sum(flt(i.balance) for i in open_rows), 2),
            "open_invoices": len(open_rows),
            "overdue_invoices": sum(1 for i in open_rows if i.due_date and getdate(i.due_date) < getdate(today())),
        }
    return result
