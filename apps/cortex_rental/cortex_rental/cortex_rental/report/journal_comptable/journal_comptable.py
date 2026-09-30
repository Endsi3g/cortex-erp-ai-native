"""Journal comptable : toutes les écritures d'une période, ligne par ligne, avec leur source (pour le comptable)."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    entries = frappe.get_list(
        "Cortex Journal Entry",
        filters={"company": filters.company, **_dates(filters)},
        fields=["name", "posting_date", "source_type", "source_name", "description", "rental_transaction"],
        order_by="posting_date asc, creation asc",
        limit_page_length=20000,
    )
    if not entries:
        return _columns(), []
    names = [e.name for e in entries]
    lines = frappe.get_all(
        "Cortex Journal Entry Line",
        filters={"parent": ["in", names], "parenttype": "Cortex Journal Entry"},
        fields=["parent", "account_number", "account_name", "debit", "credit", "idx"],
        order_by="parent asc, idx asc",
        limit_page_length=100000,
    )
    by_entry = {}
    for line in lines:
        by_entry.setdefault(line.parent, []).append(line)
    account = filters.get("account")
    data = []
    for entry in entries:
        for line in by_entry.get(entry.name, []):
            if account and line.account_number != account:
                continue
            data.append(
                {
                    "posting_date": entry.posting_date,
                    "entry": entry.name,
                    "source_type": _(entry.source_type),
                    "source": entry.source_name,
                    "rental": entry.rental_transaction,
                    "account_number": line.account_number,
                    "account_name": line.account_name,
                    "debit": flt(line.debit, 2),
                    "credit": flt(line.credit, 2),
                    "description": entry.description,
                }
            )
    return _columns(), data


def _dates(filters):
    if filters.get("from_date") and filters.get("to_date"):
        return {"posting_date": ["between", [filters.from_date, filters.to_date]]}
    if filters.get("from_date"):
        return {"posting_date": [">=", filters.from_date]}
    if filters.get("to_date"):
        return {"posting_date": ["<=", filters.to_date]}
    return {}


def _columns():
    return [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
        {
            "fieldname": "entry",
            "label": _("Écriture"),
            "fieldtype": "Link",
            "options": "Cortex Journal Entry",
            "width": 130,
        },
        {"fieldname": "source_type", "label": _("Type"), "fieldtype": "Data", "width": 90},
        {"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 130},
        {
            "fieldname": "rental",
            "label": _("Location"),
            "fieldtype": "Link",
            "options": "Cortex Rental Transaction",
            "width": 140,
        },
        {"fieldname": "account_number", "label": _("Compte"), "fieldtype": "Data", "width": 80},
        {"fieldname": "account_name", "label": _("Nom du compte"), "fieldtype": "Data", "width": 200},
        {"fieldname": "debit", "label": _("Débit"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "credit", "label": _("Crédit"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 320},
    ]
