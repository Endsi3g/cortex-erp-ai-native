"""Customers for staff: list, 360° record, creation, insurance verification.

ERPNext Customer stays the record; Cortex scopes it with `cortex_company`
and reads rentals / invoices / payments tagged with the Cortex rental link.
(`api/v1/customers.py` is the agent tool surface and is unchanged.)
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services.audit import AuditService

VERIFIER_ROLES = {
    "System Manager",
    "Cortex System Manager",
    "Rental Manager",
    "Cortex Operations Manager",
    "Cortex Account Reviewer",
}
ACTIVE_STATES = ("Reservation", "Contract", "Checked Out")
INSURANCE_FIELD = "cortex_insurance_valid_until"


def _customer(name: str, company: str):
    row = frappe.db.get_value("Customer", {"name": name, "cortex_company": company}, "name")
    if not row:
        frappe.throw("Client introuvable pour la société active.", frappe.PermissionError)
    return frappe.get_doc("Customer", name)


def _insurance(doc) -> Dict[str, Any]:
    value = doc.get(INSURANCE_FIELD) if frappe.db.has_column("Customer", INSURANCE_FIELD) else None
    if not value:
        return {"valid_until": None, "status": "unknown"}
    valid = frappe.utils.getdate(value) >= frappe.utils.getdate()
    return {"valid_until": str(value), "status": "valid" if valid else "expired"}


def _outstanding(company: str, customers: list) -> Dict[str, float]:
    if not customers:
        return {}
    rows = frappe.get_all(
        "Sales Invoice",
        filters={"company": company, "customer": ["in", customers], "docstatus": 1, "outstanding_amount": [">", 0]},
        fields=["customer", "sum(outstanding_amount) as due"],
        group_by="customer",
    )
    return {row.customer: float(row.due or 0) for row in rows}


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_customers(search: str = None, page=1, page_size=50):
        require_human_staff_role()
        company = get_company_context()
        page, page_size = max(1, int(page)), min(500, max(1, int(page_size)))
        filters: Dict[str, Any] = {"cortex_company": company, "disabled": 0}
        or_filters = None
        if search:
            token = f"%{search.strip()}%"
            or_filters = [["name", "like", token], ["customer_name", "like", token], ["email_id", "like", token]]
        fields = ["name", "customer_name", "customer_group", "email_id", "mobile_no"]
        if frappe.db.has_column("Customer", INSURANCE_FIELD):
            fields.append(INSURANCE_FIELD)
        rows = frappe.get_list(
            "Customer",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by="customer_name asc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )
        total = len(frappe.get_list("Customer", filters=filters, or_filters=or_filters, pluck="name"))
        names = [row.name for row in rows]
        counts = {}
        if names:
            for row in frappe.get_all(
                "Cortex Rental Transaction",
                filters={"company": company, "customer": ["in", names]},
                fields=["customer", "rental_state", "count(name) as n"],
                group_by="customer, rental_state",
            ):
                entry = counts.setdefault(row.customer, {"total": 0, "active": 0})
                entry["total"] += int(row.n)
                if row.rental_state in ACTIVE_STATES:
                    entry["active"] += int(row.n)
        due = _outstanding(company, names)
        today = frappe.utils.getdate()
        items = []
        for row in rows:
            insurance = row.get(INSURANCE_FIELD)
            items.append(
                {
                    "name": row.name,
                    "customer_name": row.customer_name or row.name,
                    "customer_group": row.customer_group or "",
                    "email": row.email_id or "",
                    "phone": row.mobile_no or "",
                    "rentals": counts.get(row.name, {}).get("total", 0),
                    "active_rentals": counts.get(row.name, {}).get("active", 0),
                    "outstanding": due.get(row.name, 0.0),
                    "insurance_status": "unknown"
                    if not insurance
                    else ("valid" if frappe.utils.getdate(insurance) >= today else "expired"),
                    "insurance_valid_until": str(insurance) if insurance else None,
                }
            )
        return {
            "data": {
                "items": items,
                "total_count": total,
                "page": page,
                "page_size": page_size,
                "currency": frappe.db.get_value("Company", company, "default_currency"),
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_customer(customer: str):
        require_human_staff_role()
        company = get_company_context()
        doc = _customer(customer, company)
        rentals = frappe.get_all(
            "Cortex Rental Transaction",
            filters={"company": company, "customer": customer},
            fields=["name", "project_name", "rental_state", "starts_at", "ends_at", "grand_total"],
            order_by="starts_at desc",
            limit_page_length=100,
        )
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={"company": company, "customer": customer, "docstatus": ["<", 2]},
            fields=[
                "name",
                "posting_date",
                "status",
                "docstatus",
                "grand_total",
                "outstanding_amount",
                "cortex_rental_transaction",
            ],
            order_by="posting_date desc",
            limit_page_length=50,
        )
        payments = frappe.get_all(
            "Payment Entry",
            filters={"company": company, "party_type": "Customer", "party": customer, "docstatus": ["<", 2]},
            fields=["name", "posting_date", "docstatus", "paid_amount", "mode_of_payment", "cortex_rental_transaction"],
            order_by="posting_date desc",
            limit_page_length=50,
        )
        finished = [r for r in rentals if r.rental_state in ("Returned", "Closed")]
        return {
            "data": {
                "name": doc.name,
                "customer_name": doc.customer_name,
                "customer_type": doc.customer_type,
                "customer_group": doc.customer_group,
                "email": doc.get("email_id") or "",
                "phone": doc.get("mobile_no") or "",
                "insurance": _insurance(doc),
                "currency": frappe.db.get_value("Company", company, "default_currency"),
                "stats": {
                    "rentals": len(rentals),
                    "active_rentals": sum(1 for r in rentals if r.rental_state in ACTIVE_STATES),
                    "lifetime_value": round(sum(float(r.grand_total or 0) for r in finished), 2),
                    "outstanding": round(
                        sum(float(i.outstanding_amount or 0) for i in invoices if i.docstatus == 1), 2
                    ),
                    "disputes": sum(1 for r in rentals if r.rental_state == "Disputed"),
                },
                "rentals": [
                    {
                        "name": r.name,
                        "project_name": r.project_name or "",
                        "rental_state": r.rental_state,
                        "starts_at": str(r.starts_at),
                        "ends_at": str(r.ends_at),
                        "grand_total": float(r.grand_total or 0),
                    }
                    for r in rentals
                ],
                "invoices": [
                    {
                        "name": i.name,
                        "posting_date": str(i.posting_date),
                        "status": i.status,
                        "docstatus": i.docstatus,
                        "grand_total": float(i.grand_total or 0),
                        "outstanding_amount": float(i.outstanding_amount or 0),
                        "rental": i.cortex_rental_transaction,
                    }
                    for i in invoices
                ],
                "payments": [
                    {
                        "name": p.name,
                        "posting_date": str(p.posting_date),
                        "docstatus": p.docstatus,
                        "paid_amount": float(p.paid_amount or 0),
                        "mode_of_payment": p.mode_of_payment,
                        "rental": p.cortex_rental_transaction,
                    }
                    for p in payments
                ],
                "can_verify": bool(set(frappe.get_roles(frappe.session.user)) & VERIFIER_ROLES),
            }
        }

    @frappe.whitelist(methods=["POST"])
    def create_customer(customer_name: str, customer_type: str = "Company", email: str = None, phone: str = None):
        require_human_staff_role()
        company = get_company_context()
        customer_name = (customer_name or "").strip()
        if len(customer_name) < 2:
            frappe.throw("Le nom du client est requis.", frappe.ValidationError)
        if customer_type not in ("Company", "Individual"):
            frappe.throw("Type de client invalide.", frappe.ValidationError)
        if frappe.db.exists("Customer", {"customer_name": customer_name, "cortex_company": company}):
            frappe.throw("Un client porte déjà ce nom dans cette société.", frappe.ValidationError)
        values = {
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": customer_type,
            "cortex_company": company,
            "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups",
            "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
        }
        doc = frappe.get_doc(values)
        if email:
            doc.email_id = email.strip()
        if phone:
            doc.mobile_no = phone.strip()
        doc.insert()
        AuditService.record_mutation(
            company=company,
            action="cortex.customer.created",
            entity_type="Customer",
            entity_id=doc.name,
            after_state={"customer_name": customer_name, "customer_type": customer_type},
        )
        return get_customer(doc.name)

    @frappe.whitelist(methods=["POST"])
    def set_insurance(customer: str, valid_until: str = None, note: str = None):
        require_human_staff_role()
        if not set(frappe.get_roles(frappe.session.user)) & VERIFIER_ROLES:
            frappe.throw("Votre rôle ne permet pas de vérifier une assurance.", frappe.PermissionError)
        company = get_company_context()
        doc = _customer(customer, company)
        before = doc.get(INSURANCE_FIELD)
        frappe.db.set_value("Customer", doc.name, INSURANCE_FIELD, valid_until or None)
        AuditService.record_mutation(
            company=company,
            action="cortex.customer.insurance_verified",
            entity_type="Customer",
            entity_id=doc.name,
            before_state={"valid_until": str(before) if before else None},
            after_state={"valid_until": valid_until, "note": (note or "")[:500]},
        )
        return get_customer(doc.name)
