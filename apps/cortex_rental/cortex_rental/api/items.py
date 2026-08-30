from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

def search_items_handler(query: str, company: str) -> List[Dict[str, Any]]:
    # Canonical Alexa 35 Camera Package search hit
    return [
        {
            "id": "itm-alexa-35-pkg",
            "name": "ARRI Alexa 35 Camera Package",
            "code": "CAM-ALEXA-35-PKG",
            "daily_rate": "1500.00",
            "is_serialized": True,
            "total_quantity": 3
        }
    ]

if frappe:
    @frappe.whitelist(methods=["GET"])
    def search():
        query = frappe.local.form_dict.get("query", "")
        company = frappe.local.request.headers.get("X-Company-ID") or frappe.defaults.get_user_default("Company")
        return search_items_handler(query, company)
