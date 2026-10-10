"""Données de base des tests d'intégration (bench Frappe réel) : une seule définition, valable quelle que soit la langue du site.

Ces fonctions ne servent qu'aux tests qui exigent un vrai site; sans `frappe`, elles ne sont jamais appelées.
"""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

# Tests écrits pour le mode « sans Frappe » (réponses simulées et étiquetées) : sans objet dans un vrai bench, où les mêmes
# appels exigent de vrais enregistrements. Ils tournent hors bench (CI, poste de développement).
NO_FRAPPE = unittest.skipIf(frappe is not None, "mode sans Frappe : testé hors bench")


def item_group() -> str:
    """Un groupe d'articles qui existe (son nom dépend de la langue de l'assistant de configuration d'ERPNext)."""
    return (
        frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        or frappe.db.get_value("Item Group", {}, "name")
        or "All Item Groups"
    )


def ensure_item(item_code: str) -> str:
    """Crée l'article ERPNext s'il manque (avec les champs obligatoires du site) et renvoie son code."""
    if not frappe.db.exists("Item", item_code):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": item_group(),
                "is_stock_item": 1,
            }
        ).insert(ignore_permissions=True)
    return item_code


def ensure_company(name: str, abbr: str) -> str:
    if not frappe.db.exists("Company", name):
        frappe.get_doc(
            {"doctype": "Company", "company_name": name, "abbr": abbr, "default_currency": "CAD", "country": "Canada"}
        ).insert(ignore_permissions=True)
    return name


def ensure_customer(name: str, company: str) -> str:
    """Un client de la société (champ `cortex_company`), sans doublon d'une exécution à l'autre."""
    existing = frappe.db.get_value("Customer", {"customer_name": name, "cortex_company": company}, "name")
    if existing:
        return existing
    doc = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Company",
            "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
            "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
            "cortex_company": company,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def ensure_profile(company: str, item_code: str, serialized: int = 1, quantity: int = 0, rate: float = 100.0) -> str:
    """Fiche de location (Cortex Rental Item Profile) de l'article pour la société."""
    ensure_item(item_code)
    if not frappe.db.exists("Cortex Rental Item Profile", {"item_code": item_code, "company": company}):
        frappe.get_doc(
            {
                "doctype": "Cortex Rental Item Profile",
                "company": company,
                "item_code": item_code,
                "item_name": item_code,
                "daily_rate": rate,
                "replacement_value": rate * 10,
                "is_serialized": serialized,
                "total_quantity": quantity,
            }
        ).insert(ignore_permissions=True)
    return item_code


def ensure_user(email: str, roles, company: str = "") -> str:
    """Un utilisateur de test avec ces rôles et, si `company` est donnée, la permission d'utilisateur sur cette société."""
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
                "roles": [{"role": r} for r in roles],
            }
        ).insert(ignore_permissions=True)
    if company and not frappe.db.exists("User Permission", {"user": email, "allow": "Company", "for_value": company}):
        frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Company", "for_value": company}).insert(
            ignore_permissions=True
        )
    return email


# Une vraie personne de l'équipe (jamais « Administrator », qui reçoit tous les rôles, y compris celui d'agent).
HUMAN_ROLES = ("Rental Manager", "Cortex Operations Manager")


def human_operator(company: str) -> str:
    return ensure_user("ops-human@cortex.test", HUMAN_ROLES, company)
