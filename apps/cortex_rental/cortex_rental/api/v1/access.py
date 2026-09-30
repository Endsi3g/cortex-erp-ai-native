"""Public (guest) endpoints of the access flow: request access, resend the verification link.

Guests can reach only these two calls; each is rate-limited per IP and answers identically whether or
not the email is already known. See services/access_requests.py for the rules.
"""

from typing import Any, Callable, Dict

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.services import access_requests
from cortex_rental.services.signup_rules import SignupError


def guarded(action: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Turn a rule failure into `{ok: false, code, message}` so the form can show it inline."""
    try:
        return {"ok": True, **action()}
    except SignupError as error:
        return {"ok": False, "code": error.code, "message": str(error)}


if frappe:

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @rate_limit(limit=8, seconds=60 * 60)
    def request_access(
        full_name: str = "",
        email: str = "",
        company_name: str = "",
        job_title: str = "",
        team_size: str = "",
        accept_terms: int = 0,
        website: str = "",
    ):
        payload = {
            "full_name": full_name,
            "email": email,
            "company_name": company_name,
            "job_title": job_title,
            "team_size": team_size,
            "accept_terms": int(accept_terms or 0),
            "website": website,
        }
        return guarded(lambda: access_requests.submit_request(payload, getattr(frappe.local, "request_ip", None)))

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @rate_limit(limit=10, seconds=60 * 60)
    def resend_verification(token: str = ""):
        return guarded(lambda: access_requests.resend_verification(token))

    @frappe.whitelist(allow_guest=True, methods=["GET"])
    def access_status():
        """Whether the login page should offer « Demander l'accès » (no secret, cacheable)."""
        return {"signup_enabled": access_requests.signup_enabled()}
