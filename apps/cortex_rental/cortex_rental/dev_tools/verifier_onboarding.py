"""Prépare une société d'essai neuve et son propriétaire, comme le fait l'approbation d'une vraie inscription.

    bench --site cortex.local execute cortex_rental.dev_tools.verifier_onboarding.prepare
    bench --site cortex.local execute cortex_rental.dev_tools.verifier_onboarding.finish_demo_companies

Outil de développement : il ne s'exécute jamais seul et n'est pas branché sur le produit.
"""

import frappe

from cortex_rental.services import access_requests, tenant_provisioning

COMPANY = "Atelier Lumière (essai)"
OWNER = "onb.proprio@example.com"
PASSWORD = "Sim-Pass-2026!"


def prepare():
    frappe.set_user("Administrator")
    if frappe.db.exists("User", OWNER):
        frappe.delete_doc("User", OWNER, force=True, ignore_permissions=True)
    if frappe.db.exists("Cortex Onboarding", COMPANY):
        frappe.delete_doc("Cortex Onboarding", COMPANY, force=True, ignore_permissions=True)
    if frappe.db.exists("Company", COMPANY):
        frappe.delete_doc("Company", COMPANY, force=True, ignore_permissions=True)
    settings = access_requests.get_settings()
    company = tenant_provisioning.create_company(COMPANY)
    roles = access_requests.split_owner_roles(settings.owner_roles)
    user = tenant_provisioning.create_user(OWNER, "Camille Tremblay", company, roles)
    tenant_provisioning.ensure_onboarding(company, user)
    frappe.utils.password.update_password(user, PASSWORD)
    frappe.db.commit()
    print({"company": company, "user": user, "roles": roles})


def finish_demo_companies():
    """Les sociétés de démonstration existent déjà : on les marque terminées pour ne pas rediriger leurs comptes."""
    frappe.set_user("Administrator")
    for company in frappe.get_all("Company", pluck="name"):
        if company == COMPANY:
            continue
        if not frappe.db.exists("Cortex Onboarding", company):
            tenant_provisioning.ensure_onboarding(company)
        frappe.db.set_value("Cortex Onboarding", company, "status", "Completed")
    frappe.db.commit()
