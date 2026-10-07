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
        fields=["creation", "model", "user", "input_tokens", "output_tokens", "cost"],
        order_by="creation desc",
        limit_page_length=50000,
    )
    grouped = {}
    for r in rows:
        key = (str(r.creation)[:7], r.model, r.user)
        row = grouped.setdefault(key, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})
        row["calls"] += 1
        row["input_tokens"] += int(r.input_tokens or 0)
        row["output_tokens"] += int(r.output_tokens or 0)
        row["cost"] += flt(r.cost)
    data = [
        {"month": month, "model": model, "user": user, **values, "cost": flt(values["cost"], 4)}
        for (month, model, user), values in sorted(
            grouped.items(), key=lambda kv: (kv[0][0], kv[1]["cost"]), reverse=True
        )
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
