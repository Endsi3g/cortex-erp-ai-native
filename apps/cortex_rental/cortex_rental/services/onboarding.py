"""Guided company setup: state, saves and team invitations. Every write is permission-checked.

Only the company owner (role « Cortex System Manager », scoped to exactly one company and without the
global `System Manager`) can change the setup. Nothing here is invented: counts come from the database.
"""

import json
import re
from typing import Any, Dict, Iterable, List, Optional

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
    ("company", "Votre entreprise", "profile_done", False),
    ("owner", "Vous, le propriétaire", "owner_done", False),
    ("team", "Votre équipe", "team_done", True),
    ("catalog", "Votre catalogue", "catalog_done", True),
    ("pricing", "Prix, taxes et règles", "policies_done", True),
    ("first", "Votre première location", "first_rental_done", True),
)
STEP_KEYS = {key for key, *_ in STEPS}
REQUIRED_KEYS = [key for key, _t, _f, optional in STEPS if not optional]
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,20}$")


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


def has_required_missing(user: str) -> bool:
    """True when an owner's required steps (company information, owner contact) are not all done."""
    company = company_of(user)
    if not company or not frappe.db.exists(DOCTYPE, company):
        return False
    return bool(
        required_missing({flag: bool(frappe.db.get_value(DOCTYPE, company, flag)) for _k, _t, flag, _o in STEPS})
    )


def _require_owner(company: str) -> None:
    user = frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return
    if not is_owner(user) or company_of(user) != company:
        frappe.throw("Seul le propriétaire de l'entreprise peut modifier la configuration.", frappe.PermissionError)


def _doc(company: str):
    tenant_provisioning.ensure_onboarding(company, frappe.session.user)
    return frappe.get_doc(DOCTYPE, company)


def build_steps(flags: Dict[str, bool], skipped: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """Pure: the step list the screen shows. The first unfinished step is `current`; a step is `locked` only while an
    earlier REQUIRED step is unfinished (going back is always possible, going forward needs the required steps)."""
    skipped = set(skipped)
    steps, current_set, blocked = [], False, False
    for key, title, flag, optional in STEPS:
        done = bool(flags.get(flag))
        step = {
            "key": key,
            "title": title,
            "done": done,
            "skipped": bool(not done and optional and key in skipped),
            "required": not optional,
            "optional": optional,
            "current": False,
            "locked": blocked,
        }
        if not done and not step["skipped"] and not current_set:
            step["current"] = True
            current_set = True
        if not optional and not done:
            blocked = True
        steps.append(step)
    return steps


def required_missing(flags: Dict[str, bool]) -> List[str]:
    """Pure: the keys of the required steps that are not done yet."""
    return [key for key, _t, flag, optional in STEPS if not optional and not flags.get(flag)]


def _skipped(doc) -> List[str]:
    try:
        value = json.loads(doc.get("skipped_steps") or "[]")
    except (TypeError, ValueError):
        value = []
    return [k for k in value if k in STEP_KEYS]


def _set_skipped(doc, keys: Iterable[str]) -> None:
    doc.skipped_steps = json.dumps(sorted(set(keys)))


def _address(company: str) -> Dict[str, str]:
    names = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
        pluck="parent",
    )
    if not names:
        return {"address_line1": "", "city": "", "state": "", "pincode": ""}
    row = frappe.db.get_value("Address", names[0], ["address_line1", "city", "state", "pincode"], as_dict=True) or {}
    return {k: row.get(k) or "" for k in ("address_line1", "city", "state", "pincode")}


def _auto_progress(company: str, doc) -> None:
    """Ce qui existe déjà compte comme fait : de l'équipe, du matériel ou une location (rien n'est inventé)."""
    changed = False
    checks = (
        (
            "team_done",
            len(frappe.get_all("User Permission", filters={"allow": "Company", "for_value": company}, pluck="user"))
            > 1,
        ),
        ("catalog_done", frappe.db.count("Cortex Rental Item Profile", {"company": company}) > 0),
        ("first_rental_done", frappe.db.count("Cortex Rental Transaction", {"company": company}) > 0),
    )
    for flag, condition in checks:
        if condition and not doc.get(flag):
            doc.set(flag, 1)
            changed = True
    if changed:
        doc.flags.ignore_permissions = True
        doc.save()


