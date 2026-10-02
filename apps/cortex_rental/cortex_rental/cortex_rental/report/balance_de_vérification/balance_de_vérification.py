"""Balance de vérification : débits, crédits et solde par compte. Le total des débits égale toujours celui des crédits."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    conditions = {"company": filters.company}
    if filters.get("to_date"):
        conditions["posting_date"] = ["<=", filters.to_date]
    if filters.get("from_date"):
        conditions["posting_date"] = ["between", [filters.from_date, filters.get("to_date") or "2999-12-31"]]
    entries = frappe.get_list("Cortex Journal Entry", filters=conditions, pluck="name", limit_page_length=50000)
    totals = {}
    if entries:
        for line in frappe.get_all(
            "Cortex Journal Entry Line",
            filters={"parent": ["in", entries], "parenttype": "Cortex Journal Entry"},
            fields=["account_number", "account_name", "debit", "credit"],
            limit_page_length=200000,
        ):
            row = totals.setdefault(
                line.account_number,
                {"account_number": line.account_number, "account_name": line.account_name, "debit": 0.0, "credit": 0.0},
            )
            row["debit"] += flt(line.debit)
            row["credit"] += flt(line.credit)
    data = []
    for number in sorted(totals):
        row = totals[number]
        net = flt(row["debit"] - row["credit"], 2)
        data.append(
            {
                **row,
                "debit": flt(row["debit"], 2),
                "credit": flt(row["credit"], 2),
                "debit_balance": net if net > 0 else 0.0,
                "credit_balance": -net if net < 0 else 0.0,
            }
        )
    columns = [
        {"fieldname": "account_number", "label": _("Compte"), "fieldtype": "Data", "width": 90},
        {"fieldname": "account_name", "label": _("Nom du compte"), "fieldtype": "Data", "width": 240},
        {"fieldname": "debit", "label": _("Total des débits"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "credit", "label": _("Total des crédits"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "debit_balance", "label": _("Solde débiteur"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "credit_balance", "label": _("Solde créditeur"), "fieldtype": "Currency", "width": 150},
    ]
    return columns, data
