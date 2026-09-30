"""Create a tenant (Company) and its people. Every write here is server-side and audited.

A tenant is a `Company`: a user only sees the companies they hold a `User Permission` for, and never
receives the global `System Manager` role from this module (see permissions/agent_scopes.py).
"""

from typing import Any, Dict, Iterable, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.signup_rules import abbreviation

DEFAULT_COUNTRY = "Canada"
DEFAULT_CURRENCY = "CAD"
DEFAULT_TIMEZONE = "America/Toronto"
DEFAULT_LANGUAGE = "fr"
FORBIDDEN_ROLES = {"System Manager", "Administrator", "Guest", "All"}

# Presets offered when the owner invites a colleague: a role bundle, never a raw role list.
ROLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "manager": {
        "label": "Gestionnaire",
        "description": "Location, disponibilité, approbations et consignation.",
        "roles": [
            "Rental Manager",
            "Cortex Operations Manager",
            "Cortex Account Reviewer",
            "Cortex Consignment Manager",
        ],
    },
    "counter": {
        "label": "Comptoir",
        "description": "Sorties et retours du matériel.",
        "roles": ["Rental Operator", "Cortex Counter Staff"],
    },
    "inventory": {
        "label": "Inventaire",
        "description": "Catalogue, séries et état du parc.",
        "roles": ["Cortex Inventory Manager", "Rental Operator"],
    },
    "finance": {
        "label": "Finance",
        "description": "Facturation, états financiers et versements.",
        "roles": ["Cortex Finance Manager", "Cortex Account Reviewer"],
    },
    "viewer": {
        "label": "Lecture seule",
        "description": "Consultation et journal d'audit.",
        "roles": ["Auditor"],
    },
}


def safe_roles(roles: Iterable[str]) -> List[str]:
    """Drop global-admin roles and roles that do not exist on this site; keep order, no duplicates."""
    wanted = [r.strip() for r in roles if r and r.strip() and r.strip() not in FORBIDDEN_ROLES]
    if frappe:
        wanted = [r for r in wanted if frappe.db.exists("Role", r)]
    return list(dict.fromkeys(wanted))


def create_company(company_name: str, country: str = DEFAULT_COUNTRY, currency: str = DEFAULT_CURRENCY) -> str:
    if frappe.db.exists("Company", company_name):
        frappe.throw(
            f"Une entreprise nommée « {company_name} » existe déjà : modifiez le nom de la demande avant d'approuver.",
            frappe.DuplicateEntryError,
        )
    taken = frappe.get_all("Company", pluck="abbr")
    company = frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": company_name,
            "abbr": abbreviation(company_name, taken),
            "default_currency": currency,
            "country": country,
        }
    )
    company.insert(ignore_permissions=True)
    ensure_default_pricing_rule(company.name)
    return company.name


def ensure_default_pricing_rule(company: str) -> None:
    """The house rule the product promises: 7 calendar days are billed as 3."""
    if not frappe.db.exists("DocType", "Rental Pricing Rule"):
        return
    if frappe.db.exists("Rental Pricing Rule", {"company": company}):
        return
    frappe.get_doc(
        {
            "doctype": "Rental Pricing Rule",
            "company": company,
            "rule_name": "7 jours = 3 jours facturés",
            "calendar_days": 7,
            "billable_days": 3.0,
            "is_active": 1,
            "description": "Règle par défaut : la semaine est facturée 3 jours.",
        }
    ).insert(ignore_permissions=True)


def create_user(
    email: str,
    full_name: str,
    company: str,
    roles: Iterable[str],
    language: str = DEFAULT_LANGUAGE,
    time_zone: str = DEFAULT_TIMEZONE,
) -> str:
    """Create an enabled desk user scoped to one company; the password is set through the reset link."""
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "language": language,
            "time_zone": time_zone,
        }
    )
    for role in safe_roles(roles):
        user.append("roles", {"role": role})
    user.flags.ignore_permissions = True
    user.flags.ignore_password_policy = True
    user.insert()
    frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user.name,
            "allow": "Company",
            "for_value": company,
            "apply_to_all_doctypes": 1,
            "is_default": 1,
        }
    ).insert(ignore_permissions=True)
    return user.name


def ensure_onboarding(company: str, owner_user: Optional[str] = None) -> str:
    if frappe.db.exists("Cortex Onboarding", company):
        return company
    frappe.get_doc({"doctype": "Cortex Onboarding", "company": company, "owner_user": owner_user}).insert(
        ignore_permissions=True
    )
    return company


def password_setup_link(user_email: str) -> str:
    """One-time link to /update-password, generated by Frappe (hashed key, expiry, password policy)."""
    return frappe.get_doc("User", user_email)._reset_password(send_email=False)
