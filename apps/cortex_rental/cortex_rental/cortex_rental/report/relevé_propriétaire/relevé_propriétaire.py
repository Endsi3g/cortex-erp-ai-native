"""Relevé propriétaire : lignes de versement d'un propriétaire. Aucune information client n'y figure (confidentialité)."""

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company") or not filters.get("owner"):
        frappe.throw(_("Choisissez la société et le propriétaire."))
    query = {"company": filters.company, "owner": filters.owner}
    if filters.get("from_date") and filters.get("to_date"):
        query["creation"] = ["between", [filters.from_date, f"{filters.to_date} 23:59:59"]]
    elif filters.get("from_date"):
        query["creation"] = [">=", filters.from_date]
    elif filters.get("to_date"):
        query["creation"] = ["<=", f"{filters.to_date} 23:59:59"]
    rows = frappe.get_list(
        "Consignment Payout",
        filters=query,
        fields=[
            "name",
            "serial_no",
            "status",
            "gross_amount",
            "discount_amount",
            "net_amount",
            "consignment_percentage",
            "owner_payout_amount",
            "paid_at",
        ],
        order_by="creation asc",
        limit_page_length=1000,
    )
    columns = [
        {
            "fieldname": "name",
            "label": _("Versement"),
            "fieldtype": "Link",
            "options": "Consignment Payout",
            "width": 190,
        },
        {
            "fieldname": "serial_no",
            "label": _("Numéro de série"),
            "fieldtype": "Link",
            "options": "Serial No",
            "width": 170,
        },
        {"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 110},
        {"fieldname": "gross_amount", "label": _("Brut"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "discount_amount", "label": _("Rabais"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "net_amount", "label": _("Net"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "consignment_percentage", "label": _("Part propriétaire"), "fieldtype": "Percent", "width": 140},
        {"fieldname": "owner_payout_amount", "label": _("À verser"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "paid_at", "label": _("Payé le"), "fieldtype": "Datetime", "width": 160},
    ]
    return columns, rows
