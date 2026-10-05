"""Compte de la personne connectée : profil, sécurité, sessions, notifications, société et activité.

Tout s'applique à la personne connectée seulement (jamais à une autre) : aucun paramètre ne désigne un autre
utilisateur. La société et les rôles sont lus, jamais modifiés ici (l'administration d'équipe a son propre écran).
"""

import re
from typing import Any, Dict, List

try:
    import frappe
    from frappe.utils import cint
except ImportError:
    frappe = None

NOTIFICATION_FIELDS = {
    "enable_email_notifications": "Recevoir des courriels de notification",
    "enable_email_mention": "Quand on me mentionne",
    "enable_email_assignment": "Quand une tâche m'est assignée",
    "enable_email_share": "Quand on partage un document avec moi",
    "enable_email_event_reminders": "Rappels d'événements",
}
MIN_PASSWORD = 10
NAME_LIMIT = 80
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,20}$")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _user() -> str:
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        frappe.throw("Cette page s'adresse à une personne connectée avec son propre compte.", frappe.PermissionError)
    return user


def _roles_label(user: str) -> List[str]:
    """Rôles Cortex de la personne (les rôles techniques de Frappe ne sont pas montrés)."""
    roles = frappe.get_roles(user)
    return sorted(r for r in roles if r.startswith("Cortex ") or r in ("Rental Manager", "Rental Operator", "Auditor"))


def get_account() -> Dict[str, Any]:
    user = _user()
    doc = frappe.db.get_value(
        "User",
        user,
        [
            "first_name",
            "last_name",
            "full_name",
            "mobile_no",
            "user_image",
            "language",
            "time_zone",
            "creation",
            "last_login",
        ],
        as_dict=True,
    )
    from cortex_rental.permissions.agent_scopes import get_company_context

    try:
        company = get_company_context()
    except Exception:
        company = ""
    return {
        "email": user,
        "first_name": doc.first_name or "",
        "last_name": doc.last_name or "",
        "full_name": doc.full_name or user,
        "mobile_no": doc.mobile_no or "",
        "image": doc.user_image or "",
        "language": "fr",
        "time_zone": doc.time_zone or frappe.db.get_single_value("System Settings", "time_zone") or "",
        "member_since": str(doc.creation)[:10],
        "last_login": str(doc.last_login or "")[:16],
        "company": company,
        "roles": _roles_label(user),
        "notifications": get_notifications(user),
    }


def update_profile(first_name: str, last_name: str = "", mobile_no: str = "") -> Dict[str, Any]:
    user = _user()
    first = " ".join((first_name or "").split())[:NAME_LIMIT]
    last = " ".join((last_name or "").split())[:NAME_LIMIT]
    phone = (mobile_no or "").strip()
    if len(first) < 1:
        frappe.throw("Le prénom est obligatoire.", frappe.ValidationError)
    if phone and not PHONE_RE.match(phone):
        frappe.throw("Le numéro de téléphone n'est pas valide.", frappe.ValidationError)
    # Écriture ciblée : seuls ces trois champs de sa propre fiche, jamais rôles ni société.
    frappe.db.set_value(
        "User",
        user,
        {"first_name": first, "last_name": last, "full_name": f"{first} {last}".strip(), "mobile_no": phone},
    )
    frappe.clear_cache(user=user)
    return get_account()


def update_photo(file_url: str) -> Dict[str, Any]:
    user = _user()
    file_url = (file_url or "").strip()
    if file_url:
        if not file_url.lower().endswith(IMAGE_EXT):
            frappe.throw("Choisissez une image (PNG, JPEG, WebP ou GIF).", frappe.ValidationError)
        owner = frappe.db.get_value("File", {"file_url": file_url}, "owner")
        if owner != user:
            frappe.throw("Cette image n'a pas été téléversée par vous.", frappe.PermissionError)
    frappe.db.set_value("User", user, "user_image", file_url or None)
    frappe.clear_cache(user=user)
    return {"image": file_url}


