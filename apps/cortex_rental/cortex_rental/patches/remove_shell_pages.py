"""Remove the Desk Pages that only hosted the retired Vite screens.

Cortex is now native ERPNext (workspaces, lists, forms, reports) plus the `cortex-home` Page. Any Page of the
Cortex Rental module whose folder no longer exists in the app is a leftover record that would open an empty
screen, so it is deleted.
"""

import os

import frappe


def execute():
    page_dir = os.path.join(frappe.get_app_path("cortex_rental"), "cortex_rental", "page")
    for name in frappe.get_all("Page", filters={"module": "Cortex Rental"}, pluck="name"):
        folder = os.path.join(page_dir, name.replace("-", "_"))
        if not os.path.isdir(folder):
            frappe.delete_doc("Page", name, force=True, ignore_permissions=True)
