"""Utilisation de l'IA : appels, jetons et coût par mois, modèle et personne, avec le plafond de la société."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    conditions = {"company": filters.company}
    if filters.get("from_date") and filters.get("to_date"):
        conditions["creation"] = ["between", [filters.from_date, f"{filters.to_date} 23:59:59"]]
    rows = frappe.get_list(
        "Cortex AI Usage",
        filters=conditions,
        fields=[
            "date_format(creation, '%%Y-%%m') as month",
            "model",
            "user",
            "count(name) as calls",
            "sum(input_tokens) as input_tokens",
            "sum(output_tokens) as output_tokens",
            "sum(cost) as cost",
        ],
        group_by="date_format(creation, '%%Y-%%m'), model, user",
        order_by="month desc, cost desc",
        limit_page_length=1000,
    )
    data = [
        {
            "month": r.month,
            "model": r.model,
            "user": r.user,
            "calls": int(r.calls or 0),
            "input_tokens": int(r.input_tokens or 0),
            "output_tokens": int(r.output_tokens or 0),
            "cost": flt(r.cost, 4),
        }
        for r in rows
    ]
    return _columns(), data


def _columns():
    return [
        {"fieldname": "month", "label": _("Mois"), "fieldtype": "Data", "width": 90},
        {"fieldname": "model", "label": _("Modèle"), "fieldtype": "Data", "width": 160},
        {"fieldname": "user", "label": _("Utilisateur"), "fieldtype": "Link", "options": "User", "width": 200},
        {"fieldname": "calls", "label": _("Appels"), "fieldtype": "Int", "width": 90},
        {"fieldname": "input_tokens", "label": _("Jetons en entrée"), "fieldtype": "Int", "width": 130},
        {"fieldname": "output_tokens", "label": _("Jetons en sortie"), "fieldtype": "Int", "width": 130},
        {"fieldname": "cost", "label": _("Coût ($)"), "fieldtype": "Currency", "precision": 4, "width": 110},
    ]