def change_password(old_password: str, new_password: str) -> Dict[str, Any]:
    from frappe.utils.password import check_password, update_password

    user = _user()
    try:
        check_password(user, old_password or "")
    except frappe.AuthenticationError:
        frappe.throw("Le mot de passe actuel est incorrect.", frappe.ValidationError)
    new = new_password or ""
    if len(new) < MIN_PASSWORD:
        frappe.throw(
            f"Le nouveau mot de passe doit contenir au moins {MIN_PASSWORD} caractères.", frappe.ValidationError
        )
    if new == old_password:
        frappe.throw("Le nouveau mot de passe doit être différent de l'ancien.", frappe.ValidationError)
    from frappe.core.doctype.user.user import test_password_strength

    verdict = test_password_strength(new)
    feedback = (verdict or {}).get("feedback") or {}
    if feedback.get("password_policy_validation_passed") is False:
        frappe.throw(
            "Ce mot de passe est trop facile à deviner. Ajoutez des mots ou des chiffres.", frappe.ValidationError
        )
    update_password(user, new)
    closed = sign_out_other_sessions()["closed"]
    return {"changed": True, "other_sessions_closed": closed}


def list_sessions() -> Dict[str, Any]:
    user = _user()
    rows = frappe.db.sql(
        "SELECT sid, ipaddress, lastupdate FROM `tabSessions` WHERE user=%s ORDER BY lastupdate DESC",
        (user,),
        as_dict=True,
    )
    current = frappe.session.sid
    return {
        "sessions": [
            {
                "id": r.sid[-6:],
                "current": r.sid == current,
                "ip": r.ipaddress or "",
                "last_active": str(r.lastupdate)[:16],
            }
            for r in rows
        ]
    }


def sign_out_other_sessions() -> Dict[str, Any]:
    user = _user()
    others = frappe.db.sql("SELECT sid FROM `tabSessions` WHERE user=%s AND sid!=%s", (user, frappe.session.sid))
    from frappe.sessions import delete_session

    for (sid,) in others:
        delete_session(sid, reason="Session Expired")
    return {"closed": len(others)}


def get_notifications(user: str = "") -> Dict[str, Any]:
    user = user or _user()
    values = {key: 1 for key in NOTIFICATION_FIELDS}
    if frappe.db.exists("Notification Settings", user):
        row = frappe.db.get_value("Notification Settings", user, list(NOTIFICATION_FIELDS), as_dict=True) or {}
        values.update({k: cint(row.get(k)) for k in NOTIFICATION_FIELDS if row.get(k) is not None})
    return {"labels": NOTIFICATION_FIELDS, "values": values}


def update_notifications(values: Dict[str, Any]) -> Dict[str, Any]:
    user = _user()
    clean = {k: 1 if cint(values.get(k)) else 0 for k in NOTIFICATION_FIELDS if k in (values or {})}
    if not clean:
        frappe.throw("Aucun réglage à enregistrer.", frappe.ValidationError)
    from frappe.desk.doctype.notification_settings.notification_settings import create_notification_settings

    create_notification_settings(user)
    frappe.db.set_value("Notification Settings", user, clean)
    return get_notifications(user)


def my_activity(limit: int = 15) -> Dict[str, Any]:
    from cortex_rental.permissions.agent_scopes import get_company_context
    from cortex_rental.services import team_activity

    user = _user()
    company = get_company_context()
    rows = frappe.get_all(
        "Audit Event",
        filters={"company": company, "actor_id": user, "action": ["in", list(team_activity.ACTION_TEXT)]},
        fields=["action", "entity_type", "entity_id", "creation"],
        order_by="creation desc",
        limit_page_length=max(1, min(int(limit or 15), 50)),
    )
    return {
        "activity": [
            {
                "text": team_activity.action_text(r.action),
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "at": str(r.creation)[:16],
            }
            for r in rows
        ]
    }


def ai_usage() -> Dict[str, Any]:
    """Consommation d'IA du mois pour la société (seulement si la personne a le droit de lire l'usage)."""
    if not frappe.has_permission("Cortex AI Usage", "read"):
        return {"visible": False}
    from cortex_rental.permissions.agent_scopes import get_company_context
    from cortex_rental.services.ai import budget, settings as ai_settings

    status = budget.status(get_company_context(), ai_settings.load())
    return {"visible": True, **status}
