"""Versements de consignation par propriétaire et par état (montants calculés par le serveur, jamais recalculés ici)."""

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    query = {"company": filters.company}
    if filters.get("status"):
        query["status"] = filters.status
    rows = frappe.get_list(
        "Consignment Payout",
        filters=query,
        fields=[
            "`owner` as owner_ref",
            "status",
            "count(name) as payouts",
            "sum(gross_amount) as gross",
            "sum(discount_amount) as discount",
            "sum(net_amount) as net",
            "sum(owner_payout_amount) as payout",
        ],
        group_by="`owner`, status",
        order_by="payout desc",
        limit_page_length=500,
    )
    columns = [
        {
            "fieldname": "owner_ref",
            "label": _("Propriétaire"),
            "fieldtype": "Link",
            "options": "Consignment Owner",
            "width": 220,
        },
        {"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 120},
        {"fieldname": "payouts", "label": _("Versements"), "fieldtype": "Int", "width": 110},
        {"fieldname": "gross", "label": _("Brut"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "discount", "label": _("Rabais"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "net", "label": _("Net"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "payout", "label": _("À verser au propriétaire"), "fieldtype": "Currency", "width": 190},
    ]
    return columns, rows
