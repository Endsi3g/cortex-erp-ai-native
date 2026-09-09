"""
Cortex Rental - Schema Prerequisites & Setup Hooks

Ensures required DocTypes (Company, Customer, Item, Serial No) exist in the Frappe
database. When ERPNext is installed, ERPNext provides full authoritative versions of
these DocTypes. When running in a standalone Frappe environment or test bench without
ERPNext, this module provisions minimal DocType stubs and default records so that Link
fields, permission checks, and availability queries never fail with 'Missing DocType' or
pymysql TableMissingError.
"""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None


def _ensure_doctype_stub(doctype_name: str, fields: List[Dict[str, Any]], module: str = "Cortex Rental") -> None:
    if not frappe or not getattr(frappe, "db", None):
        return

    try:
        if frappe.db.exists("DocType", doctype_name):
            return

        doc = frappe.get_doc(
            {
                "doctype": "DocType",
                "name": doctype_name,
                "module": module,
                "custom": 0,
                "is_submittable": 0,
                "fields": fields,
                "permissions": [
                    {"role": "System Manager", "read": 1, "write": 1, "create": 1},
                    {"role": "All", "read": 1},
                ],
            }
        )
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        # Fall back silently if another worker or concurrent process created it
        pass


def ensure_prerequisites() -> None:
    """
    Ensure all prerequisite DocTypes and records exist.
    """
    if not frappe or not getattr(frappe, "db", None):
        return

    # 1. Company stub
    if not frappe.db.exists("DocType", "Company"):
        _ensure_doctype_stub(
            doctype_name="Company",
            fields=[
                {"fieldname": "company_name", "label": "Company Name", "fieldtype": "Data", "reqd": 1},
                {"fieldname": "default_currency", "label": "Default Currency", "fieldtype": "Data", "default": "CAD"},
                {"fieldname": "country", "label": "Country", "fieldtype": "Data", "default": "Canada"},
            ],
        )

    # Ensure default company record exists
    try:
        if frappe.db.table_exists("Company") and not frappe.db.exists("Company", "CineRental Montreal"):
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "name": "CineRental Montreal",
                    "company_name": "CineRental Montreal",
                    "default_currency": "CAD",
                    "country": "Canada",
                }
            ).insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        pass

    # 2. Customer stub
    if not frappe.db.exists("DocType", "Customer"):
        _ensure_doctype_stub(
            doctype_name="Customer",
            fields=[
                {"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Data", "reqd": 1},
                {"fieldname": "cortex_company", "label": "Company", "fieldtype": "Link", "options": "Company"},
            ],
        )

    # 3. Item stub
    if not frappe.db.exists("DocType", "Item"):
        _ensure_doctype_stub(
            doctype_name="Item",
            fields=[
                {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "reqd": 1},
                {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data"},
                {"fieldname": "item_group", "label": "Item Group", "fieldtype": "Data"},
            ],
        )

    # 4. Serial No stub
    if not frappe.db.exists("DocType", "Serial No"):
        _ensure_doctype_stub(
            doctype_name="Serial No",
            fields=[
                {"fieldname": "serial_no", "label": "Serial No", "fieldtype": "Data", "reqd": 1},
                {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link", "options": "Item"},
                {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company"},
                {
                    "fieldname": "cortex_status",
                    "label": "Cortex Rental Status",
                    "fieldtype": "Select",
                    "options": "Active\nQuarantine\nUnder Repair\nMissing\nDecommissioned",
                    "default": "Active",
                },
                {"fieldname": "cortex_ownership", "label": "Ownership", "fieldtype": "Select", "options": "Owned\nConsignment", "default": "Owned"},
            ],
        )


def before_migrate() -> None:
    ensure_prerequisites()


def after_migrate() -> None:
    ensure_prerequisites()


def after_install() -> None:
    ensure_prerequisites()


def boot_session(bootinfo: Any = None) -> None:
    ensure_prerequisites()