def get_state(company: str) -> Dict[str, Any]:
    doc = _doc(company)
    _auto_progress(company, doc)
    flags = {flag: bool(doc.get(flag)) for _k, _t, flag, _o in STEPS}
    skipped = _skipped(doc)
    steps = build_steps(flags, skipped)
    profile_company = frappe.get_doc("Company", company)
    user = frappe.session.user
    team = frappe.get_all("User Permission", filters={"allow": "Company", "for_value": company}, pluck="user")
    members = frappe.get_all(
        "User", filters={"name": ["in", team or [""]]}, fields=["name", "full_name", "enabled", "last_login"]
    )
    me = frappe.db.get_value("User", user, ["first_name", "last_name", "mobile_no", "time_zone"], as_dict=True) or {}
    settings = (
        frappe.db.get_value(
            "Cortex Finance Settings",
            {"company": company},
            ["tps_number", "tvq_number", "deposit_percent"],
            as_dict=True,
        )
        or {}
    )
    missing = required_missing(flags)
    return {
        "company": company,
        "status": doc.status,
        "is_owner": is_owner(user) or "System Manager" in frappe.get_roles(user),
        "steps": steps,
        "required_missing": missing,
        "can_finish": not missing,
        "progress": {
            "done": sum(1 for s_ in steps if s_["done"]),
            "total": len(steps),
            "required_done": len(REQUIRED_KEYS) - len(missing),
            "required_total": len(REQUIRED_KEYS),
        },
        "company_info": {
            "company_name": profile_company.company_name,
            "country": profile_company.country,
            "default_currency": profile_company.default_currency,
            "phone_no": profile_company.phone_no or "",
            "email": profile_company.email or "",
            "website": profile_company.website or "",
            "logo": profile_company.company_logo or "",
            **_address(company),
        },
        "owner_info": {
            "email": user,
            "first_name": me.get("first_name") or "",
            "last_name": me.get("last_name") or "",
            "mobile_no": me.get("mobile_no") or "",
            "time_zone": me.get("time_zone") or tenant_provisioning.DEFAULT_TIMEZONE,
        },
        "team": [
            {"email": m.name, "full_name": m.full_name, "enabled": bool(m.enabled), "signed_in": bool(m.last_login)}
            for m in members
        ],
        "role_presets": [
            {"key": key, "label": preset["label"], "description": preset["description"]}
            for key, preset in tenant_provisioning.ROLE_PRESETS.items()
        ],
        "catalog": {"equipment_count": frappe.db.count("Cortex Rental Item Profile", {"company": company})},
        "pricing": {
            "tps_number": settings.get("tps_number") or "",
            "tvq_number": settings.get("tvq_number") or "",
            "deposit_percent": float(
                settings.get("deposit_percent") if settings.get("deposit_percent") is not None else 30
            ),
            "rules": frappe.get_all(
                "Rental Pricing Rule",
                filters={"company": company, "is_active": 1},
                fields=["name", "rule_name", "calendar_days", "billable_days"],
            ),
        },
        "first": {"rentals": frappe.db.count("Cortex Rental Transaction", {"company": company})},
    }


def _phone(value: Optional[str], label: str) -> str:
    phone = (value or "").strip()
    if not PHONE_RE.match(phone):
        raise SignupError("invalid_phone", f"{label} n'est pas valide (chiffres, espaces, + ( ) - . seulement).")
    return phone


def save_company_profile(company: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Étape « Votre entreprise » : adresse, téléphone, courriel de contact, pays et devise, logo (tous obligatoires
    sauf le site Web). Ces informations servent au soutien, aux devis et aux factures."""
    _require_owner(company)
    country = (data.get("country") or "").strip()
    currency = (data.get("default_currency") or "").strip()
    if not country or not frappe.db.exists("Country", country):
        raise SignupError("invalid_country", "Choisissez un pays de la liste.")
    if not currency or not frappe.db.exists("Currency", currency):
        raise SignupError("invalid_currency", "Choisissez une devise de la liste.")
    address_line1 = clean_name(data.get("address_line1"), "L'adresse", 140)
    city = clean_name(data.get("city"), "La ville", 60)
    state = clean_name(data.get("state"), "La province ou l'État", 60)
    pincode = clean_name(data.get("pincode"), "Le code postal", 20)
    phone = _phone(data.get("phone_no"), "Le téléphone de l'entreprise")
    email = normalize_email(data.get("email"))
    company_doc = frappe.get_doc("Company", company)
    if not company_doc.company_logo:
        raise SignupError("logo_required", "Ajoutez le logo de votre entreprise avant de continuer.")
    if currency != company_doc.default_currency and frappe.db.exists("GL Entry", {"company": company}):
        raise SignupError(
            "currency_locked",
            "La devise ne peut plus changer : des écritures comptables existent déjà pour cette entreprise.",
        )
    website = (data.get("website") or "").strip()
    if website and not website.lower().startswith(("http://", "https://")):
        website = "https://" + website
    values = {"phone_no": phone, "email": email, "website": website}
    if data.get("tax_id"):
        values["tax_id"] = clean_name(data["tax_id"], "Le numéro de taxes", 60)
    if country == company_doc.country and currency == company_doc.default_currency:
        # Seuls les coordonnées changent : on évite le enregistrement complet d'ERPNext (près de 2 s de validations).
        frappe.db.set_value("Company", company, values)
        frappe.clear_document_cache("Company", company)
    else:
        company_doc.country = country
        company_doc.default_currency = currency
        company_doc.update(values)
        company_doc.flags.ignore_permissions = True
        company_doc.save()

    names = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Company", "link_name": company, "parenttype": "Address"},
        pluck="parent",
    )
    values = {"address_line1": address_line1, "city": city, "state": state, "pincode": pincode, "country": country}
    if names:
        frappe.db.set_value("Address", names[0], values)
    else:
        frappe.get_doc(
            {
                "doctype": "Address",
                "address_title": company,
                "address_type": "Office",
                "is_your_company_address": 1,
                "links": [{"link_doctype": "Company", "link_name": company}],
                **values,
            }
        ).insert(ignore_permissions=True)

    doc = _doc(company)
    doc.profile_done = 1
    doc.flags.ignore_permissions = True
    doc.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.onboarding.profile_saved",
        entity_type=DOCTYPE,
        entity_id=company,
        after_state={"country": country, "default_currency": currency, "city": city},
    )
    return get_state(company)


def _timezones() -> set:
    import pytz

    return set(pytz.all_timezones)


def save_owner_profile(company: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Étape « Vous, le propriétaire » : nom et téléphone de la personne-ressource (obligatoires pour le soutien)."""
    _require_owner(company)
    first = clean_name(data.get("first_name"), "Le prénom", 80)
    last = " ".join((data.get("last_name") or "").split())[:80]
    phone = _phone(data.get("mobile_no"), "Votre téléphone")
    time_zone = (data.get("time_zone") or "").strip() or tenant_provisioning.DEFAULT_TIMEZONE
    user = frappe.session.user
    if time_zone not in _timezones():
        raise SignupError("invalid_time_zone", "Choisissez un fuseau horaire de la liste.")
    if frappe.db.exists("User", {"mobile_no": phone, "name": ["!=", user]}):
        raise SignupError("phone_taken", "Ce numéro de téléphone est déjà utilisé par un autre compte.")
    if user != "Administrator":
        frappe.db.set_value(
            "User",
            user,
            {
                "first_name": first,
                "last_name": last,
                "full_name": f"{first} {last}".strip(),
                "mobile_no": phone,
                "time_zone": time_zone,
            },
        )
        frappe.clear_cache(user=user)
    doc = _doc(company)
    doc.owner_done = 1
    doc.owner_user = user
    doc.flags.ignore_permissions = True
    doc.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.onboarding.owner_saved",
        entity_type=DOCTYPE,
        entity_id=company,
        after_state={"owner": user},
    )
    return get_state(company)


