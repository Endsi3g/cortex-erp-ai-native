from functools import lru_cache
from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services import defense
from cortex_rental.api.v1._shared import envelope, page_args, to_float
from cortex_rental.permissions.agent_scopes import get_company_context, require_agent_scope, require_human_staff_role
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency
from cortex_rental.services.agent_telemetry import log_tool_call


@lru_cache(maxsize=None)
def _customer_fields() -> tuple:
    """
    Return the tuple of Customer DocType fields that exist in the current schema.
    Cached at process level — schema columns do not change at runtime.
    """
    base = ["name", "customer_name"]
    if frappe and hasattr(frappe.db, "has_column"):
        for col in ("customer_group", "territory", "custom_insurance_valid_until", "disabled", "cortex_company"):
            if frappe.db.has_column("Customer", col):
                base.append(col)
    return tuple(base)


def search_customers_handler(query: str, company: str) -> List[Dict[str, Any]]:
    if frappe:
        fields = list(_customer_fields())
        filters: Dict[str, Any] = {}
        if "disabled" in fields:
            filters["disabled"] = 0
        # Scope by tenant — PRD-NFR-6: every query MUST be scoped by company.
        if "cortex_company" in fields:
            filters["cortex_company"] = company

        customers = frappe.get_all("Customer", filters=filters, fields=fields)
        results = []
        for c in customers:
            c_name = c.customer_name or c.name
            if not query or query.lower() in c.name.lower() or query.lower() in c_name.lower():
                results.append(
                    {
                        "id": c.name,
                        "name": c_name,
                        "customer_group": c.get("customer_group") or "Commercial",
                        "territory": c.get("territory") or "All Territories",
                        "insurance_valid": bool(c.get("custom_insurance_valid_until", True)),
                    }
                )
        return results

    # Mock catalog
    custs = [
        {
            "id": "cust-dune3-01",
            "name": "Dune 3 Productions Inc.",
            "customer_group": "Commercial Production",
            "territory": "Canada",
            "insurance_valid": True,
        },
        {
            "id": "cust-netflix-02",
            "name": "Horizon Cinema Services LLC",
            "customer_group": "Feature Film",
            "territory": "United States",
            "insurance_valid": True,
        },
    ]
    if query:
        return [c for c in custs if query.lower() in c["name"].lower() or query.lower() in c["id"].lower()]
    return custs


TRANSACTION = "Cortex Rental Transaction"
OPEN_STATES = ("Reservation", "Contract", "Checked Out", "Partially Returned")


def list_customers_handler(company: str, search: str, page: int, page_size: int) -> Dict[str, Any]:
    """Customers of the tenant with rental activity counted from real transactions.

    Only values ERPNext holds are returned: no risk score, deposit or balance is estimated.
    """
    fields = list(_customer_fields())
    filters: Dict[str, Any] = {}
    if "disabled" in fields:
        filters["disabled"] = 0
    if "cortex_company" in fields:
        filters["cortex_company"] = company
    or_filters = None
    if search and search.strip():
        token = f"%{search.strip()}%"
        or_filters = [["name", "like", token], ["customer_name", "like", token]]

    total = len(frappe.get_all("Customer", filters=filters, or_filters=or_filters, pluck="name"))
    customers = frappe.get_list(
        "Customer",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="customer_name asc",
        start=(page - 1) * page_size,
        page_length=page_size,
    )
    rentals = (
        frappe.get_all(
            TRANSACTION,
            filters={"company": company, "customer": ["in", [c.name for c in customers]]},
            fields=["customer", "rental_state", "starts_at", "grand_total"],
            limit_page_length=0,
        )
        if customers
        else []
    )
    items = []
    for customer in customers:
        mine = [r for r in rentals if r.customer == customer.name]
        starts = [r.starts_at for r in mine if r.starts_at]
        item = {
            "id": customer.name,
            "name": customer.customer_name or customer.name,
            "rentals_count": len(mine),
            "open_rentals_count": sum(1 for r in mine if r.rental_state in OPEN_STATES),
            "billed_total": round(sum(to_float(r.grand_total) for r in mine), 2),
        }
        if customer.get("customer_group"):
            item["customer_group"] = customer.customer_group
        if customer.get("territory"):
            item["territory"] = customer.territory
        if customer.get("custom_insurance_valid_until"):
            item["insurance_valid_until"] = str(customer.custom_insurance_valid_until)
        if starts:
            item["last_rental_start"] = str(max(starts))
        items.append(item)
    return {"items": items, "total_count": total, "page": page, "page_size": page_size}


def create_customer_draft_handler(payload: Dict[str, Any], company: str, actor_id: str) -> Dict[str, Any]:
    name = " ".join(str(payload.get("customer_name") or payload.get("name") or "").split())[:140]
    if not name:
        raise ValueError("Le nom du client est obligatoire.")
    email = payload.get("email")
    phone = payload.get("phone")

    doc_id = f"cust-draft-{name.lower().replace(' ', '-')[:15]}" if name else "cust-draft-new"

    if frappe:
        doc = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": name,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
                "cortex_company": company,
                "disabled": 0,
            }
        )
        doc.insert(ignore_permissions=True)
        doc_id = doc.name

    AuditService.record_mutation(
        company=company,
        action="cortex.customer.draft_created",
        entity_type="Customer",
        entity_id=doc_id,
        after_state={"customer_name": name, "email": email, "phone": phone},
    )

    return {"id": doc_id, "customer_name": name, "email": email, "phone": phone, "status": "draft", "company": company}


if frappe:

    @frappe.whitelist(methods=["GET", "POST"])
    @defense.safe_input
    @log_tool_call("search_customers", scope="agent:customers:read")
    def search_customers(query: str = ""):
        require_agent_scope("agent:customers:read")
        company = get_company_context()
        data = search_customers_handler(query=query, company=company)
        return {"data": data, "meta": {"company": company}}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def list_customers(search: str = None, page: int = 1, page_size: int = 20):
        require_human_staff_role()
        if not frappe.has_permission("Customer", "read"):
            frappe.throw("Accès refusé aux clients.", frappe.PermissionError)
        page, page_size = page_args(page, page_size)
        return envelope(list_customers_handler(get_company_context(), search, page, page_size))

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def summary(customer: str):
        """Vue 360° d'un client : devis ouverts, locations en cours, solde dû, dernière location."""
        require_human_staff_role()
        from cortex_rental.services import customer_360

        return customer_360.summary(customer, get_company_context())

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @log_tool_call("create_customer_draft", scope="agent:customers:draft")
    def create_customer_draft():
        require_agent_scope("agent:customers:draft")
        company = get_company_context()
        payload = frappe.local.form_dict
        result = with_idempotency(
            company=company,
            scope="customers.create_customer_draft",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: create_customer_draft_handler(
                payload=payload, company=company, actor_id=frappe.session.user
            ),
        )
        return {"data": result, "meta": {"company": company}}
