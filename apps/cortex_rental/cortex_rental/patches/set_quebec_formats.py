"""Québec display formats: 1 782,50 / aaaa-mm-jj / 24 h, Monday first. Only overrides the untouched ERPNext defaults."""

import frappe

DEFAULTS_TO_REPLACE = {
    "number_format": ("#,###.##", "# ###,##"),
    "date_format": ("dd-mm-yyyy", "yyyy-mm-dd"),
    "time_format": ("HH:mm:ss", "HH:mm:ss"),
}


def execute():
    settings = frappe.get_single("System Settings")
    changed = False
    for field, (old, new) in DEFAULTS_TO_REPLACE.items():
        if (settings.get(field) or old) == old and settings.get(field) != new:
            settings.set(field, new)
            changed = True
    if settings.get("first_day_of_the_week") != "Monday":
        settings.first_day_of_the_week = "Monday"
        changed = True
    if changed:
        settings.save(ignore_permissions=True)
