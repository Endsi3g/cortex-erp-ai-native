"""Billing endpoints: advance payments, balance invoices and the finance lists.

Human staff only — no agent scope reaches these. Every rental is loaded
through the server-resolved Company, and ERPNext documents are listed only
when they carry the Cortex traceability link for that Company.
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import (
    get_company_context,
    require_finance_role,
    require_human_staff_role,
)
from cortex_rental.services import billing
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency

INVOICE_STATUSES = ("Draft", "Unpaid", "Partly Paid", "Paid", "Overdue", "Return", "Credit Note Issued", "Cancelled")


def _rental(name: str, company: str):
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.company != company:
        frappe.throw("Location introuvable pour la société active.", frappe.PermissionError)
    return doc


def _page(page: Any, page_size: Any):
    page, page_size = max(1, int(page or 1)), min(100, max(1, int(page_size or 20)))
    return page, page_size, (page - 1) * page_size


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_rental_billing(rental_id: str):
        require_human_staff_role()
        return {"data": billing.billing_summary(_rental(rental_id, get_company_context()))}

    @frappe.whitelist(methods=["GET"])
    def get_payment_modes():
        require_human_staff_role()
        company = get_company_context()
        modes = frappe.get_all("Mode of Payment", filters={"enabled": 1}, pluck="name", order_by="name asc")
        configured = set(frappe.get_all("Mode of Payment Account", filters={"company": company}, pluck="parent"))
        return {"data": [{"name": mode, "has_account": mode in configured} for mode in modes]}

    @frappe.whitelist(methods=["POST"])
    def record_advance_payment():
        require_human_staff_role()
        company = get_company_context()
        payload: Dict[str, Any] = frappe.local.form_dict
        doc = _rental(payload.get("rental_id"), company)
        result = with_idempotency(
            company=company,
            scope="billing.record_advance_payment",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: billing.record_advance_payment(
                doc,
                amount=payload.get("amount"),
                mode_of_payment=payload.get("mode_of_payment"),
                reference_no=payload.get("reference_no"),
                reference_date=payload.get("reference_date"),
                user=frappe.session.user,
            ),
        )
        return {"data": result}

    @frappe.whitelist(methods=["POST"])
    def create_final_invoice():
        require_human_staff_role()
        company = get_company_context()
        payload: Dict[str, Any] = frappe.local.form_dict
        doc = _rental(payload.get("rental_id"), company)
        name = with_idempotency(
            company=company,
            scope="billing.create_final_invoice",
            idempotency_key=get_idempotency_key_header(),
            payload=payload,
            handler=lambda: billing.create_final_invoice(doc),
        )
        return {"data": {"sales_invoice": name}}

    @frappe.whitelist(methods=["GET"])
    def list_invoices(
        status: str = None, search: str = None, from_date: str = None, to_date: str = None, page=1, page_size=20
    ):
        require_finance_role()
        company = get_company_context()
        page, page_size, start = _page(page, page_size)
        filters: Dict[str, Any] = {"company": company, "cortex_rental_transaction": ["is", "set"]}
        if status:
            if status not in INVOICE_STATUSES:
                frappe.throw(f"Statut de facture inconnu : {status}", frappe.ValidationError)
            filters["status"] = status
        if from_date or to_date:
            filters["posting_date"] = ["between", [from_date or "1900-01-01", to_date or "2999-12-31"]]
        or_filters = None
        if search:
            token = f"%{search.strip()}%"
            or_filters = [
                ["name", "like", token],
                ["customer_name", "like", token],
                ["cortex_rental_transaction", "like", token],
            ]
        fields = [
            "name",
            "customer",
            "customer_name",
            "posting_date",
            "due_date",
            "status",
            "docstatus",
            "currency",
            "grand_total",
            "total_advance",
            "outstanding_amount",
            "cortex_rental_transaction",
            "is_return",
        ]
        rows = frappe.get_list(
            "Sales Invoice",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by="posting_date desc, name desc",
            start=start,
            page_length=page_size,
        )
        total = len(frappe.get_list("Sales Invoice", filters=filters, or_filters=or_filters, pluck="name"))
        return {"data": {"items": rows, "total_count": total, "page": page, "page_size": page_size}}

    @frappe.whitelist(methods=["GET"])
    def list_payments(search: str = None, from_date: str = None, to_date: str = None, page=1, page_size=20):
        require_finance_role()
        company = get_company_context()
        page, page_size, start = _page(page, page_size)
        filters: Dict[str, Any] = {
            "company": company,
            "cortex_rental_transaction": ["is", "set"],
            "docstatus": ["<", 2],
        }
        if from_date or to_date:
            filters["posting_date"] = ["between", [from_date or "1900-01-01", to_date or "2999-12-31"]]
        or_filters = None
        if search:
            token = f"%{search.strip()}%"
            or_filters = [
                ["name", "like", token],
                ["party_name", "like", token],
                ["cortex_rental_transaction", "like", token],
            ]
        rows = frappe.get_list(
            "Payment Entry",
            filters=filters,
            or_filters=or_filters,
            fields=[
                "name",
                "party",
                "party_name",
                "posting_date",
                "mode_of_payment",
                "reference_no",
                "paid_amount",
                "unallocated_amount",
                "paid_to_account_currency as currency",
                "docstatus",
                "cortex_rental_transaction",
            ],
            order_by="posting_date desc, name desc",
            start=start,
            page_length=page_size,
        )
        total = len(frappe.get_list("Payment Entry", filters=filters, or_filters=or_filters, pluck="name"))
        return {"data": {"items": rows, "total_count": total, "page": page, "page_size": page_size}}
