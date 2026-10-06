"""Administration of one company: pricing rules, team and roles, imports overview.

Every write is permission-checked: pricing rules go through the normal Frappe permission model (role
« Pricing Manager », company scoped by User Permission); team changes need the company owner (or a System Manager),
like the setup assistant. Nothing here decides a price: `PricingService` stays the only place that computes one.
"""

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services import tenant_provisioning
from cortex_rental.services import defense
from cortex_rental.services.audit import AuditService
from cortex_rental.services.signup_rules import SignupError, clean_name

OWNER_ROLE = "Cortex System Manager"
RULE_DOCTYPE = "Rental Pricing Rule"
MAX_CALENDAR_DAYS = 365
# Durations shown as the built-in reference curve (used when no active rule matches exactly).
REFERENCE_DURATIONS = (1, 2, 3, 4, 7, 14, 30)
IMPORT_TARGETS = (
    ("Item", "Équipement (articles)", "Catalogue de location : code, nom, groupe, prix."),
    ("Customer", "Clients", "Fiches clients : nom, type, contacts."),
    (
        "Supplier",
        "Fournisseurs et propriétaires",
        "Fournisseurs, y compris les propriétaires de matériel en consignation.",
    ),
)


# ---- pure rules (unit-tested without Frappe) ------------------------------------------------------


