from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_agent_scope, get_company_context
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency


def search_customers_handler(query: str, company: str) -> List[Dict[str, Any]]:
    if frappe:
        customers = frappe.get_all(
            "Customer",
            filters={"disabled": 0, "cortex_company": company},
            fields=["name", "customer_name", "customer_group", "territory", "custom_insurance_valid_until"]
        )
        results = []
        for c in customers:
            if not query or query.lower() in c.name.lower() or query.lower() in c.customer_name.lower():
                results.append({
                    "id": c.name,
                    "name": c.customer_name or c.name,
                    "customer_group": c.customer_group,
                    "territory": c.territory,
                    "insurance_valid": bool(c.get("custom_insurance_valid_until"))
                })
        return results

    # Mock catalog
    custs = [
        {"id": "cust-dune3-01", "name": "Dune 3 Productions Inc.", "customer_group": "Commercial Production", "territory": "Canada", "insurance_valid": True},
        {"id": "cust-netflix-02", "name": "Horizon Cinema Services LLC", "customer_group": "Feature Film", "territory": "United States", "insurance_valid": True},
    ]
    if query:
        return [c for c in custs if query.lower() in c["name"].lower() or query.lower() in c["id"].lower()]
    return custs


def create_customer_draft_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    name = payload.get("customer_name") or payload.get("name")
    email = payload.get("email")
    phone = payload.get("phone")

    doc_id = f"cust-draft-{name.lower().replace(' ', '-')[:15]}" if name else "cust-draft-new"

    if frappe:
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Company",
            "customer_group": "Commercial",
            "territory": "All Territories",
            "cortex_company": company,
            "disabled": 0
        })
        doc.insert(ignore_permissions=True)
        doc_id = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.customer.draft_created",
        entity_type="Customer",
        entity_id=doc_id,
        after_state={"customer_name": name, "email": email, "phone": phone}
    )

    return {
        "id": doc_id,
        "customer_name": name,
        "email": email,
        "phone": phone,
        "status": "draft",
        "company": company
    }


if frappe:
    @frappe.whitelist(methods=["GET", "POST"])
    def search_customers(query: str = ""):
        require_agent_scope("agent:customers:read")
        company = get_company_context()
        data = search_customers_handler(query=query, company=company)
        return {"data": data, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    def create_customer_draft():
        require_agent_scope("agent:customers:draft")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="customers.create_customer_draft",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: create_customer_draft_handler(payload=payload, company=company, actor_id=frappe.session.user),
        )
        return {"data": result, "meta": {"company": company}}
