"""
Undo the Desk lockdown that earlier Cortex builds applied on every login
and migration (setup.setup_cortex_sidebar hid every Workspace except
"Cortex Rental" directly in the database).

Cortex now runs as its own app under /cortex, and ERPNext Desk (/app) is
the standard ERPNext again: accountants submit invoices and payments
there. Public, standard workspaces are made visible again; private
(per-user) workspaces are left untouched because Cortex never hid them
on purpose and their owner may have.
"""

import frappe


def execute():
    if not frappe.db.table_exists("Workspace"):
        return

    frappe.db.sql(
        """
        UPDATE `tabWorkspace`
        SET `is_hidden` = 0
        WHERE `public` = 1
          AND IFNULL(`for_user`, '') = ''
          AND `is_hidden` = 1
        """
    )