def save_pricing(company: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Étape facultative « Prix, taxes et règles » : numéros de TPS/TVQ et pourcentage d'acompte."""
    _require_owner(company)
    tps = " ".join((data.get("tps_number") or "").split())[:40]
    tvq = " ".join((data.get("tvq_number") or "").split())[:40]
    try:
        deposit = float(data.get("deposit_percent"))
    except (TypeError, ValueError):
        raise SignupError("invalid_deposit", "Indiquez le pourcentage d'acompte (par exemple 30).")
    if not 0 <= deposit <= 100:
        raise SignupError("invalid_deposit", "L'acompte doit être entre 0 et 100 %.")
    from cortex_rental.services import billing

    billing.ensure_settings(company)
    tenant_provisioning.ensure_default_pricing_rule(company)
    frappe.db.set_value(
        "Cortex Finance Settings",
        {"company": company},
        {"tps_number": tps, "tvq_number": tvq, "deposit_percent": deposit},
    )
    doc = _doc(company)
    doc.policies_done = 1
    _set_skipped(doc, [k for k in _skipped(doc) if k != "pricing"])
    doc.flags.ignore_permissions = True
    doc.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.onboarding.pricing_saved",
        entity_type=DOCTYPE,
        entity_id=company,
        after_state={"deposit_percent": deposit},
    )
    return get_state(company)


def skip_step(company: str, step: str) -> Dict[str, Any]:
    """Passer une étape facultative pour l'instant (on peut y revenir à tout moment)."""
    _require_owner(company)
    if step not in STEP_KEYS or step in REQUIRED_KEYS:
        raise SignupError("not_skippable", "Cette étape est obligatoire : elle ne peut pas être passée.")
    doc = _doc(company)
    _set_skipped(doc, _skipped(doc) + [step])
    doc.flags.ignore_permissions = True
    doc.save()
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
    """Marque une étape facultative comme faite. Les étapes obligatoires se complètent seulement en enregistrant leurs
    informations (save_company_profile, save_owner_profile)."""
    _require_owner(company)
    if step not in STEP_KEYS:
        raise SignupError("invalid_step", "Étape inconnue.")
    if step in REQUIRED_KEYS:
        raise SignupError("required_step", "Cette étape se termine en enregistrant ses informations.")
    flag = next(flag for key, _t, flag, _o in STEPS if key == step)
    doc = _doc(company)
    doc.set(flag, 1)
    _set_skipped(doc, [k for k in _skipped(doc) if k != step])
    doc.flags.ignore_permissions = True
    doc.save()
    return get_state(company)


def finish(company: str) -> Dict[str, Any]:
    _require_owner(company)
    doc = _doc(company)
    missing = required_missing({flag: bool(doc.get(flag)) for _k, _t, flag, _o in STEPS})
    if missing:
        titles = [title for key, title, _f, _o in STEPS if key in missing]
        raise SignupError("required_missing", "Il reste des étapes obligatoires : " + ", ".join(titles) + ".")
    doc.status = "Completed"
    doc.completed_on = now_datetime()
    doc.flags.ignore_permissions = True
    doc.save()
    return get_state(company)
