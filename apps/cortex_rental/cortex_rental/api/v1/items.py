from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.audit import AuditService
from cortex_rental.services.agent_telemetry import log_tool_call


def search_items_handler(query: str, company: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Handler logic for item search."""
    if frappe:
        filters = {"company": company}
        if category:
            filters["category"] = category

        # Search profiles (Company-scoped: never return another tenant's catalog/rates)
        profiles = frappe.get_all(
            "Cortex Rental Item Profile",
            filters=filters,
            fields=["item_code", "item_name", "category", "daily_rate", "replacement_value", "deposit_required"],
        )

        results = []
        for p in profiles:
            if not query or query.lower() in p.item_code.lower() or query.lower() in (p.item_name or "").lower():
                results.append(
                    {
                        "id": p.item_code,
                        "item_code": p.item_code,
                        "name": p.item_name or p.item_code,
                        "category": p.category,
                        "daily_rate": float(p.daily_rate or 0.0),
                        "replacement_value": float(p.replacement_value or 0.0),
                        "deposit_required": float(p.deposit_required or 0.0),
                    }
                )
        return results

    # Fallback / Mock results for DX
    catalog = [
        {
            "id": "itm-alexa-35-pkg",
            "item_code": "itm-alexa-35-pkg",
            "name": "ARRI Alexa 35 Camera Package",
            "category": "Camera Bodies",
            "daily_rate": 1500.00,
            "replacement_value": 85000.00,
            "deposit_required": 5000.00,
        },
        {
            "id": "itm-cooke-s4i-set",
            "item_code": "itm-cooke-s4i-set",
            "name": "Cooke S4/i Prime Lens Set (6 Lenses)",
            "category": "Cinema Lenses",
            "daily_rate": 1200.00,
            "replacement_value": 110000.00,
            "deposit_required": 6000.00,
        },
        {
            "id": "itm-arri-skypanel-x21",
            "item_code": "itm-arri-skypanel-x21",
            "name": "ARRI SkyPanel X21 LED Softlight",
            "category": "Lighting",
            "daily_rate": 350.00,
            "replacement_value": 9500.00,
            "deposit_required": 1000.00,
        },
    ]
    if query:
        return [i for i in catalog if query.lower() in i["name"].lower() or query.lower() in i["item_code"].lower()]
    return catalog


if frappe:

    @frappe.whitelist(methods=["GET", "POST"])
    @log_tool_call("search_rental_items", scope="agent:items:read")
    def search_items(query: str = "", category: Optional[str] = None):
        require_agent_scope("agent:items:read")
        company = get_company_context()
        data = search_items_handler(query=query, company=company, category=category)
        AuditService.record_read(
            action="cortex.items.searched", metadata={"query": query, "count": len(data)}, company=company
        )
        return {"data": data, "meta": {"company": company, "count": len(data)}}
