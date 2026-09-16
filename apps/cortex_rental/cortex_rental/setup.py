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
                "custom": 1,
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


def setup_cortex_sidebar() -> None:
    """
    Ensures that only the 'Cortex Rental' workspace is visible in the Frappe Desk sidebar.
    Hides all standard ERPNext and Frappe workspaces (Accounting, Buying, HR, etc.)
    by setting is_hidden = 1, and guarantees Cortex Rental has is_hidden = 0, public = 1,
    and sequence_id = 1.0.
    """
    if not frappe or not getattr(frappe, "db", None):
        return

    try:
        if frappe.db.table_exists("Workspace"):
            frappe.db.sql(
                """
                UPDATE `tabWorkspace`
                SET `is_hidden` = 1
                WHERE `name` != 'Cortex Rental'
                """
            )
            frappe.db.sql(
                """
                UPDATE `tabWorkspace`
                SET `is_hidden` = 0, `public` = 1, `sequence_id` = 1.0
                WHERE `name` = 'Cortex Rental'
                """
            )
            frappe.db.commit()
    except Exception:
        pass


def before_migrate() -> None:
    ensure_prerequisites()


def after_migrate() -> None:
    ensure_prerequisites()
    setup_cortex_sidebar()


def after_install() -> None:
    ensure_prerequisites()
    setup_cortex_sidebar()


def boot_session(bootinfo: Any = None) -> None:
    ensure_prerequisites()
    setup_cortex_sidebar()
    if bootinfo and isinstance(bootinfo, dict) and "allowed_workspaces" in bootinfo:
        # Keep only the dedicated Cortex workspaces; CORTEX_WORKSPACE_ORDER is the
        # single source of truth — match on both name and title for robustness.
        bootinfo["allowed_workspaces"] = [
            ws for ws in bootinfo["allowed_workspaces"]
            if ws.get("name") in CORTEX_WORKSPACE_ORDER
            or ws.get("title") in CORTEX_WORKSPACE_ORDER
        ]


# Ordered list of Cortex-dedicated workspaces — single source of truth for sidebar
# filtering in both boot_session and the get_cortex_workspace_sidebar_items override.
CORTEX_WORKSPACE_ORDER = [
    "Disponibilité",
    "Devis & Locations",
    "Check-in & Retours",
    "Parc Matériel",
    "Facturation & P&L",
    "Supervision & IA",
    "Cortex Rental",
]


if frappe:
    @frappe.whitelist()
    def get_cortex_workspace_sidebar_items() -> Dict[str, Any]:
        """
        Override of frappe.desk.desktop.get_workspace_sidebar_items.
        Registered via hooks.override_whitelisted_methods.

        Filters the sidebar items so that ONLY the dedicated Cortex workspaces
        (defined in CORTEX_WORKSPACE_ORDER) are presented in the Frappe Desk
        workspace sidebar. All generic ERPNext workspaces are hidden.
        """
        try:
            from frappe.desk.desktop import get_workspace_sidebar_items as _original
            sidebar = _original()
            if isinstance(sidebar, dict) and "pages" in sidebar:
                filtered = [
                    p for p in sidebar["pages"]
                    if p.get("name") in CORTEX_WORKSPACE_ORDER
                    or p.get("title") in CORTEX_WORKSPACE_ORDER
                ]

                def _sort_key(p: Dict[str, Any]) -> int:
                    label = p.get("title") or p.get("name") or ""
                    return CORTEX_WORKSPACE_ORDER.index(label) if label in CORTEX_WORKSPACE_ORDER else 99

                filtered.sort(key=_sort_key)
                sidebar["pages"] = filtered
            return sidebar
        except Exception:
            # Fallback: direct DB query when the core Frappe function is unavailable.
            pages = frappe.get_all(
                "Workspace",
                filters={"name": ["in", CORTEX_WORKSPACE_ORDER], "is_hidden": 0},
                fields=["name", "title", "for_user", "parent_page", "content", "public"],
                order_by="sequence_id asc",
            )
            return {"pages": pages}
else:
    def get_cortex_workspace_sidebar_items() -> Dict[str, Any]:  # type: ignore[misc]
        """No-op stub when Frappe is not installed (e.g. unit-test environments)."""
        return {"pages": []}
