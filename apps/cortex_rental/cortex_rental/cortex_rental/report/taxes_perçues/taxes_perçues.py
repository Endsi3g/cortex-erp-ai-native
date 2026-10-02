"""Taxes perçues par mois (TPS et TVQ facturées, factures annulées exclues) : base de la déclaration de taxes."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    conditions = {"company": filters.company, "status": ["!=", "Cancelled"]}
    if filters.get("from_date"):
        conditions["issue_date"] = [">=", filters.from_date]
    if filters.get("to_date"):
        conditions["issue_date"] = ["between", [filters.get("from_date") or "2000-01-01", filters.to_date]]
    invoices = frappe.get_list(
        "Cortex Rental Invoice",
        filters=conditions,
        fields=["issue_date", "subtotal", "tps_amount", "tvq_amount", "total"],
        limit_page_length=50000,
    )
    months = {}
    for inv in invoices:
        key = str(inv.issue_date)[:7]
        row = months.setdefault(
            key, {"month": key, "invoices": 0, "subtotal": 0.0, "tps": 0.0, "tvq": 0.0, "total": 0.0}
        )
        row["invoices"] += 1
        row["subtotal"] += flt(inv.subtotal)
        row["tps"] += flt(inv.tps_amount)
        row["tvq"] += flt(inv.tvq_amount)
        row["total"] += flt(inv.total)
    data = []
    for key in sorted(months, reverse=True):
        row = months[key]
        data.append(
            {
                **{k: (flt(v, 2) if k not in ("month", "invoices") else v) for k, v in row.items()},
                "to_remit": flt(row["tps"] + row["tvq"], 2),
            }
        )
    columns = [
        {"fieldname": "month", "label": _("Mois"), "fieldtype": "Data", "width": 110},
        {"fieldname": "invoices", "label": _("Factures"), "fieldtype": "Int", "width": 100},
        {"fieldname": "subtotal", "label": _("Sous-total"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "tps", "label": _("TPS"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "tvq", "label": _("TVQ"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "to_remit", "label": _("Taxes à remettre"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "total", "label": _("Total facturé"), "fieldtype": "Currency", "width": 140},
    ]
    return columns, data
