"""Disponibilité du parc : capacité, indisponibilités et réservations par équipement sur une période.

Les quantités viennent d'AvailabilityService (la même règle que la création de location) : ce rapport ne recalcule rien.
Les profils affichés respectent les permissions et la société de la personne.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from cortex_rental.services.availability import AvailabilityService


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Choisissez une société."))
    from_date = getdate(filters.get("from_date") or today())
    to_date = getdate(filters.get("to_date") or add_days(today(), 7))
    if to_date < from_date:
        frappe.throw(_("La date de fin doit suivre la date de début."))

    profile_filters = {"company": filters.company}
    if filters.get("category"):
        profile_filters["category"] = filters.category
    profiles = frappe.get_list(
        "Cortex Rental Item Profile",
        filters=profile_filters,
        fields=["item_code", "item_name", "category"],
        order_by="category asc, item_name asc",
        limit_page_length=500,
    )
    starts_at, ends_at = f"{from_date} 00:00:00", f"{to_date} 23:59:59"
    service = AvailabilityService()
    rows = []
    for profile in profiles:
        result = service.check(filters.company, starts_at, ends_at, [{"item_id": profile.item_code, "quantity": 1}])[0]
        available = float(result["available_quantity"])
        fleet = float(result["total_fleet_quantity"])
        rows.append(
            {
                "item_code": profile.item_code,
                "item_name": profile.item_name,
                "category": profile.category,
                "fleet": fleet,
                "unavailable": float(result["unavailable_status_quantity"]),
                "reserved": float(result["reserved_quantity"]),
                "available": available,
                "status": _("Complet")
                if available <= 0
                else _("Limité")
                if fleet and available / fleet <= 0.25
                else _("Disponible"),
            }
        )

    columns = [
        {"fieldname": "item_code", "label": _("Équipement"), "fieldtype": "Link", "options": "Item", "width": 160},
        {"fieldname": "item_name", "label": _("Nom"), "fieldtype": "Data", "width": 240},
        {"fieldname": "category", "label": _("Catégorie"), "fieldtype": "Data", "width": 170},
        {"fieldname": "fleet", "label": _("Parc"), "fieldtype": "Float", "width": 90},
        {"fieldname": "unavailable", "label": _("Indisponible"), "fieldtype": "Float", "width": 110},
        {"fieldname": "reserved", "label": _("Réservé"), "fieldtype": "Float", "width": 100},
        {"fieldname": "available", "label": _("Disponible"), "fieldtype": "Float", "width": 110},
        {"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 110},
    ]
    chart = {
        "data": {
            "labels": [row["item_name"] or row["item_code"] for row in rows[:12]],
            "datasets": [
                {"name": _("Réservé"), "values": [row["reserved"] for row in rows[:12]]},
                {"name": _("Disponible"), "values": [row["available"] for row in rows[:12]]},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": 1},
        "colors": ["#b45309", "#066336"],
    }
    message = _("Période du {0} au {1}. Les réservations bloquantes sont : réservation, contrat, sortie.").format(
        from_date, to_date
    )
    return columns, rows, message, chart