def validate_pricing_rule(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean a pricing rule payload or raise SignupError(code, message in French)."""
    name = clean_name(data.get("rule_name"), "Le nom de la règle", 100)
    try:
        calendar_days = int(data.get("calendar_days"))
    except (TypeError, ValueError):
        raise SignupError("invalid_days", "Indiquez un nombre entier de jours civils.")
    if not 1 <= calendar_days <= MAX_CALENDAR_DAYS:
        raise SignupError("invalid_days", f"Les jours civils doivent être entre 1 et {MAX_CALENDAR_DAYS}.")
    try:
        billable = round(float(data.get("billable_days")), 2)
    except (TypeError, ValueError):
        raise SignupError("invalid_billable", "Indiquez le nombre de jours facturés (par exemple 3 ou 1,5).")
    if billable <= 0:
        raise SignupError("invalid_billable", "Les jours facturés doivent être supérieurs à zéro.")
    if billable > calendar_days:
        raise SignupError(
            "billable_exceeds_calendar",
            "Une règle ne peut pas facturer plus de jours que la durée réelle de location.",
        )
    description = " ".join(str(data.get("description") or "").split())[:500]
    return {
        "rule_name": name,
        "calendar_days": calendar_days,
        "billable_days": billable,
        "description": description,
    }


def detect_preset(roles: Iterable[str], presets: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """The preset whose roles the person holds in full (the largest one wins), or None for a custom mix."""
    held: Set[str] = set(roles)
    best: Tuple[int, Optional[str]] = (0, None)
    for key, preset in presets.items():
        wanted = set(preset["roles"])
        if wanted and wanted <= held and len(wanted) > best[0]:
            best = (len(wanted), key)
    return best[1]


def role_changes(
    current: Iterable[str], target: Iterable[str], presets: Dict[str, Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """(to add, to remove): swap preset roles for the target's, leave every other role (Desk User, custom) alone."""
    held, wanted = set(current), set(target)
    preset_roles = {role for preset in presets.values() for role in preset["roles"]}
    add = [role for role in target if role not in held]
    remove = sorted(role for role in held if role in preset_roles and role not in wanted)
    return add, remove


# ---- access ---------------------------------------------------------------------------------------


def _is_system_manager(user: str) -> bool:
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def can_manage_team(user: str) -> bool:
    return _is_system_manager(user) or OWNER_ROLE in frappe.get_roles(user)


def _require_team_admin(company: str) -> None:
    from cortex_rental.services import onboarding

    onboarding._require_owner(company)


def _member_emails(company: str) -> List[str]:
    return frappe.get_all("User Permission", filters={"allow": "Company", "for_value": company}, pluck="user")


def _require_member(company: str, email: str) -> None:
    if email not in _member_emails(company):
        raise SignupError("not_member", "Cette personne ne fait pas partie de l'équipe de cette entreprise.")


# ---- pricing rules --------------------------------------------------------------------------------


def _rule_row(row: Any) -> Dict[str, Any]:
    return {
        "name": row.name,
        "rule_name": row.rule_name,
        "calendar_days": int(row.calendar_days or 0),
        "billable_days": float(row.billable_days or 0),
        "is_active": bool(row.is_active),
        "description": row.description or "",
    }


def reference_curve() -> List[Dict[str, Any]]:
    """Built-in curve, computed by the pricing service itself so the screen never re-implements it."""
    from datetime import datetime, timedelta

    from cortex_rental.services.pricing import PricingService

    start = datetime(2026, 1, 1)
    curve = []
    for days in REFERENCE_DURATIONS:
        calendar, billable = PricingService.compute_billable_days(
            start.isoformat(), (start + timedelta(days=days)).isoformat()
        )
        curve.append({"calendar_days": calendar, "billable_days": billable})
    return curve


def get_pricing(company: str) -> Dict[str, Any]:
    rules = frappe.get_list(
        RULE_DOCTYPE,
        filters={"company": company},
        fields=["name", "rule_name", "calendar_days", "billable_days", "is_active", "description"],
        order_by="calendar_days asc, creation asc",
    )
    return {
        "company": company,
        "rules": [_rule_row(r) for r in rules],
        "reference_curve": reference_curve(),
        "can_edit": bool(frappe.has_permission(RULE_DOCTYPE, "write")),
    }


def _duplicate_active(company: str, calendar_days: int, exclude: Optional[str] = None) -> bool:
    filters: Dict[str, Any] = {"company": company, "is_active": 1, "calendar_days": calendar_days}
    if exclude:
        filters["name"] = ["!=", exclude]
    return bool(frappe.db.exists(RULE_DOCTYPE, filters))


def save_pricing_rule(company: str, data: Dict[str, Any]) -> Dict[str, Any]:
    if not frappe.has_permission(RULE_DOCTYPE, "write"):
        raise SignupError("forbidden", "Votre rôle ne permet pas de modifier les règles tarifaires.")
    clean = validate_pricing_rule(data)
    name = (data.get("name") or "").strip()
    active = bool(int(data.get("is_active", 1) or 0))
    if active and _duplicate_active(company, clean["calendar_days"], exclude=name or None):
        raise SignupError(
            "duplicate_rule",
            f"Une règle active existe déjà pour {clean['calendar_days']} jours civils : désactivez-la ou modifiez-la.",
        )
    if name:
        doc = frappe.get_doc(RULE_DOCTYPE, name)
        if doc.company != company:
            raise SignupError("not_member", "Cette règle appartient à une autre entreprise.")
        before = _rule_row(doc)
        doc.update({**clean, "is_active": int(active)})
        doc.save()
        action = "cortex.pricing_rule.updated"
    else:
        before = None
        doc = frappe.get_doc({"doctype": RULE_DOCTYPE, "company": company, **clean, "is_active": int(active)})
        doc.insert()
        action = "cortex.pricing_rule.created"
    AuditService.record_mutation(
        company=company,
        action=action,
        entity_type=RULE_DOCTYPE,
        entity_id=doc.name,
        before_state=before,
        after_state=_rule_row(doc),
    )
    return get_pricing(company)


def set_pricing_rule_active(company: str, name: str, active: bool) -> Dict[str, Any]:
    if not frappe.has_permission(RULE_DOCTYPE, "write"):
        raise SignupError("forbidden", "Votre rôle ne permet pas de modifier les règles tarifaires.")
    doc = frappe.get_doc(RULE_DOCTYPE, name)
    if doc.company != company:
        raise SignupError("not_member", "Cette règle appartient à une autre entreprise.")
    if active and _duplicate_active(company, int(doc.calendar_days), exclude=doc.name):
        raise SignupError("duplicate_rule", "Une autre règle active existe déjà pour cette durée.")
    before = _rule_row(doc)
    doc.is_active = int(active)
    doc.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.pricing_rule.activated" if active else "cortex.pricing_rule.deactivated",
        entity_type=RULE_DOCTYPE,
        entity_id=doc.name,
        before_state=before,
        after_state=_rule_row(doc),
    )
    return get_pricing(company)


# ---- team -----------------------------------------------------------------------------------------


