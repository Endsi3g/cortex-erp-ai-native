"""Prochains départs et retours : ce que l'entrepôt prépare et ce qui doit revenir, retards compris."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

DEPARTURE_STATES = ("Reservation", "Contract")


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    days = max(1, min(cint(filters.get("days") or 7), 90))
    kind = filters.get("kind") or ""
    now, horizon = now_datetime(), add_days(now_datetime(), days)
    fields = [
        "name",
        "customer",
        "project_name",
        "rental_state",
        "starts_at",
        "ends_at",
        "customer_account_ready",
        "insurance_ready",
        "payment_ready",
        "grand_total",
    ]
    rows = []
    if kind in ("", "Départs"):
        for row in frappe.get_list(
            "Cortex Rental Transaction",
            filters={
                "company": filters.company,
                "rental_state": ["in", DEPARTURE_STATES],
                "starts_at": ["between", [now, horizon]],
            },
            fields=fields,
            order_by="starts_at asc",
            limit_page_length=500,
        ):
            rows.append(_row(row, _("Départ"), row.starts_at))
    if kind in ("", "Retours"):
        for row in frappe.get_list(
            "Cortex Rental Transaction",
            filters={"company": filters.company, "rental_state": "Checked Out", "ends_at": ["<=", horizon]},
            fields=fields,
            order_by="ends_at asc",
            limit_page_length=500,
        ):
            late = row.ends_at < now
            rows.append(_row(row, _("En retard") if late else _("Retour"), row.ends_at))
    rows.sort(key=lambda r: r["when"])

    columns = [
        {"fieldname": "kind", "label": _("Type"), "fieldtype": "Data", "width": 100},
        {"fieldname": "when", "label": _("Date et heure"), "fieldtype": "Datetime", "width": 170},
        {
            "fieldname": "name",
            "label": _("Location"),
            "fieldtype": "Link",
            "options": "Cortex Rental Transaction",
            "width": 170,
        },
        {"fieldname": "customer", "label": _("Client"), "fieldtype": "Link", "options": "Customer", "width": 200},
        {"fieldname": "project_name", "label": _("Projet"), "fieldtype": "Data", "width": 200},
        {"fieldname": "rental_state", "label": _("État"), "fieldtype": "Data", "width": 120},
        {"fieldname": "ready", "label": _("Prêt à sortir"), "fieldtype": "Data", "width": 260},
        {"fieldname": "grand_total", "label": _("Total"), "fieldtype": "Currency", "width": 120},
    ]
    return columns, rows


def _row(row, kind, when):
    missing = []
    if not row.customer_account_ready:
        missing.append(_("compte client"))
    if not row.insurance_ready:
        missing.append(_("assurance"))
    if not row.payment_ready:
        missing.append(_("paiement"))
    return {
        "kind": kind,
        "when": when,
        "name": row.name,
        "customer": row.customer,
        "project_name": row.project_name,
        "rental_state": row.rental_state,
        "ready": _("Oui") if not missing else _("À compléter : {0}").format(", ".join(missing)),
        "grand_total": row.grand_total,
    }
