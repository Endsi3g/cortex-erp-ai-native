"""Activité des clients : locations, locations en cours et total, calculés sur les transactions Cortex."""

import frappe
from frappe import _

ACTIVE_STATES = ("Reservation", "Contract", "Checked Out")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    base = {"company": filters.company, "rental_state": ["not in", ("Quote", "Cancelled")]}
    if filters.get("from_date"):
        base["starts_at"] = [">=", filters.from_date]
    totals = frappe.get_list(
        "Cortex Rental Transaction",
        filters=base,
        fields=["customer", "count(name) as rentals", "sum(grand_total) as total", "max(starts_at) as last_start"],
        group_by="customer",
        order_by="total desc",
        limit_page_length=500,
    )
    active = {
        row.customer: row.active
        for row in frappe.get_list(
            "Cortex Rental Transaction",
            filters={**base, "rental_state": ["in", ACTIVE_STATES]},
            fields=["customer", "count(name) as active"],
            group_by="customer",
            limit_page_length=500,
        )
    }
    rows = [
        {
            "customer": r.customer,
            "rentals": r.rentals,
            "active": active.get(r.customer, 0),
            "total": r.total,
            "last_start": r.last_start,
        }
        for r in totals
    ]
    columns = [
        {"fieldname": "customer", "label": _("Client"), "fieldtype": "Link", "options": "Customer", "width": 240},
        {"fieldname": "rentals", "label": _("Locations"), "fieldtype": "Int", "width": 110},
        {"fieldname": "active", "label": _("En cours"), "fieldtype": "Int", "width": 110},
        {"fieldname": "total", "label": _("Total (TTC)"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "last_start", "label": _("Dernier départ"), "fieldtype": "Datetime", "width": 170},
    ]
    chart = {
        "data": {
            "labels": [r["customer"] for r in rows[:10]],
            "datasets": [{"name": _("Total (TTC)"), "values": [r["total"] or 0 for r in rows[:10]]}],
        },
        "type": "bar",
        "colors": ["#066336"],
    }
    return columns, rows, None, chart