def get_team(company: str) -> Dict[str, Any]:
    user = frappe.session.user
    emails = _member_emails(company)
    rows = frappe.get_all(
        "User",
        filters={"name": ["in", emails or [""]]},
        fields=["name", "full_name", "enabled", "last_login", "creation"],
        order_by="full_name asc",
    )
    presets = tenant_provisioning.ROLE_PRESETS
    members = []
    for row in rows:
        roles = frappe.get_roles(row.name)
        is_owner = OWNER_ROLE in roles
        members.append(
            {
                "email": row.name,
                "full_name": row.full_name or row.name,
                "enabled": bool(row.enabled),
                "signed_in": bool(row.last_login),
                "last_login": str(row.last_login) if row.last_login else None,
                "is_owner": is_owner,
                "is_you": row.name == user,
                "preset": None if is_owner else detect_preset(roles, presets),
            }
        )
    return {
        "company": company,
        "members": members,
        "presets": [{"key": k, "label": p["label"], "description": p["description"]} for k, p in presets.items()],
        "can_manage": can_manage_team(user),
    }


def set_member_preset(company: str, email: str, preset: str) -> Dict[str, Any]:
    _require_team_admin(company)
    presets = tenant_provisioning.ROLE_PRESETS
    if preset not in presets:
        raise SignupError("invalid_role", "Choisissez un profil dans la liste.")
    _require_member(company, email)
    if OWNER_ROLE in frappe.get_roles(email):
        raise SignupError("owner_locked", "Le profil du propriétaire ne se change pas ici.")
    target = tenant_provisioning.safe_roles(presets[preset]["roles"])
    doc = frappe.get_doc("User", email)
    current = [r.role for r in doc.roles]
    add, remove = role_changes(current, target, presets)
    doc.flags.ignore_permissions = True
    if add:
        doc.add_roles(*add)
    if remove:
        doc.remove_roles(*remove)
    AuditService.record_mutation(
        company=company,
        action="cortex.team.role_changed",
        entity_type="User",
        entity_id=email,
        before_state={"roles": sorted(current)},
        after_state={"preset": preset, "added": add, "removed": remove},
    )
    return get_team(company)


def set_member_enabled(company: str, email: str, enabled: bool) -> Dict[str, Any]:
    _require_team_admin(company)
    _require_member(company, email)
    if email == frappe.session.user:
        raise SignupError("self_locked", "Vous ne pouvez pas désactiver votre propre compte.")
    if OWNER_ROLE in frappe.get_roles(email) and not enabled:
        raise SignupError("owner_locked", "Le compte du propriétaire ne se désactive pas ici.")
    was = bool(frappe.db.get_value("User", email, "enabled"))
    frappe.db.set_value("User", email, "enabled", int(enabled))
    if not enabled:
        # Une personne désactivée perd tout de suite ses appareils connectés (sinon sa session resterait ouverte).
        from cortex_rental.services import devices

        devices.revoke_all(email, keep_sid=None, by=frappe.session.user)
    AuditService.record_mutation(
        company=company,
        action="cortex.team.member_enabled" if enabled else "cortex.team.member_disabled",
        entity_type="User",
        entity_id=email,
        before_state={"enabled": was},
        after_state={"enabled": bool(enabled)},
    )
    return get_team(company)


# ---- logo de la société --------------------------------------------------------------------------

LOGO_EXT = (".png", ".jpg", ".jpeg", ".webp")
LOGO_MAX_BYTES = 2 * 1024 * 1024


