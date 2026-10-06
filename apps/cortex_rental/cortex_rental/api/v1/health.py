"""Santé du service pour les orchestrateurs et la surveillance (sans compte, sans donnée sensible).

- `health`  : le processus répond (liveness).
- `ready`   : la base, le cache, les migrations et le planificateur sont en ordre (readiness); 503 si inutilisable.
"""

from typing import Any, Dict

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.services import defense
from cortex_rental.services import health as health_service


def health_check_handler() -> Dict[str, Any]:
    return health_service.liveness()


if frappe:

    @frappe.whitelist(methods=["GET"], allow_guest=True)
    @defense.safe_input
    @rate_limit(limit=600, seconds=60)
    def health():
        return health_check_handler()

    @frappe.whitelist(methods=["GET"], allow_guest=True)
    @defense.safe_input
    @rate_limit(limit=120, seconds=60)
    def ready():
        report = health_service.readiness()
        if report["status"] == "down":
            frappe.local.response["http_status_code"] = 503
        return report
