"""Remove the Desk Pages that a Workspace of the same slug made unreachable.

`cortex-operations` and `cortex-rental` were registered as Pages, but Workspaces with those slugs
(the "Cortex Operations" group and the "Cortex Rental" hub) always take the route. The screens now
live in `cortex-ops-overview` and `cortex-rental-detail`; drop the stale Page records.
"""

import frappe

SHADOWED_PAGES = ("cortex-operations", "cortex-rental")


def execute():
    for name in SHADOWED_PAGES:
        if frappe.db.exists("Page", name):
            frappe.delete_doc("Page", name, force=True, ignore_permissions=True)
