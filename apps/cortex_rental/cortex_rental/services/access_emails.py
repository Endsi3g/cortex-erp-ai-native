"""Emails of the access flow, rendered from templates/emails/cortex_*.html inside Frappe's layout."""

from typing import Any, Dict, Iterable, Optional

try:
    import frappe
    from frappe.utils import get_url
except ImportError:
    frappe = None

BRAND = "Cortex"


def _send(recipients: Iterable[str], subject: str, template: str, args: Dict[str, Any]) -> bool:
    """Queue the email. Returns False (and logs) when the site has no outgoing account or it fails:
    a mail problem must never fail the visitor's request; admins see the status on the request."""
    try:
        frappe.sendmail(
            recipients=list(recipients),
            subject=subject,
            template=template,
            args={"brand": BRAND, "site_url": get_url(), **args},
            delayed=False,
        )
        return True
    except Exception:
        frappe.clear_messages()
        frappe.log_error(title=f"Cortex access email failed: {template}")
        return False


def send_verification(email: str, full_name: str, company_name: str, token: str, hours: int) -> bool:
    link = get_url(f"/cortex-verify?token={token}")
    return _send(
        [email],
        f"Confirmez votre courriel pour {BRAND}",
        "cortex_verify_email",
        {"full_name": full_name, "company_name": company_name, "link": link, "hours": hours},
    )


def send_account_exists(email: str, full_name: str) -> bool:
    return _send(
        [email],
        f"Vous avez déjà un compte {BRAND}",
        "cortex_account_exists",
        {"full_name": full_name, "login_url": get_url("/login"), "reset_url": get_url("/login#forgot")},
    )


def send_admin_notice(recipients: Iterable[str], request: Dict[str, Any]) -> bool:
    to = [r for r in recipients if r]
    if not to:
        return False
    return _send(
        to,
        f"Nouvelle demande d'accès : {request['company_name']}",
        "cortex_access_admin_notice",
        {**request, "review_url": get_url(f"/app/cortex-signup-request/{request['name']}")},
    )


def send_welcome(email: str, full_name: str, company_name: str, link: str) -> bool:
    return _send(
        [email],
        f"Votre espace {BRAND} est prêt",
        "cortex_welcome",
        {
            "email": email,
            "full_name": full_name,
            "company_name": company_name,
            "link": link,
            "login_url": get_url("/login"),
        },
    )


def send_rejection(email: str, full_name: str, company_name: str, reason: Optional[str]) -> bool:
    return _send(
        [email],
        f"Votre demande d'accès {BRAND}",
        "cortex_access_rejected",
        {"full_name": full_name, "company_name": company_name, "reason": reason or ""},
    )


def send_team_invite(
    email: str, full_name: str, company_name: str, invited_by: str, role_label: str, link: str
) -> bool:
    return _send(
        [email],
        f"{invited_by} vous invite sur {BRAND}",
        "cortex_team_invite",
        {
            "full_name": full_name,
            "company_name": company_name,
            "invited_by": invited_by,
            "role_label": role_label,
            "link": link,
        },
    )
