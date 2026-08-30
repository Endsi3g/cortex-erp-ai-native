from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None


def health_check_handler() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "cortex_rental",
        "version": "1.0.0",
        "database": "MariaDB 10.11+",
        "framework": "Frappe Framework / ERPNext v15+",
    }


if frappe:

    @frappe.whitelist(methods=["GET"], allow_guest=True)
    def health():
        return health_check_handler()
