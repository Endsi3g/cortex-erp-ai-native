"""Le guide natif « Bienvenue dans Cortex » est remplacé par l'assistant de configuration (page cortex-setup)."""

import frappe


def execute():
    if frappe.db.exists("Module Onboarding", "Cortex Rental"):
        frappe.delete_doc("Module Onboarding", "Cortex Rental", force=True, ignore_permissions=True)
    steps = frappe.get_all("Onboarding Step", filters={"name": ["like", "%"]}, pluck="name")
    wanted = {
        "Vérifier le profil de l’entreprise",
        "Ajouter le logo de votre entreprise",
        "Inviter votre équipe",
        "Ajouter votre matériel",
        "Vérifier la règle tarifaire 7 = 3",
        "Créer votre première location",
        "Essayer l’assistant Cortex",
    }
    for name in steps:
        if name in wanted:
            frappe.delete_doc("Onboarding Step", name, force=True, ignore_permissions=True)
    # Première version de l'assistant, dont la route entrait en conflit avec la liste du DocType « Cortex Onboarding ».
    if frappe.db.exists("Page", "cortex-onboarding"):
        frappe.delete_doc("Page", "cortex-onboarding", force=True, ignore_permissions=True)
