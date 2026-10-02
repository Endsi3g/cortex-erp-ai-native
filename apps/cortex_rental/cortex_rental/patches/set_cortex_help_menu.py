"""Replace the stock Help menu (docs, forum, GitHub issues, paid support) with Cortex's own entries."""

import frappe

ITEMS = (
    ("Discuter avec l'assistant", "Action", None, "cortex.openAssistant()"),
    ("Contacter le support", "Route", "/app/cortex-support-request/new", None),
    ("Mes demandes de support", "Route", "/app/cortex-support-request", None),
    ("Raccourcis clavier", "Action", None, "cortex.showShortcuts(event)"),
)


def execute():
    settings = frappe.get_single("Navbar Settings")
    settings.set("help_dropdown", [])
    for label, item_type, route, action in ITEMS:
        settings.append(
            "help_dropdown",
            {
                "item_label": label,
                "item_type": item_type,
                "route": route,
                "action": action,
                "is_standard": 0,
                "hidden": 0,
            },
        )
    settings.save(ignore_permissions=True)
