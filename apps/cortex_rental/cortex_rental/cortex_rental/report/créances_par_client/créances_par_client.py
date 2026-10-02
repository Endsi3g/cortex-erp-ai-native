"""Créances par client : soldes des factures ouvertes, classés selon le retard sur l'échéance."""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

BUCKETS = (
    ("not_due", "Non échu"),
    ("d1_30", "1 à 30 jours"),
    ("d31_60", "31 à 60 jours"),
    ("d61_90", "61 à 90 jours"),
    ("d91", "Plus de 90 jours"),
)


def bucket(days_late: int) -> str:
    if days_late <= 0:
        return "not_due"
    if days_late <= 30:
        return "d1_30"
    if days_late <= 60:
        return "d31_60"
    if days_late <= 90:
        return "d61_90"
    return "d91"


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    as_of = getdate(filters.get("as_of") or today())
    invoices = frappe.get_list(
        "Cortex Rental Invoice",
        filters={"company": filters.company, "status": ["in", ("Issued", "Partially Paid")], "balance": [">", 0]},
        fields=["customer", "due_date", "issue_date", "balance"],
        limit_page_length=5000,
    )
    per_customer = {}
    for inv in invoices:
        row = per_customer.setdefault(
            inv.customer, {"customer": inv.customer, "invoices": 0, "balance": 0.0, **{key: 0.0 for key, _ in BUCKETS}}
        )
        row["invoices"] += 1
        row["balance"] = flt(row["balance"] + flt(inv.balance), 2)
        key = bucket(date_diff(as_of, inv.due_date or inv.issue_date))
        row[key] = flt(row[key] + flt(inv.balance), 2)
    data = sorted(per_customer.values(), key=lambda r: -r["balance"])
    columns = [
        {"fieldname": "customer", "label": _("Client"), "fieldtype": "Link", "options": "Customer", "width": 260},
        {"fieldname": "invoices", "label": _("Factures ouvertes"), "fieldtype": "Int", "width": 130},
        {"fieldname": "balance", "label": _("Solde total"), "fieldtype": "Currency", "width": 140},
    ] + [{"fieldname": key, "label": _(label), "fieldtype": "Currency", "width": 130} for key, label in BUCKETS]
    return columns, data
