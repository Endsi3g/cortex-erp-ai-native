"""French is the only language Cortex ships: make it the site default and the language of existing users.

ERPNext and Frappe already include French translations; `translations/fr.csv` adds the Cortex strings. People who
chose another language explicitly (anything other than empty or English) keep their choice.
"""

import frappe


def execute():
    if frappe.db.exists("Language", "fr"):
        frappe.db.set_value("Language", "fr", "enabled", 1)
    frappe.db.set_single_value("System Settings", "language", "fr")
    for name in frappe.get_all("User", filters={"user_type": "System User"}, pluck="name"):
        language = frappe.db.get_value("User", name, "language")
        if not language or language == "en":
            frappe.db.set_value("User", name, "language", "fr", update_modified=False)
