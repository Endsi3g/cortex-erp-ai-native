"""Guided company setup: state, saves and team invitations. Every write is permission-checked.

Only the company owner (role « Cortex System Manager », scoped to exactly one company and without the
global `System Manager`) can change the setup. Nothing here is invented: counts come from the database.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
    from frappe.utils import now_datetime
except ImportError:
    frappe = None

from cortex_rental.services import access_emails, tenant_provisioning
from cortex_rental.services.audit import AuditService
from cortex_rental.services.signup_rules import (
    SignupError,
    check_domain_policy,
    clean_name,
    normalize_email,
    split_lines,
)

OWNER_ROLE = "Cortex System Manager"
DOCTYPE = "Cortex Onboarding"

# key, French title, flag field, optional?
STEPS = (
    ("profile", "Profil de l'entreprise", "profile_done", False),
    ("team", "Équipe", "team_done", True),
    ("catalog", "Catalogue", "catalog_done", True),
    ("policies", "Règles de location", "policies_done", True),
)
STEP_KEYS = {key for key, *_ in STEPS}


def company_of(user: str) -> Optional[str]:
    """The single company a scoped user belongs to, or None (multi-company and global admins are skipped)."""
    companies = frappe.get_all("User Permission", filters={"user": user, "allow": "Company"}, pluck="for_value")
    return companies[0] if len(set(companies)) == 1 else None


def is_owner(user: str) -> bool:
    roles = frappe.get_roles(user)
    return OWNER_ROLE in roles and "System Manager" not in roles


def needs_onboarding(user: str) -> bool:
    """True for a company owner whose guided setup is not completed."""
    if not is_owner(user):
        return False
    company = company_of(user)
    if not company or not frappe.db.exists(DOCTYPE, company):
        return False
    return frappe.db.get_value(DOCTYPE, company, "status") != "Completed"


def _require_owner(company: str) -> None:
    user = frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return
    if not is_owner(user) or company_of(user) != company:
        frappe.throw("Seul le propriétaire de l'entreprise peut modifier la configuration.", frappe.PermissionError)


def _doc(company: str):
    tenant_provisioning.ensure_onboarding(company, frappe.session.user)
    return frappe.get_doc(DOCTYPE, company)


def build_steps(flags: Dict[str, bool]) -> List[Dict[str, Any]]:
    """Pure: the step list the screen shows, with the first unfinished step marked `current`."""
    steps, current_set = [], False
    for key, title, flag, optional in STEPS:
        done = bool(flags.get(flag))
        step = {"key": key, "title": title, "done": done, "optional": optional, "current": False}
        if not done and not current_set:
            step["current"] = True
            current_set = True
        steps.append(step)
    return steps


def get_state(company: str) -> Dict[str, Any]:
    doc = _doc(company)
    flags = {flag: bool(doc.get(flag)) for _k, _t, flag, _o in STEPS}
    steps = build_steps(flags)
    profile_company = frappe.get_doc("Company", company)
    user = frappe.session.user
    team = frappe.get_all(
        "User Permission",
        filters={"allow": "Company", "for_value": company},
        pluck="user",
    )
    members = frappe.get_all(
        "User", filters={"name": ["in", team or [""]]}, fields=["name", "full_name", "enabled", "last_login"]
    )
    return {
        "company": company,
        "status": doc.status,
        "is_owner": is_owner(user) or "System Manager" in frappe.get_roles(user),
        "steps": steps,
        "progress": {"done": sum(1 for s in steps if s["done"]), "total": len(steps)},
        "profile": {
            "company_name": profile_company.company_name,
            "country": profile_company.country,
            "default_currency": profile_company.default_currency,
            "tax_id": profile_company.tax_id or "",
            "phone_no": profile_company.phone_no or "",
            "website": profile_company.website or "",
            "time_zone": frappe.db.get_value("User", user, "time_zone") or tenant_provisioning.DEFAULT_TIMEZONE,
            "language": frappe.db.get_value("User", user, "language") or tenant_provisioning.DEFAULT_LANGUAGE,
        },
        "team": [
            {"email": m.name, "full_name": m.full_name, "enabled": bool(m.enabled), "signed_in": bool(m.last_login)}
            for m in members
        ],
        "role_presets": [
            {"key": key, "label": preset["label"], "description": preset["description"]}
            for key, preset in tenant_provisioning.ROLE_PRESETS.items()
        ],
        "catalog": {
            "equipment_count": frappe.db.count("Cortex Rental Item Profile", {"company": company}),
            "import_url": "/app/data-import/new?reference_doctype=Item",
            "equipment_url": "/app/cortex-equipment",
        },
        "policies": {
            "rules": frappe.get_all(
                "Rental Pricing Rule",
                filters={"company": company, "is_active": 1},
                fields=["name", "rule_name", "calendar_days", "billable_days"],
            )
        },
    }


def save_company_profile(company: str, data: Dict[str, Any]) -> Dict[str, Any]:
    _require_owner(company)
    country = (data.get("country") or "").strip()
    currency = (data.get("default_currency") or "").strip()
    if not country or not frappe.db.exists("Country", country):
        raise SignupError("invalid_country", "Choisissez un pays de la liste.")
    if not currency or not frappe.db.exists("Currency", currency):
        raise SignupError("invalid_currency", "Choisissez une devise de la liste.")
    company_doc = frappe.get_doc("Company", company)
    if currency != company_doc.default_currency and frappe.db.exists("GL Entry", {"company": company}):
        raise SignupError(
            "currency_locked",
            "La devise ne peut plus changer : des écritures comptables existent déjà pour cette entreprise.",
        )
    website = (data.get("website") or "").strip()
    if website and not website.lower().startswith(("http://", "https://")):
        website = "https://" + website
    company_doc.country = country
    company_doc.default_currency = currency
    company_doc.tax_id = clean_name(data["tax_id"], "Le numéro de taxes", 60) if data.get("tax_id") else ""
    company_doc.phone_no = clean_name(data["phone_no"], "Le téléphone", 40) if data.get("phone_no") else ""
    company_doc.website = website
    company_doc.flags.ignore_permissions = True
    company_doc.save()

    user = frappe.session.user
    time_zone = (data.get("time_zone") or "").strip()
    language = (data.get("language") or "").strip()
    updates = {}
    if time_zone:
        updates["time_zone"] = time_zone
    if language and frappe.db.exists("Language", language):
        updates["language"] = language
    if updates and user != "Administrator":
        frappe.db.set_value("User", user, updates)

    doc = _doc(company)
    doc.profile_done = 1
    doc.flags.ignore_permissions = True
    doc.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.onboarding.profile_saved",
        entity_type=DOCTYPE,
        entity_id=company,
        after_state={"country": country, "default_currency": currency},
    )
    return get_state(company)


def invite_team_member(company: str, email: str, full_name: str, preset: str) -> Dict[str, Any]:
    _require_owner(company)
    email = normalize_email(email)
    full_name = clean_name(full_name, "Le nom")
    if preset not in tenant_provisioning.ROLE_PRESETS:
        raise SignupError("invalid_role", "Choisissez un profil dans la liste.")
    settings = frappe.get_cached_doc("Cortex Access Settings")
    check_domain_policy(email, split_lines(settings.allowed_email_domains), block_free=False)
    if frappe.db.exists("User", email):
        raise SignupError("exists", "Cette personne a déjà un compte. Demandez-lui de se connecter.")

    definition = tenant_provisioning.ROLE_PRESETS[preset]
    user = tenant_provisioning.create_user(email, full_name, company, definition["roles"])
    link = tenant_provisioning.password_setup_link(user)
    inviter = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    sent = access_emails.send_team_invite(user, full_name, company, inviter, definition["label"], link)
    AuditService.record_mutation(
        company=company,
        action="cortex.onboarding.member_invited",
        entity_type="User",
        entity_id=user,
        after_state={"preset": preset, "roles": definition["roles"]},
    )
    result = {"email": user, "email_sent": sent}
    if not sent:
        result["setup_link"] = link  # shown to the owner only, so they can pass it on manually
    return result


def complete_step(company: str, step: str) -> Dict[str, Any]:
    _require_owner(company)
    if step not in STEP_KEYS:
        raise SignupError("invalid_step", "Étape inconnue.")
    flag = next(flag for key, _t, flag, _o in STEPS if key == step)
    doc = _doc(company)
    doc.set(flag, 1)
    doc.flags.ignore_permissions = True
    doc.save()
    return get_state(company)


def finish(company: str) -> Dict[str, Any]:
    _require_owner(company)
    doc = _doc(company)
    if not doc.profile_done:
        raise SignupError("profile_required", "Complétez d'abord le profil de l'entreprise.")
    doc.status = "Completed"
    doc.completed_on = now_datetime()
    doc.flags.ignore_permissions = True
    doc.save()
    return get_state(company)
