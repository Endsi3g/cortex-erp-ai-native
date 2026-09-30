"""Show translated names for records that are referenced by name and stored in English.

Frappe's `translated_doctype` setting makes Link fields and list columns display `__(name)`, so standard roles, print
formats, notifications and similar records appear in French without being renamed (their stored names, which code
relies on, never change).
"""

import frappe

DOCTYPES = (
    "Role",
    "Print Format",
    "Report",
    "Notification",
    "Designation",
    "Lead Source",
    "Project Type",
    "Warehouse Type",
    "Print Style",
    "Module Def",
    "Energy Point Rule",
    "UOM",
)


def execute():
    for doctype in DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        if not frappe.get_meta(doctype).get("translated_doctype"):
            frappe.make_property_setter(
                {
                    "doctype": doctype,
                    "doctype_or_field": "DocType",
                    "property": "translated_doctype",
                    "property_type": "Check",
                    "value": "1",
                },
                is_system_generated=False,
            )
    frappe.clear_cache()