def set_company_logo(company: str, file_url: str) -> Dict[str, Any]:
    """Définit (ou retire) le logo de la société. Propriétaire seulement ; image PNG, JPEG ou WebP de 2 Mo au plus.

    Le logo s'affiche dans la barre latérale, sur les devis envoyés aux clients et à l'accueil : on en fait une copie
    publique sous un nom unique. Le SVG est refusé (il peut contenir du code)."""
    import os

    _require_team_admin(company)
    file_url = (file_url or "").strip()
    if not file_url:
        frappe.db.set_value("Company", company, "company_logo", None)
        AuditService.record_mutation(
            company=company,
            action="cortex.company.logo_changed",
            entity_type="Company",
            entity_id=company,
            after_state={"logo": None},
        )
        return {"logo": ""}
    if not file_url.lower().endswith(LOGO_EXT):
        raise SignupError("invalid_logo", "Choisissez une image PNG, JPEG ou WebP (le SVG n'est pas accepté).")
    name = frappe.db.get_value("File", {"file_url": file_url, "owner": frappe.session.user}, "name")
    if not name:
        raise SignupError("not_yours", "Cette image n'a pas été téléversée par vous.")
    file_doc = frappe.get_doc("File", name)
    content = file_doc.get_content()
    if len(content) > LOGO_MAX_BYTES:
        raise SignupError("logo_too_big", "Le logo dépasse 2 Mo : choisissez une image plus légère.")
    # On ne se fie pas à l'extension : les premiers octets doivent être ceux d'un PNG, d'un JPEG ou d'un WebP.
    if not defense.sniff_image(content):
        raise SignupError("invalid_logo", "Ce fichier n'est pas une vraie image PNG, JPEG ou WebP.")
    public = file_url
    if file_doc.is_private:
        copy = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"logo-{frappe.generate_hash(length=10)}{os.path.splitext(file_url)[1].lower()}",
                "content": content,
                "is_private": 0,
            }
        ).insert(ignore_permissions=True)
        file_doc.delete(ignore_permissions=True)
        public = copy.file_url
    frappe.db.set_value("Company", company, "company_logo", public)
    frappe.clear_cache(user=frappe.session.user)  # la barre latérale lit le logo au démarrage de la session
    AuditService.record_mutation(
        company=company,
        action="cortex.company.logo_changed",
        entity_type="Company",
        entity_id=company,
        after_state={"logo": public},
    )
    return {"logo": public}


# ---- appareils de l'équipe ------------------------------------------------------------------------


def team_devices(company: str) -> Dict[str, Any]:
    """Pour chaque membre, ses sessions actives (appareil, système, adresse IP, dernière activité)."""
    _require_team_admin(company)
    from cortex_rental.services import devices

    rows = []
    for row in frappe.get_all(
        "User",
        filters={"name": ["in", _member_emails(company) or [""]], "enabled": 1},
        fields=["name", "full_name"],
        order_by="full_name asc",
    ):
        sessions = devices.list_for(row.name, frappe.session.sid)["sessions"]
        rows.append(
            {
                "email": row.name,
                "full_name": row.full_name or row.name,
                "you": row.name == frappe.session.user,
                "sessions": sessions,
            }
        )
    return {"members": rows}


def sign_out_member(company: str, email: str, device_id: str = "") -> Dict[str, Any]:
    """Ferme les sessions d'un membre de l'équipe (un seul appareil, ou tous), avec une trace dans le journal d'audit."""
    _require_team_admin(company)
    _require_member(company, email)
    from cortex_rental.services import devices

    me = frappe.session.user
    if device_id:
        closed = devices.revoke(email, device_id, frappe.session.sid, by=me)["closed"]
    else:
        closed = devices.revoke_all(email, keep_sid=frappe.session.sid if email == me else None, by=me)
    AuditService.record_mutation(
        company=company,
        action="cortex.account.session_revoked",
        entity_type="User",
        entity_id=email,
        before_state=None,
        after_state={"closed": closed, "scope": "device" if device_id else "all", "by": me},
    )
    return {"closed": closed}


# ---- imports --------------------------------------------------------------------------------------


def get_imports(company: str) -> Dict[str, Any]:
    """Data Import history for this company's people, plus the targets the person may import into."""
    team = _member_emails(company)
    history = frappe.get_all(
        "Data Import",
        filters={"owner": ["in", team or [""]]},
        fields=["name", "reference_doctype", "import_type", "status", "creation", "owner"],
        order_by="creation desc",
        limit_page_length=20,
    )
    targets = [
        {
            "doctype": dt,
            "label": label,
            "description": description,
            "url": f"/app/data-import/new?reference_doctype={dt.replace(' ', '%20')}",
        }
        for dt, label, description in IMPORT_TARGETS
        if frappe.has_permission(dt, "import")
    ]
    return {
        "company": company,
        "targets": targets,
        "history": [
            {
                "name": h.name,
                "doctype": h.reference_doctype,
                "import_type": h.import_type,
                "status": h.status,
                "created": str(h.creation),
                "by": h.owner,
                "url": f"/app/data-import/{h.name}",
            }
            for h in history
        ],
    }
