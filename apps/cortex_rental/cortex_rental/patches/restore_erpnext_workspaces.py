"""Un-hide the ERPNext workspaces that earlier Cortex versions hid.

`setup.setup_cortex_sidebar()` used to run `UPDATE tabWorkspace SET is_hidden = 1`
for every workspace except "Cortex Rental" on each session boot. The Desk sidebar
now keeps ERPNext areas visible next to the Cortex groups, so restore the ones the
product exposes. Only the workspaces listed below are touched, and only when they
exist; everything else keeps whatever visibility an administrator chose.
"""

import frappe

ERPNEXT_WORKSPACES = (
    "Accounting",
    "Stock",
    "Selling",
    "Buying",
    "Projects",
    "ERPNext Settings",
)


def execute():
    for name in ERPNEXT_WORKSPACES:
        if frappe.db.exists("Workspace", name):
            frappe.db.set_value("Workspace", name, "is_hidden", 0, update_modified=False)
