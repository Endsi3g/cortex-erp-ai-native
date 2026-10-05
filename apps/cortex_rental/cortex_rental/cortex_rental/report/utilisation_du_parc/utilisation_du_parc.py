"""Utilisation du parc : pour chaque équipement, les jours-unités loués, le taux d'utilisation, les revenus et le rendement.

Un équipement qui dort coûte de l'argent ; un équipement toujours sorti manque peut-être de remplaçants. Ce rapport montre où
acheter, où vendre et où ajuster le tarif. Les jours loués comptent les locations Contrat, Sorti, Retourné et Clos
(pas les devis ni les annulations) sur la période choisie.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime

COUNTED = ("Contract", "Checked Out", "Returned", "Closed")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    start = get_datetime(filters.get("from_date") or frappe.utils.add_days(frappe.utils.today(), -90))
    end = get_datetime(f"{filters.get('to_date') or frappe.utils.today()} 23:59:59")
    days_in_period = max(1.0, (end - start).total_seconds() / 86400.0)
    profiles = frappe.get_list(
        "Cortex Rental Item Profile",
        filters={"company": filters.company},
        fields=[
            "item_code",
            "item_name",
            "category",
            "total_quantity",
            "daily_rate",
            "replacement_value",
            "is_serialized",
        ],
        limit_page_length=1000,
    )
    transactions = {
        t.name: t
        for t in frappe.get_list(
            "Cortex Rental Transaction",
            filters={
                "company": filters.company,
                "rental_state": ["in", list(COUNTED)],
                "starts_at": ["<", end],
                "ends_at": [">", start],
            },
            fields=["name", "starts_at", "ends_at"],
            limit_page_length=0,
        )
    }
    lines = (
        frappe.get_list(
            "Cortex Rental Transaction Item",
            filters={"parent": ["in", list(transactions)]},
            parent_doctype="Cortex Rental Transaction",
            fields=["parent", "item_code", "qty", "amount"],
            limit_page_length=0,
        )
        if transactions
        else []
    )
    rows = [
        frappe._dict(**line, starts_at=transactions[line.parent].starts_at, ends_at=transactions[line.parent].ends_at)
        for line in lines
    ]
    used, revenue = {}, {}
    for r in rows:
        s, e = max(get_datetime(r.starts_at), start), min(get_datetime(r.ends_at), end)
        span = max(0.0, (e - s).total_seconds() / 86400.0)
        used[r.item_code] = used.get(r.item_code, 0.0) + span * flt(r.qty)
        full = max(1.0, (get_datetime(r.ends_at) - get_datetime(r.starts_at)).total_seconds() / 86400.0)
        revenue[r.item_code] = revenue.get(r.item_code, 0.0) + flt(r.amount) * (span / full)
    fleet_by_item = _fleet(filters.company, profiles)
    data = []
    for p in profiles:
        fleet = fleet_by_item.get(p.item_code, flt(p.total_quantity))
        capacity = fleet * days_in_period
        rented = used.get(p.item_code, 0.0)
        earned = revenue.get(p.item_code, 0.0)
        invested = flt(p.replacement_value) * fleet
        data.append(
            {
                "item_name": p.item_name or p.item_code,
                "category": p.category,
                "fleet": fleet,
                "rented_days": round(rented, 1),
                "utilization": round(rented / capacity * 100, 1) if capacity else 0.0,
                "revenue": round(earned, 2),
                "revenue_per_unit": round(earned / fleet, 2) if fleet else 0.0,
                "yield": round(earned / invested * 100, 1) if invested else 0.0,
                "advice": _advice(rented / capacity * 100 if capacity else 0.0, fleet),
            }
        )
    data.sort(key=lambda r: r["utilization"], reverse=True)
    return _columns(), data, None, _chart(data)


def _fleet(company, profiles):
    serialized = [p.item_code for p in profiles if p.is_serialized]
    if not serialized:
        return {}
    rows = frappe.get_list(
        "Serial No",
        filters={"company": company, "item_code": ["in", serialized], "cortex_status": ["!=", "Decommissioned"]},
        fields=["item_code", "count(name) as c"],
        group_by="item_code",
        limit_page_length=0,
    )
    return {row.item_code: flt(row.c) for row in rows}


def _advice(util, fleet):
    if fleet and util >= 80:
        return _("Très demandé : envisagez une unité de plus ou un tarif plus élevé")
    if fleet and util < 15:
        return _("Peu loué : revoir le tarif, le promouvoir ou vendre")
    return ""


def _chart(data):
    top = data[:10]
    return {
        "data": {
            "labels": [r["item_name"][:22] for r in top],
            "datasets": [{"name": _("Utilisation (%)"), "values": [r["utilization"] for r in top]}],
        },
        "type": "bar",
        "colors": ["#066336"],
    }


def _columns():
    return [
        {"fieldname": "item_name", "label": _("Équipement"), "fieldtype": "Data", "width": 240},
        {"fieldname": "category", "label": _("Catégorie"), "fieldtype": "Data", "width": 150},
        {"fieldname": "fleet", "label": _("Parc"), "fieldtype": "Int", "width": 70},
        {"fieldname": "rented_days", "label": _("Jours loués"), "fieldtype": "Float", "precision": 1, "width": 100},
        {"fieldname": "utilization", "label": _("Utilisation (%)"), "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "revenue", "label": _("Revenus ($)"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "revenue_per_unit", "label": _("Revenus par unité ($)"), "fieldtype": "Currency", "width": 140},
        {
            "fieldname": "yield",
            "label": _("Rendement (% de la valeur)"),
            "fieldtype": "Float",
            "precision": 1,
            "width": 150,
        },
        {"fieldname": "advice", "label": _("À noter"), "fieldtype": "Data", "width": 320},
    ]
