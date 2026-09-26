"""Consignment: owners, statements and payouts (tenant-scoped).

Statements are computed from real returned/closed rentals of consigned
serials (services.consignment); no caller — human or agent — supplies an
amount. Owner-facing output never carries renter identity.
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_agent_scope, require_human_staff_role
from cortex_rental.services import consignment as consignment_service
from cortex_rental.services.agent_telemetry import log_tool_call
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency

CONSIGNMENT_MANAGERS = {"System Manager", "Cortex System Manager", "Cortex Consignment Manager", "Rental Manager"}
FINANCE_APPROVERS = {"System Manager", "Cortex System Manager", "Accounts Manager", "Cortex Finance Manager"}


def _require(roles: set, message: str) -> None:
    if not set(frappe.get_roles(frappe.session.user)) & roles:
        frappe.throw(message, frappe.PermissionError)


def _owner(name: str, company: str):
    doc = frappe.get_doc("Consignment Owner", name)
    if doc.company != company:
        frappe.throw("Propriétaire introuvable pour la société active.", frappe.PermissionError)
    return doc


def _previous_period(period: str) -> str:
    year, month = (int(part) for part in period.split("-")[:2])
    return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"


def _owner_row(company: str, owner, period: str) -> Dict[str, Any]:
    lines = consignment_service.statement_lines(company, owner.name, period)
    return {
        "id": owner.name,
        "owner_code": owner.short_code,
        "display_name": owner.owner_name,
        "owner_type": owner.owner_type,
        "contact_email": owner.email or "",
        "contact_phone": owner.phone or "",
        "default_commission_percentage": float(owner.default_percentage or 0),
        "active_serials_count": len(consignment_service.owner_serials(company, owner.name)),
        "period_revenue": round(sum(line["_net"] for line in lines), 2),
        "period_amount_due": round(sum(line["owner_amount"] for line in lines), 2),
        "statement_status": consignment_service.statement_status(company, owner.name, period),
    }


if frappe:

    @frappe.whitelist(methods=["POST"])
    @log_tool_call("prepare_owner_statement", scope="agent:consignment:read")
    def prepare_owner_statement():
        """Agent tool: returns the computed statement for an owner and period (read-only)."""
        require_agent_scope("agent:consignment:read")
        company = get_company_context()
        payload = frappe.local.form_dict
        owner, period = payload.get("owner_id"), payload.get("period")
        if not owner or not period:
            frappe.throw("owner_id and period (YYYY-MM) are required.", frappe.ValidationError)
        return {"data": consignment_service.owner_statement(company, owner, period), "meta": {"company": company}}

    @frappe.whitelist(methods=["GET"])
    def get_dashboard(period: str = None):
        require_human_staff_role()
        company = get_company_context()
        period = period or frappe.utils.nowdate()[:7]
        owners = [
            frappe.get_doc("Consignment Owner", name)
            for name in frappe.get_list("Consignment Owner", filters={"company": company}, pluck="name")
        ]
        rows = [_owner_row(company, owner, period) for owner in owners]
        previous = _previous_period(period)
        previous_total = sum(
            sum(line["owner_amount"] for line in consignment_service.statement_lines(company, owner.name, previous))
            for owner in owners
        )
        items: Dict[str, Dict[str, Any]] = {}
        for owner in owners:
            for line in consignment_service.statement_lines(company, owner.name, period):
                entry = items.setdefault(
                    line["serial_number"],
                    {
                        "serial_number": line["serial_number"],
                        "item_name": line["equipment_name"],
                        "owner_code": owner.short_code,
                        "revenue_generated": 0.0,
                        "owner_payout": 0.0,
                    },
                )
                entry["revenue_generated"] = round(entry["revenue_generated"] + line["_net"], 2)
                entry["owner_payout"] = round(entry["owner_payout"] + line["owner_amount"], 2)
        return {
            "data": {
                "period": period,
                "currency": frappe.db.get_value("Company", company, "default_currency"),
                "current_month_total_payout": round(sum(row["period_amount_due"] for row in rows), 2),
                "previous_month_total_payout": round(previous_total, 2),
                "active_owners_count": sum(1 for row in rows if row["active_serials_count"]),
                "active_consigned_serials_count": sum(row["active_serials_count"] for row in rows),
                "owners": rows,
                "top_earning_items": sorted(items.values(), key=lambda entry: entry["revenue_generated"], reverse=True)[
                    :10
                ],
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_owner(owner: str, period: str = None):
        require_human_staff_role()
        company = get_company_context()
        doc = _owner(owner, company)
        period = period or frappe.utils.nowdate()[:7]
        serials = frappe.get_all(
            "Serial No",
            filters={"company": company, "cortex_consignment_owner": owner},
            fields=["name", "item_code", "cortex_status"],
            order_by="name asc",
        )
        payouts = frappe.get_all(
            "Consignment Payout",
            filters={"company": company, "consignment_owner": owner},
            fields=["period", "status", "sum(owner_payout_amount) as amount"],
            group_by="period, status",
            order_by="period desc",
            limit_page_length=48,
        )
        row = _owner_row(company, doc, period)
        row.update(
            {
                "billing_address": doc.billing_address or "",
                "serials": [
                    {"serial_no": s.name, "item_code": s.item_code, "status": s.cortex_status or "Active"}
                    for s in serials
                ],
                "statements": [
                    {"period": p.period, "status": p.status, "amount": float(p.amount or 0)} for p in payouts
                ],
                "can_manage": bool(set(frappe.get_roles(frappe.session.user)) & CONSIGNMENT_MANAGERS),
            }
        )
        return {"data": row}

    @frappe.whitelist(methods=["POST"])
    def save_owner(owner: str):
        require_human_staff_role()
        _require(CONSIGNMENT_MANAGERS, "Votre rôle ne permet pas de gérer les propriétaires.")
        company = get_company_context()
        data = frappe.parse_json(owner) if isinstance(owner, str) else owner
        values = {
            "owner_name": (data.get("display_name") or "").strip(),
            "short_code": (data.get("owner_code") or "").strip().upper(),
            "owner_type": data.get("owner_type") or "Third-Party",
            "default_percentage": float(data.get("default_commission_percentage") or 0),
            "email": data.get("contact_email") or "",
            "phone": data.get("contact_phone") or "",
            "billing_address": data.get("billing_address") or "",
        }
        if not values["owner_name"] or not values["short_code"]:
            frappe.throw("Nom et code du propriétaire requis.", frappe.ValidationError)
        if not 0 <= values["default_percentage"] <= 100:
            frappe.throw("Le pourcentage doit être entre 0 et 100.", frappe.ValidationError)
        if data.get("id"):
            doc = _owner(data["id"], company)
            doc.update({k: v for k, v in values.items() if k != "short_code"})
            doc.save()
        else:
            doc = frappe.get_doc({"doctype": "Consignment Owner", "company": company, **values})
            doc.insert()
        AuditService.record_mutation(
            company=company,
            action="cortex.consignment.owner_saved",
            entity_type="Consignment Owner",
            entity_id=doc.name,
            after_state={"owner_name": doc.owner_name, "default_percentage": doc.default_percentage},
        )
        return get_owner(doc.name)

    @frappe.whitelist(methods=["POST"])
    def set_serial_owner(serial_no: str, owner: str = None):
        require_human_staff_role()
        _require(CONSIGNMENT_MANAGERS, "Votre rôle ne permet pas d’affecter une unité à un propriétaire.")
        company = get_company_context()
        current = frappe.db.get_value("Serial No", serial_no, ["company", "cortex_consignment_owner"], as_dict=True)
        if not current or (current.company and current.company != company):
            frappe.throw("Numéro de série introuvable pour la société active.", frappe.DoesNotExistError)
        if owner:
            _owner(owner, company)
        frappe.db.set_value("Serial No", serial_no, "cortex_consignment_owner", owner or None)
        AuditService.record_mutation(
            company=company,
            action="cortex.consignment.serial_owner_set",
            entity_type="Serial No",
            entity_id=serial_no,
            before_state={"owner": current.cortex_consignment_owner},
            after_state={"owner": owner},
        )
        return {"data": {"serial_no": serial_no, "owner": owner}}

    @frappe.whitelist(methods=["GET"])
    def get_owner_statement(owner: str, period: str):
        require_human_staff_role()
        company = get_company_context()
        statement = consignment_service.owner_statement(company, owner, period)
        return {
            "data": {"statement": statement, "status": consignment_service.statement_status(company, owner, period)}
        }

    @frappe.whitelist(methods=["POST"])
    def prepare_statement(owner: str, period: str):
        require_human_staff_role()
        _require(CONSIGNMENT_MANAGERS, "Votre rôle ne permet pas de préparer un relevé.")
        company = get_company_context()
        _owner(owner, company)
        result = with_idempotency(
            company=company,
            scope="consignment.prepare_statement",
            idempotency_key=get_idempotency_key_header(),
            payload={"owner": owner, "period": period},
            handler=lambda: consignment_service.prepare_statement(company, owner, period, frappe.session.user),
        )
        AuditService.record_mutation(
            company=company,
            action="cortex.consignment.statement_prepared",
            entity_type="Consignment Owner",
            entity_id=owner,
            after_state={"period": period, "payouts": len(result["payouts"])},
        )
        return {"data": result}

    @frappe.whitelist(methods=["POST"])
    def approve_statement(owner: str, period: str):
        require_human_staff_role()
        _require(FINANCE_APPROVERS, "L’approbation d’un relevé est réservée à la finance.")
        company = get_company_context()
        _owner(owner, company)
        status = consignment_service.set_statement_status(company, owner, period, "Approved")
        AuditService.record_mutation(
            company=company,
            action="cortex.consignment.statement_approved",
            entity_type="Consignment Owner",
            entity_id=owner,
            after_state={"period": period},
        )
        return {"data": {"status": status}}

    @frappe.whitelist(methods=["POST"])
    def mark_statement_paid(owner: str, period: str, reference: str):
        require_human_staff_role()
        _require(FINANCE_APPROVERS, "Le paiement d’un relevé est réservé à la finance.")
        if not reference or len(reference.strip()) < 3:
            frappe.throw("La référence du paiement ERPNext est obligatoire.", frappe.ValidationError)
        company = get_company_context()
        _owner(owner, company)
        status = consignment_service.set_statement_status(company, owner, period, "Paid", reference.strip())
        AuditService.record_mutation(
            company=company,
            action="cortex.consignment.statement_paid",
            entity_type="Consignment Owner",
            entity_id=owner,
            after_state={"period": period, "reference": reference.strip()[:140]},
        )
        return {"data": {"status": status}}
