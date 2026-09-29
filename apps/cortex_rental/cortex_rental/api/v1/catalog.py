"""Read-only fleet catalogue for the Cortex UI: equipment, serial numbers and kits.

Quantities are derived from Serial No `cortex_status` and from open rental
transactions. A value the ERP does not hold (brand, weekly/monthly rates, image,
maintenance dates) is omitted from the payload, never estimated.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1._shared import envelope, page_args, split_lines, to_float
from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role

# Serial No.cortex_status -> status shown by the UI.
SERIAL_STATUS = {
    "Active": "Available",
    "Quarantine": "Quarantine",
    "Under Repair": "Repair",
    "Missing": "Missing",
    "Decommissioned": "Decommissioned",
}
MAINTENANCE = {"Quarantine", "Under Repair"}
OUT_STATES = ("Checked Out",)
RESERVED_STATES = ("Reservation", "Contract")
PROFILE_FIELDS = [
    "name",
    "item_code",
    "item_name",
    "category",
    "daily_rate",
    "is_serialized",
    "total_quantity",
    "required_accessories",
    "modified",
]


def _currency(company: str) -> str:
    return frappe.db.get_value("Company", company, "default_currency") or "CAD"


def _serial_counts(company: str, item_codes: List[str]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    if not item_codes:
        return counts
    rows = frappe.get_all(
        "Serial No",
        filters={"item_code": ["in", item_codes], "company": company},
        fields=["item_code", "cortex_status"],
        limit_page_length=0,
    )
    for row in rows:
        counts[row.item_code][row.cortex_status or "Active"] += 1
    return counts


def _rented_quantities(company: str, item_codes: List[str]) -> Dict[str, float]:
    """Units currently out: quantity minus returned quantity on 'Checked Out' transactions."""
    rented: Dict[str, float] = defaultdict(float)
    if not item_codes:
        return rented
    open_names = frappe.get_all(
        "Cortex Rental Transaction",
        filters={"company": company, "rental_state": ["in", list(OUT_STATES)]},
        pluck="name",
        limit_page_length=0,
    )
    if not open_names:
        return rented
    lines = frappe.get_all(
        "Cortex Rental Transaction Item",
        filters={"parent": ["in", open_names], "item_code": ["in", item_codes]},
        fields=["item_code", "qty", "returned_qty"],
        limit_page_length=0,
    )
    for line in lines:
        rented[line.item_code] += max(0.0, to_float(line.qty) - to_float(line.returned_qty))
    return rented


def serialize_equipment(profile: Any, serials: Dict[str, int], rented: float, currency: str) -> Dict[str, Any]:
    is_serialized = bool(profile.is_serialized)
    total = sum(serials.values()) if is_serialized else int(profile.total_quantity or 0)
    maintenance = sum(n for status, n in serials.items() if status in MAINTENANCE)
    unavailable = maintenance + serials.get("Missing", 0) + serials.get("Decommissioned", 0)
    rented_qty = int(rented)
    return {
        "item_code": profile.item_code,
        "item_name": profile.item_name or profile.item_code,
        "category": profile.category or "Uncategorized",
        "daily_rate": to_float(profile.daily_rate),
        "currency": currency,
        "is_serialized": is_serialized,
        "total_fleet_quantity": total,
        "rented_quantity": rented_qty,
        "maintenance_quantity": maintenance,
        "available_quantity": max(0, total - rented_qty - unavailable),
        "required_accessories": split_lines(profile.required_accessories),
    }


def list_equipment_handler(company: str, category: Optional[str], search: Optional[str], page: int, page_size: int):
    filters: Dict[str, Any] = {"company": company}
    if category:
        filters["category"] = category
    or_filters = None
    if search and search.strip():
        token = f"%{search.strip()}%"
        or_filters = [["item_code", "like", token], ["item_name", "like", token]]
    total = frappe.db.count("Cortex Rental Item Profile", filters=filters)
    profiles = frappe.get_list(
        "Cortex Rental Item Profile",
        filters=filters,
        or_filters=or_filters,
        fields=PROFILE_FIELDS,
        order_by="item_name asc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    codes = [p.item_code for p in profiles]
    serials, rented, currency = _serial_counts(company, codes), _rented_quantities(company, codes), _currency(company)
    items = [
        serialize_equipment(p, serials.get(p.item_code, {}), rented.get(p.item_code, 0.0), currency) for p in profiles
    ]
    return {"items": items, "total_count": total}


def _owned_profile(item_code: str, company: str):
    rows = frappe.get_list(
        "Cortex Rental Item Profile",
        filters={"company": company, "item_code": item_code},
        fields=PROFILE_FIELDS,
        page_length=1,
    )
    if not rows:
        frappe.throw("Équipement introuvable.", frappe.DoesNotExistError)
    return rows[0]


def get_equipment_handler(company: str, item_code: str) -> Dict[str, Any]:
    profile = _owned_profile(item_code, company)
    serials = _serial_counts(company, [item_code]).get(item_code, {})
    rented = _rented_quantities(company, [item_code]).get(item_code, 0.0)
    payload = serialize_equipment(profile, serials, rented, _currency(company))
    units = frappe.get_list(
        "Serial No",
        filters={"item_code": item_code, "company": company},
        fields=["name", "cortex_status", "warehouse"],
        order_by="name asc",
        page_length=200,
    )
    payload["serials"] = [
        {
            "serial_number": u.name,
            "status": SERIAL_STATUS.get(u.cortex_status or "Active", "Available"),
            **({"warehouse": u.warehouse} if u.warehouse else {}),
        }
        for u in units
    ]
    return payload


def get_serial_handler(company: str, serial_number: str) -> Dict[str, Any]:
    if not frappe.has_permission("Serial No", "read", serial_number):
        frappe.throw("Numéro de série introuvable.", frappe.PermissionError)
    serial = frappe.get_doc("Serial No", serial_number)
    if serial.get("company") != company:
        frappe.throw("Numéro de série introuvable.", frappe.PermissionError)
    status = SERIAL_STATUS.get(serial.get("cortex_status") or "Active", "Available")
    active = frappe.get_all(
        "Cortex Rental Transaction Item",
        filters={"serial_no": serial_number},
        fields=["parent"],
        limit_page_length=20,
    )
    if active:
        states = frappe.get_all(
            "Cortex Rental Transaction",
            filters={"name": ["in", [row.parent for row in active]], "company": company},
            pluck="rental_state",
        )
        if any(state in OUT_STATES for state in states):
            status = "Checked Out"
        elif status == "Available" and any(state in RESERVED_STATES for state in states):
            status = "Reserved"
    payout = frappe.get_all(
        "Consignment Payout",
        filters={"serial_no": serial_number, "company": company},
        fields=["owner", "consignment_percentage"],
        order_by="creation desc",
        page_length=1,
    )
    payload: Dict[str, Any] = {
        "serial_number": serial.name,
        "item_code": serial.item_code,
        "item_name": serial.get("item_name") or serial.item_code,
        "status": status,
        "is_consigned": bool(payout) or serial.get("cortex_ownership") == "Consignment",
    }
    if serial.get("warehouse"):
        payload["warehouse"] = serial.warehouse
    if payout:
        payload["owner_id"] = payout[0].owner
        payload["consignment_rate"] = to_float(payout[0].consignment_percentage)
    return payload


def list_kits_handler(company: str, category: Optional[str]) -> Dict[str, Any]:
    """Kits are ERPNext Product Bundles whose parent item has a rental profile in this company."""
    profiles = frappe.get_all(
        "Cortex Rental Item Profile",
        filters={"company": company},
        fields=["item_code", "item_name", "category"],
        limit_page_length=0,
    )
    names = {p.item_code: p for p in profiles}
    if not names:
        return {"kits": [], "total_count": 0}
    bundles = frappe.get_all(
        "Product Bundle",
        filters={"new_item_code": ["in", list(names)], "disabled": 0},
        fields=["name", "new_item_code"],
        limit_page_length=0,
    )
    kits = []
    for bundle in bundles:
        parent = names[bundle.new_item_code]
        if category and parent.category != category:
            continue
        doc = frappe.get_doc("Product Bundle", bundle.name)
        kits.append(
            {
                "kit_code": bundle.new_item_code,
                "kit_name": parent.item_name or bundle.new_item_code,
                "category": parent.category or "Uncategorized",
                "components": [
                    {
                        "item_code": row.item_code,
                        "item_name": (names.get(row.item_code).item_name if row.item_code in names else None)
                        or row.description
                        or row.item_code,
                        "quantity": to_float(row.qty),
                    }
                    for row in doc.items
                ],
            }
        )
    return {"kits": kits, "total_count": len(kits)}


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_equipment(category: str = None, search: str = None, page: int = 1, page_size: int = 20):
        require_human_staff_role()
        page, page_size = page_args(page, page_size)
        return envelope(list_equipment_handler(get_company_context(), category, search, page, page_size))

    @frappe.whitelist(methods=["GET"])
    def get_equipment(item_code: str):
        require_human_staff_role()
        return envelope(get_equipment_handler(get_company_context(), item_code))

    @frappe.whitelist(methods=["GET"])
    def get_serial(serial_number: str):
        require_human_staff_role()
        return envelope(get_serial_handler(get_company_context(), serial_number))

    @frappe.whitelist(methods=["GET"])
    def list_kits(category: str = None):
        require_human_staff_role()
        return envelope(list_kits_handler(get_company_context(), category))
