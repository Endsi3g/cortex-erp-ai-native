import os
import sys
from typing import Any, Dict, List, Optional
import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback/shim for environments where mcp package is in development
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator

from cortex_mcp.config import settings
from cortex_mcp.client import client
from cortex_mcp.schemas import (
    SearchItemsInput,
    SearchCustomersInput,
    CreateCustomerDraftInput,
    CheckAvailabilityInput,
    CreateQuoteDraftInput,
    SubmitApprovalRequestInput,
    PrepareOwnerStatementInput,
    GetTransactionInput
)

# Direct fallback import from cortex_rental services when running in unified environment
try:
    from cortex_rental.services.pricing import PricingService
    from cortex_rental.services.consignment import ConsignmentService
    from cortex_rental.api.v1.quotes import create_draft_handler
    from cortex_rental.api.v1.availability import check_availability_handler
    from cortex_rental.api.v1.approvals import submit_approval_handler
    from cortex_rental.api.v1.customers import search_customers_handler, create_customer_draft_handler
    from cortex_rental.api.v1.items import search_items_handler
    from cortex_rental.api.v1.consignment import prepare_owner_statement_handler
except ImportError:
    PricingService = None
    ConsignmentService = None
    create_draft_handler = None
    check_availability_handler = None
    submit_approval_handler = None
    search_customers_handler = None
    create_customer_draft_handler = None
    search_items_handler = None
    prepare_owner_statement_handler = None

mcp = FastMCP("Cortex Rental ERP Private Facade")


@mcp.tool()
async def search_rental_items(query: str = "", category: Optional[str] = None, company: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search the rental catalog for cameras, lenses, lighting, audio and grip equipment.
    Returns daily rates, categories, and replacement values.
    """
    comp = company or settings.default_company
    if search_items_handler:
        return search_items_handler(query=query, company=comp, category=category)

    res = await client.call_method(
        "cortex_rental.api.v1.items.search_items",
        params={"query": query, "category": category},
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def search_customers(query: str = "", company: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search registered production companies, producers, and client accounts in Cortex ERP.
    """
    comp = company or settings.default_company
    if search_customers_handler:
        return search_customers_handler(query=query, company=comp)

    res = await client.call_method(
        "cortex_rental.api.v1.customers.search_customers",
        params={"query": query},
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def create_customer_draft(name: str, email: Optional[str] = None, phone: Optional[str] = None, notes: Optional[str] = None, company: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new prospective customer draft account. Does not activate credit lines autonomously.
    """
    comp = company or settings.default_company
    payload = {"customer_name": name, "email": email, "phone": phone, "notes": notes}

    if create_customer_draft_handler:
        return create_customer_draft_handler(payload=payload, company=comp, actor_id="agent:mcp-fastmcp")

    res = await client.call_method(
        "cortex_rental.api.v1.customers.create_customer_draft",
        json_data=payload,
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def check_inventory_availability(starts_at: str, ends_at: str, items: List[Dict[str, Any]], company: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check real-time equipment availability for specified dates.
    Calculates safety buffers, active reservations, and maintenance locks.
    """
    comp = company or settings.default_company
    payload = {"starts_at": starts_at, "ends_at": ends_at, "items": items}

    if check_availability_handler:
        return check_availability_handler(payload=payload, company=comp)

    res = await client.call_method(
        "cortex_rental.api.v1.availability.check_availability",
        json_data=payload,
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def create_quote_draft(customer_id: str, starts_at: str, ends_at: str, lines: List[Dict[str, Any]], notes: Optional[str] = None, evidence_ids: Optional[List[str]] = None, company: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an AI-generated quote draft in Cortex Rental.
    Applies canonical 7 days = 3 billable days rule. Does NOT lock physical inventory until approved.
    """
    comp = company or settings.default_company
    payload = {
        "customer_id": customer_id,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "lines": lines,
        "notes": notes,
        "evidence_ids": evidence_ids or []
    }

    if create_draft_handler:
        return create_draft_handler(payload=payload, company=comp, actor_id="agent:mcp-fastmcp")

    res = await client.call_method(
        "cortex_rental.api.v1.quotes.create_quote_draft",
        json_data=payload,
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def submit_approval_request(action: str, entity_type: str, entity_id: str, rationale: str, proposed_payload: Optional[Dict[str, Any]] = None, evidence_ids: Optional[List[str]] = None, company: Optional[str] = None) -> Dict[str, Any]:
    """
    Submit a high-stakes action proposal to the human operator approval queue.
    Strict Gate: Agents cannot auto-approve. Human operator validation is required.
    """
    comp = company or settings.default_company
    payload = {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "proposed_payload": proposed_payload,
        "rationale": rationale,
        "evidence_ids": evidence_ids or []
    }

    if submit_approval_handler:
        return submit_approval_handler(payload=payload, company=comp, actor_id="agent:mcp-fastmcp")

    res = await client.call_method(
        "cortex_rental.api.v1.approvals.submit_approval",
        json_data=payload,
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


@mcp.tool()
async def prepare_owner_statement(owner_id: str, gross_amount: float, consignment_percentage: float, serial_no: str, days: float = 3.0, rate: float = 1500.0, company: Optional[str] = None) -> Dict[str, Any]:
    """
    Prepare a third-party equipment consignment payout statement.
    Strict Invariant: Redacts all customer and renter identities from the owner calculation snapshot.
    """
    comp = company or settings.default_company
    payload = {
        "owner_id": owner_id,
        "gross_amount": gross_amount,
        "consignment_percentage": consignment_percentage,
        "serial_no": serial_no,
        "days": days,
        "rate": rate
    }

    if prepare_owner_statement_handler:
        return prepare_owner_statement_handler(payload=payload, company=comp)

    res = await client.call_method(
        "cortex_rental.api.v1.consignment.prepare_owner_statement",
        json_data=payload,
        company=comp
    )
    return res.get("data") if isinstance(res, dict) and "data" in res else res


if __name__ == "__main__":
    if hasattr(mcp, "run"):
        mcp.run()
    else:
        print("Cortex FastMCP Server initialized with tools:", list(mcp.tools.keys()))
