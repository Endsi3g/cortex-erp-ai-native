"""Global search for the Cortex command bar (⌘K).

Human staff only. Every lookup is scoped to the server-resolved Company and
goes through `frappe.get_list`, so DocType permissions and the Cortex
permission query hooks apply on top of the explicit Company filter.
"""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role

MIN_QUERY_LENGTH = 2
PER_GROUP_LIMIT = 5


def _like(query: str) -> str:
    return f"%{query}%"


def search_handler(query: str, company: str) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if len(query) < MIN_QUERY_LENGTH:
        return []
    token = _like(query)
    results: List[Dict[str, Any]] = []

    rentals = frappe.get_list(
        "Cortex Rental Transaction",
        filters={"company": company},
        or_filters=[["name", "like", token], ["customer", "like", token], ["project_name", "like", token]],
        fields=["name", "customer", "rental_state", "project_name"],
        order_by="modified desc",
        limit_page_length=PER_GROUP_LIMIT,
    )
    for row in rentals:
        results.append(
            {
                "type": "rental",
                "id": row.name,
                "title": row.name,
                "subtitle": " · ".join(part for part in (row.customer, row.project_name, row.rental_state) if part),
            }
        )

    customers = frappe.get_list(
        "Customer",
        filters={"cortex_company": company, "disabled": 0},
        or_filters=[["name", "like", token], ["customer_name", "like", token]],
        fields=["name", "customer_name"],
        order_by="customer_name asc",
        limit_page_length=PER_GROUP_LIMIT,
    )
    for row in customers:
        results.append(
            {
                "type": "customer",
                "id": row.name,
                "title": row.customer_name or row.name,
                "subtitle": row.name if row.customer_name and row.customer_name != row.name else "",
            }
        )

    equipment = frappe.get_list(
        "Cortex Rental Item Profile",
        filters={"company": company},
        or_filters=[["item_code", "like", token], ["item_name", "like", token]],
        fields=["item_code", "item_name", "category"],
        order_by="item_name asc",
        limit_page_length=PER_GROUP_LIMIT,
    )
    for row in equipment:
        results.append(
            {
                "type": "equipment",
                "id": row.item_code,
                "title": row.item_name or row.item_code,
                "subtitle": " · ".join(part for part in (row.item_code, row.category) if part),
            }
        )

    serials = frappe.get_list(
        "Serial No",
        filters={"company": company, "name": ["like", token]},
        fields=["name", "item_code", "cortex_status"],
        order_by="name asc",
        limit_page_length=PER_GROUP_LIMIT,
    )
    for row in serials:
        results.append(
            {
                "type": "serial",
                "id": row.name,
                "title": row.name,
                "subtitle": " · ".join(part for part in (row.item_code, row.cortex_status or "Active") if part),
            }
        )

    return results


if frappe:

    @frappe.whitelist(methods=["GET"])
    def global_search(query: str = ""):
        require_human_staff_role()
        company = get_company_context()
        return {"data": {"query": query, "results": search_handler(query, company)}, "meta": {"company": company}}
