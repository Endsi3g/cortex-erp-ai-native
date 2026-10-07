"""Formats d'impression intégrés de la facture (A4 en priorité, Lettre en choix) : on les charge et, si personne n'a
choisi de format par défaut, on retient « Facture Cortex A4 ». Un choix existant n'est jamais écrasé."""

import frappe

DOCTYPE = "Cortex Rental Invoice"
DEFAULT = "Facture Cortex A4"


def execute():
    frappe.reload_doc("cortex_rental", "print_format", "facture_cortex_a4")
    frappe.reload_doc("cortex_rental", "print_format", "facture_cortex_lettre")
    if not frappe.db.exists("DocType", DOCTYPE) or not frappe.db.exists("Print Format", DEFAULT):
        return
    if frappe.db.get_value("DocType", DOCTYPE, "default_print_format"):
        return
    frappe.make_property_setter(
        {
            "doctype": DOCTYPE,
            "doctype_or_field": "DocType",
            "property": "default_print_format",
            "value": DEFAULT,
            "property_type": "Data",
        }
    )
