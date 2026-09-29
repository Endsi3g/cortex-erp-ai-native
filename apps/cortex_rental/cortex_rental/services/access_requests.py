"""Access-request workflow: submit -> verify email -> (approve) -> provision.

Design rules
- Responses to anonymous callers are identical whether or not an email is already known (no enumeration).
- The emailed token is stored only as a SHA-256 hash and expires; it embeds the request id.
- Approval is manual unless the site opts into "Automatic after email verification".
- Nobody receives `System Manager` here, and no password passes through this code.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
    from frappe.utils import add_to_date, get_datetime, now_datetime
except ImportError:
    frappe = None

from cortex_rental.services import access_emails, tenant_provisioning
from cortex_rental.services.audit import AuditService
from cortex_rental.services.signup_rules import (
    TEAM_SIZES,
    SignupError,
    check_domain_policy,
    clean_name,
    new_token,
    normalize_email,
    split_lines,
    split_token,
    token_matches,
)

DOCTYPE = "Cortex Signup Request"
RESEND_COOLDOWN_SECONDS = 60
MAX_RESENDS = 5

GENERIC_RECEIVED = {"status": "check_email", "cooldown_seconds": RESEND_COOLDOWN_SECONDS}


def get_settings() -> Any:
    return frappe.get_cached_doc("Cortex Access Settings")


def signup_enabled() -> bool:
    return bool(frappe and frappe.db.exists("DocType", "Cortex Access Settings") and get_settings().signup_enabled)


def submit_request(payload: Dict[str, Any], ip: Optional[str]) -> Dict[str, Any]:
    """Anonymous entry point. Validates, stores and emails; always answers `check_email`."""
    settings = get_settings()
    if not settings.signup_enabled:
        raise SignupError("signup_disabled", "Les demandes d'accès sont fermées pour le moment.")
    if payload.get("website"):  # honeypot: humans never fill it, bots do
        return dict(GENERIC_RECEIVED)

    email = normalize_email(payload.get("email"))
    full_name = clean_name(payload.get("full_name"), "Le nom")
    company_name = clean_name(payload.get("company_name"), "Le nom de l'entreprise")
    job_title = clean_name(payload.get("job_title"), "La fonction") if payload.get("job_title") else ""
    team_size = payload.get("team_size") or ""
    if team_size not in TEAM_SIZES:
        team_size = ""
    if not payload.get("accept_terms"):
        raise SignupError("terms", "Acceptez les conditions d'utilisation pour continuer.")
    check_domain_policy(email, split_lines(settings.allowed_email_domains), bool(settings.block_free_email_domains))

    if frappe.db.exists("User", email):
        access_emails.send_account_exists(email, full_name)
        return dict(GENERIC_RECEIVED)

    existing = frappe.db.get_value(DOCTYPE, {"email": email}, ["name", "status"], as_dict=True)
    if existing:
        if existing.status == "Pending Verification":
            _issue_and_send(existing.name, resend=True)
        return dict(GENERIC_RECEIVED)

    request = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "full_name": full_name,
            "email": email,
            "company_name": company_name,
            "job_title": job_title,
            "team_size": team_size,
            "status": "Pending Verification",
            "ip_address": ip,
        }
    )
    request.flags.ignore_permissions = True
    request.insert()
    _issue_and_send(request.name)
    return dict(GENERIC_RECEIVED)


def _issue_and_send(name: str, resend: bool = False) -> bool:
    """Create a fresh token and email it. Returns False when throttled (cooldown or resend cap)."""
    request = frappe.get_doc(DOCTYPE, name)
    now = now_datetime()
    if resend:
        last = request.verification_sent_on
        if last and (now - get_datetime(last)).total_seconds() < RESEND_COOLDOWN_SECONDS:
            return False
        if int(request.resend_count or 0) >= MAX_RESENDS:
            return False
        request.resend_count = int(request.resend_count or 0) + 1
    hours = int(get_settings().verification_hours or 48)
    token, digest = new_token(request.name)
    request.token_hash = digest
    request.verification_sent_on = now
    request.expires_on = add_to_date(now, hours=hours)
    sent = access_emails.send_verification(request.email, request.full_name, request.company_name, token, hours)
    request.mail_status = (
        "En file d'envoi" if sent else "Échec : aucun compte courriel sortant n'est configuré ou l'envoi a échoué"
    )
    request.flags.ignore_permissions = True
    request.save()
    return True


def resend_verification(token: str) -> Dict[str, Any]:
    """Resend from the expired-link page. Same answer whatever happens."""
    try:
        request_id, _secret = split_token(token)
        if frappe.db.get_value(DOCTYPE, request_id, "status") == "Pending Verification":
            _issue_and_send(request_id, resend=True)
    except SignupError:
        pass
    return dict(GENERIC_RECEIVED)


def verify_token(token: str) -> Dict[str, Any]:
    """Result of clicking the emailed link: {state, ...}. Never raises for a bad link."""
    try:
        request_id, secret = split_token(token)
    except SignupError:
        return {"state": "invalid"}
    row = frappe.db.get_value(
        DOCTYPE, request_id, ["name", "status", "token_hash", "expires_on", "email", "company_name"], as_dict=True
    )
    if not row or not token_matches(secret, row.token_hash):
        return {"state": "invalid"}
    if row.status in ("Pending Approval", "Provisioned", "Rejected"):
        return {"state": "already_verified", "status": row.status, "company_name": row.company_name}
    if row.expires_on and get_datetime(row.expires_on) < now_datetime():
        return {"state": "expired", "token": token}

    request = frappe.get_doc(DOCTYPE, request_id)
    request.status = "Pending Approval"
    request.verified_on = now_datetime()
    request.token_hash = ""  # single use
    request.flags.ignore_permissions = True
    request.save()
    # The link is opened with a GET, which Frappe does not commit on its own.
    frappe.db.commit()  # nosemgrep
    if get_settings().approval_mode == "Automatic after email verification":
        provision(request.name, decided_by="Administrator")
        frappe.db.commit()  # nosemgrep
        return {"state": "verified", "next": "password", "company_name": request.company_name}
    _notify_admins(request)
    frappe.db.commit()  # nosemgrep
    return {"state": "verified", "next": "approval", "company_name": request.company_name}


def _admin_recipients() -> List[str]:
    configured = get_settings().notify_email
    if configured:
        return [configured]
    users = frappe.get_all(
        "Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent", limit_page_length=50
    )
    emails = frappe.get_all(
        "User",
        filters=[
            ["name", "in", users],
            ["name", "!=", "Administrator"],
            ["enabled", "=", 1],
            ["user_type", "=", "System User"],
        ],
        pluck="email",
    )
    return [e for e in emails if e and not e.endswith("@example.com")]


def _notify_admins(request: Any) -> None:
    try:
        access_emails.send_admin_notice(
            _admin_recipients(),
            {
                "name": request.name,
                "full_name": request.full_name,
                "email": request.email,
                "company_name": request.company_name,
                "job_title": request.job_title or "",
                "team_size": request.team_size or "",
            },
        )
    except Exception:
        # The request stays visible in the desk list; a mail failure must not block the applicant.
        frappe.log_error(title="Cortex access request: admin notice failed")


def _require_approver() -> None:
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Seul un System Manager peut décider d'une demande d'accès.", frappe.PermissionError)


def approve_request(name: str) -> Dict[str, Any]:
    _require_approver()
    return provision(name, decided_by=frappe.session.user)


def provision(name: str, decided_by: str) -> Dict[str, Any]:
    request = frappe.get_doc(DOCTYPE, name)
    if request.status != "Pending Approval":
        frappe.throw("Cette demande n'est pas en attente d'approbation.", frappe.ValidationError)
    if frappe.db.exists("User", request.email):
        frappe.throw(
            f"Un utilisateur {request.email} existe déjà : refusez la demande ou supprimez d'abord ce compte.",
            frappe.DuplicateEntryError,
        )
    settings = get_settings()
    company = tenant_provisioning.create_company(request.company_name)
    roles = split_owner_roles(settings.owner_roles)
    user = tenant_provisioning.create_user(request.email, request.full_name, company, roles)
    tenant_provisioning.ensure_onboarding(company, user)

    request.status = "Provisioned"
    request.company = company
    request.user = user
    request.decided_by = decided_by
    request.decided_on = now_datetime()
    request.flags.ignore_permissions = True
    request.save()
    AuditService.record_mutation(
        company=company,
        action="cortex.access.provisioned",
        entity_type=DOCTYPE,
        entity_id=request.name,
        after_state={"company": company, "user": user, "roles": roles, "decided_by": decided_by},
    )
    link = tenant_provisioning.password_setup_link(user)
    welcome_sent = access_emails.send_welcome(user, request.full_name, company, link)
    result = {
        "status": "Provisioned",
        "company": company,
        "user": user,
        "welcome_email": "queued" if welcome_sent else "failed",
    }
    if not welcome_sent:
        # Fallback for the approving admin only: hand the one-time password link over manually.
        result["setup_link"] = link
    return result


def split_owner_roles(value: Optional[str]) -> List[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def resend_verification_as_admin(name: str) -> Dict[str, Any]:
    _require_approver()
    if frappe.db.get_value(DOCTYPE, name, "status") != "Pending Verification":
        frappe.throw("Cette demande n'attend plus de vérification.", frappe.ValidationError)
    _issue_and_send(name)
    return {"mail_status": frappe.db.get_value(DOCTYPE, name, "mail_status")}


def reject_request(name: str, reason: str = "") -> Dict[str, Any]:
    _require_approver()
    request = frappe.get_doc(DOCTYPE, name)
    if request.status not in ("Pending Approval", "Pending Verification"):
        frappe.throw("Cette demande a déjà été traitée.", frappe.ValidationError)
    request.status = "Rejected"
    request.rejection_reason = (reason or "").strip()
    request.decided_by = frappe.session.user
    request.decided_on = now_datetime()
    request.token_hash = ""
    request.flags.ignore_permissions = True
    request.save()
    access_emails.send_rejection(request.email, request.full_name, request.company_name, request.rejection_reason)
    return {"status": "Rejected"}
