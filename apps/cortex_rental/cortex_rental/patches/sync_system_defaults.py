"""Bring the global defaults in line with System Settings and give every tenant user their company by default.

System Settings only copies a value into the global defaults when it changes through the form, so values written
during setup stayed stale (date format, language). Reports also start empty when a person's default company is not
their own company.
"""

import frappe
from frappe.model import no_value_fields


def execute():
    settings = frappe.get_single("System Settings")
    for df in settings.meta.get("fields"):
        value = settings.get(df.fieldname)
        if df.fieldtype not in no_value_fields and value not in (None, ""):
            frappe.db.set_default(df.fieldname, value)

    users = {}
    for row in frappe.get_all("User Permission", filters={"allow": "Company"}, fields=["name", "user", "for_value"]):
        users.setdefault(row.user, []).append(row)
    for rows in users.values():
        if len(rows) == 1:
            frappe.db.set_value("User Permission", rows[0].name, "is_default", 1)
