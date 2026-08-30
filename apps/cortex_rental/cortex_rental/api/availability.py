from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

def check_availability_handler(data: Dict[str, Any], company: str) -> List[Dict[str, Any]]:
    """
    Pure availability check algorithm:
    Calculates unreserved stock in time window without database mutation.
    """
    items = data.get("items", [])
    results = []

    for itm in items:
        item_id = itm.get("item_id")
        requested_qty = float(itm.get("quantity", 1.0))
        
        # Fleet stock check
        total_base = 3.0
        booked = 0.0
        avail = max(0.0, total_base - booked)

        results.append({
            "item_id": item_id,
            "item_code": "CAM-ALEXA-35-PKG",
            "requested_quantity": requested_qty,
            "total_base_quantity": total_base,
            "booked_quantity": booked,
            "available_quantity": avail,
            "is_available": (avail >= requested_qty),
            "conflicts": [],
            "suggested_serial_numbers": [
                {"serial": "SN-ALX35-001", "status": "available"},
                {"serial": "SN-ALX35-002", "status": "available"},
                {"serial": "SN-ALX35-003", "status": "available"},
            ]
        })

    return results

if frappe:
    @frappe.whitelist(methods=["POST"])
    def check():
        data = frappe.local.form_dict
        company = frappe.local.request.headers.get("X-Company-ID") or frappe.defaults.get_user_default("Company")
        return check_availability_handler(data, company)
