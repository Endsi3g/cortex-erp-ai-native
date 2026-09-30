"""Give the demonstration equipment French names (only when the demo records exist and still carry the English ones)."""

import frappe

NAMES = {
    "ARRI Alexa 35 Camera Body": "Boîtier de caméra ARRI Alexa 35",
    "Cooke S4/i Prime Lens Set (5-Lens)": "Ensemble d'objectifs fixes Cooke S4/i (5 objectifs)",
    "Aputure Electro Storm 1200d Pro Light": "Projecteur Aputure Electro Storm 1200d Pro",
    "BNC 12G-SDI Video Cable 50ft": "Câble vidéo BNC 12G-SDI, 50 pi",
    'Avenger C-Stand 40" with Grip Arm': "Pied C-Stand Avenger 40 po avec bras",
}
RULES = {"7 Days for 3": "7 jours pour 3", "2 Weeks = 6 Days": "2 semaines = 6 jours"}


def execute():
    for doctype, fields in (
        ("Item", ("item_name",)),
        ("Cortex Rental Item Profile", ("item_name",)),
        ("Cortex Rental Transaction Item", ("item_name",)),
    ):
        for english, french in NAMES.items():
            for field in fields:
                for name in frappe.get_all(doctype, filters={field: english}, pluck="name"):
                    frappe.db.set_value(doctype, name, field, french, update_modified=False)
    for english, french in RULES.items():
        for name in frappe.get_all("Rental Pricing Rule", filters={"rule_name": english}, pluck="name"):
            frappe.db.set_value("Rental Pricing Rule", name, "rule_name", french, update_modified=False)
