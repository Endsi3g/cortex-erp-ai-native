"""Human-facing, tenant-scoped APIs for the rental composer and lifecycle."""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services.audit import AuditService
from cortex_rental.services.idempotency import get_idempotency_key_header, with_idempotency
from cortex_rental.services.pricing import PricingService


def _profile(item_code: str, company: str):
    profile = frappe.db.get_value(
        "Cortex Rental Item Profile",
        {"item_code": item_code, "company": company},
        ["item_code", "item_name", "category", "daily_rate", "is_serialized"],
        as_dict=True,
    )
    if not profile:
        frappe.throw(f"{item_code} is not in the rental catalog for this company.", frappe.ValidationError)
    return profile


def _pricing(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    starts_at, ends_at = payload.get("starts_at"), payload.get("ends_at")
    if not starts_at or not ends_at:
        frappe.throw("Rental start and end dates are required.", frappe.ValidationError)
    calendar_days, billable_days = PricingService.compute_billable_days(starts_at, ends_at, company)
    requests = payload.get("items") or []
    if not requests:
        frappe.throw("Add at least one rental item before requesting a price.", frappe.ValidationError)
    lines, subtotal, discount_amount = [], 0.0, 0.0
    roles = set(frappe.get_roles(frappe.session.user))
    for requested in requests:
        code = requested.get("item_code")
        quantity = float(requested.get("quantity") or 0)
        discount = float(requested.get("discount_percentage") or 0)
        if quantity <= 0:
            frappe.throw(f"Quantity must be greater than zero for {code}.", frappe.ValidationError)
        if discount < 0 or discount > 100:
            frappe.throw(f"Discount must be between 0 and 100 for {code}.", frappe.ValidationError)
        if discount and not roles.intersection({"System Manager", "Administrator", "Rental Manager"}):
            frappe.throw("Only a Rental Manager can apply a discount.", frappe.PermissionError)
        profile = _profile(code, company)
        # The browser's daily_rate is deliberately ignored. The company-scoped
        # Rental Item Profile is the sole price authority.
        daily_rate = float(profile.daily_rate or 0)
        line_total = PricingService.calculate_line_total(daily_rate, quantity, billable_days, discount)
        undiscounted = PricingService.calculate_line_total(daily_rate, quantity, billable_days)
        discount_amount += undiscounted - line_total
        subtotal += line_total
        lines.append({
            "item_code": code,
            "item_name": profile.item_name or code,
            "category": profile.category or "Uncategorized",
            "quantity": quantity,
            "daily_rate": daily_rate,
            "discount_percentage": discount,
            "billable_days": billable_days,
            "line_subtotal": line_total,
            "is_serialized": bool(profile.is_serialized),
        })
    # Tax is supplied only by an ERPNext tax template configured for the
    # company. No client-side Quebec tax constant is treated as canonical.
    return {
        "calendar_days": calendar_days,
        "billable_days": billable_days,
        "subtotal": round(subtotal, 2),
        "discount_amount": round(discount_amount, 2),
        "tax_amount": 0.0,
        "grand_total": round(subtotal, 2),
        "pricing_rule_applied": "Rental Pricing Rule / Cortex Rental Item Profile",
        "lines": lines,
    }


def _customer_in_company(customer: str, company: str) -> None:
    if not frappe.db.exists("Customer", {"name": customer, "cortex_company": company}):
        frappe.throw("Customer is unavailable for the active company.", frappe.PermissionError)


def _serialize(doc) -> Dict[str, Any]:
    customer = frappe.db.get_value("Customer", doc.customer, ["customer_name", "email_id"], as_dict=True) or {}
    items = []
    for row in doc.items or []:
        profile = frappe.db.get_value(
            "Cortex Rental Item Profile",
            {"company": doc.company, "item_code": row.item_code},
            ["category"],
            as_dict=True,
        ) or {}
        try:
            serials = frappe.parse_json(row.assigned_serials or "[]")
        except Exception:
            serials = [row.serial_no] if row.serial_no else []
        if row.serial_no and row.serial_no not in serials:
            serials.append(row.serial_no)
        try:
            scanned_checkout = frappe.parse_json(row.scanned_checkout_serials or "[]")
        except Exception:
            scanned_checkout = []
        checkin_rows = frappe.get_all("Cortex Check-In Item",
            filters={"transaction_item": row.name}, fields=["serial_no", "parent"])
        scanned_checkin = [entry.serial_no for entry in checkin_rows if entry.serial_no and
            frappe.db.get_value("Cortex Check-In", entry.parent, "status") == "Completed"]
        items.append({
            "id": row.name,
            "item_code": row.item_code,
            "item_name": row.item_name or row.item_code,
            "category": profile.get("category") or "Uncategorized",
            "quantity": float(row.qty or 0),
            "daily_rate": float(row.rate or 0),
            "discount_percentage": float(row.discount_percentage or 0),
            "billable_days": float(row.billable_days or doc.billable_days or 0),
            "subtotal": float(row.amount or 0),
            "assigned_serials": serials,
            # No separate durable scan rows exist for checkout; do not imply
            # scan history that the DocType does not store.
            "scanned_checkout_serials": scanned_checkout,
            "scanned_checkin_serials": scanned_checkin,
            "is_consigned": False,
        })
    return {
        "provenance": "api",
        "last_synced_at": frappe.utils.now_datetime().isoformat(),
        "id": doc.name,
        "name": doc.name,
        "company": doc.company,
        "customer_id": doc.customer,
        "customer_name": customer.get("customer_name") or doc.customer,
        "customer_contact_email": customer.get("email_id") or None,
        "project_name": doc.project_name or None,
        "rental_state": doc.rental_state,
        "starts_at": str(doc.starts_at),
        "ends_at": str(doc.ends_at),
        "calendar_days": int(doc.calendar_days or 0),
        "billable_days": float(doc.billable_days or 0),
        "subtotal": float(doc.subtotal or 0),
        "discount_total": sum(
            PricingService.calculate_line_total(float(row.rate or 0), float(row.qty or 0), float(row.billable_days or 0))
            - float(row.amount or 0) for row in doc.items or []
        ),
        "tax_rate": float(doc.tax_rate or 0),
        "tax_amount": float(doc.tax_amount or 0),
        "grand_total": float(doc.grand_total or 0),
        "currency": frappe.db.get_value("Company", doc.company, "default_currency") or "CAD",
        "readiness": {
            "customer_account_ready": bool(doc.customer_account_ready),
            "insurance_ready": bool(doc.insurance_ready),
            "payment_ready": bool(doc.payment_ready),
            "overall_ready": bool(doc.customer_account_ready and doc.insurance_ready and doc.payment_ready),
            "missing_requirements": [label for field, label in (
                ("customer_account_ready", "Vérification du compte client"),
                ("insurance_ready", "Certificat d’assurance valide"),
                ("payment_ready", "Caution ou modalités de paiement"),
            ) if not bool(getattr(doc, field, 0))],
        },
        "items": items,
        "notes": doc.notes or "",
        "created_at": str(doc.creation),
        "updated_at": str(doc.modified),
        "version": int(doc.version or 1),
    }


def _owned_transaction(name: str, company: str):
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.company != company:
        frappe.throw("Rental transaction is unavailable for the active company.", frappe.PermissionError)
    return doc


if frappe:

    @frappe.whitelist(methods=["GET"])
    def search_rental_customers(query: str = ""):
        require_human_staff_role()
        company = get_company_context()
        rows = frappe.get_all("Customer", filters={"cortex_company": company, "disabled": 0},
            fields=["name", "customer_name", "custom_insurance_valid_until"],
            order_by="customer_name asc", limit_page_length=100)
        needle = (query or "").strip().casefold()
        today = frappe.utils.getdate()
        items = []
        for row in rows:
            display_name = row.customer_name or row.name
            if needle and needle not in display_name.casefold() and needle not in row.name.casefold():
                continue
            expires = row.custom_insurance_valid_until
            items.append({"id": row.name, "name": display_name,
                "insurance_valid": (frappe.utils.getdate(expires) >= today) if expires else None})
        return {"items": items}

    @frappe.whitelist(methods=["GET"])
    def search_rental_catalog(query: str = ""):
        require_human_staff_role()
        company = get_company_context()
        rows = frappe.get_all("Cortex Rental Item Profile", filters={"company": company},
            fields=["item_code", "item_name", "category", "daily_rate", "is_serialized", "required_accessories"],
            order_by="item_name asc", limit_page_length=200)
        needle = (query or "").strip().casefold()
        items = []
        for row in rows:
            display_name = row.item_name or row.item_code
            if needle and needle not in display_name.casefold() and needle not in row.item_code.casefold():
                continue
            raw = row.required_accessories or ""
            try:
                accessories = (frappe.parse_json(raw) if raw.lstrip().startswith("[")
                    else [part.strip() for part in raw.split(",") if part.strip()])
            except Exception:
                accessories = [part.strip() for part in raw.split(",") if part.strip()]
            items.append({"item_code": row.item_code, "item_name": display_name,
                "category": row.category or "Uncategorized", "daily_rate": float(row.daily_rate or 0),
                "is_serialized": bool(row.is_serialized), "required_accessories": accessories})
        return {"items": items}

    @frappe.whitelist(methods=["GET"])
    def list_rentals(page: int = 1, page_size: int = 20, state: str = None,
                     customer_id: str = None, search: str = None,
                     starts_after: str = None, ends_before: str = None):
        require_human_staff_role()
        company = get_company_context()
        page, page_size = max(1, int(page)), min(100, max(1, int(page_size)))
        filters: Dict[str, Any] = {"company": company}
        if state:
            filters["rental_state"] = state
        if customer_id:
            _customer_in_company(customer_id, company)
            filters["customer"] = customer_id
        if starts_after:
            filters["starts_at"] = (">=", starts_after)
        if ends_before:
            filters["ends_at"] = ("<=", ends_before)
        or_filters = None
        if search:
            token = f"%{search.strip()}%"
            or_filters = [["name", "like", token], ["customer", "like", token]]
        total = frappe.db.count("Cortex Rental Transaction", filters=filters)
        names = frappe.get_all(
            "Cortex Rental Transaction", filters=filters, or_filters=or_filters,
            fields=["name"], order_by="modified desc", start=(page - 1) * page_size,
            page_length=page_size,
        )
        return {"data": {
            "provenance": "api", "last_synced_at": frappe.utils.now_datetime().isoformat(),
            "items": [_serialize(frappe.get_doc("Cortex Rental Transaction", row.name)) for row in names],
            "total_count": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }}

    @frappe.whitelist(methods=["GET"])
    def get_rental(name: str):
        require_human_staff_role()
        return {"data": _serialize(_owned_transaction(name, get_company_context()))}

    @frappe.whitelist(methods=["POST"])
    def preview_pricing():
        require_human_staff_role()
        result = _pricing(frappe.local.form_dict, get_company_context())
        return {"data": {
            "provenance": "api", "last_synced_at": frappe.utils.now_datetime().isoformat(), **result
        }}

    @frappe.whitelist(methods=["POST"])
    def create_quote_draft():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        if isinstance(payload.get("items"), str):
            payload["items"] = frappe.parse_json(payload["items"])
        _customer_in_company(payload.get("customer_id"), company)
        priced = _pricing(payload, company)

        def create():
            doc = frappe.get_doc({
                "doctype": "Cortex Rental Transaction", "company": company,
                "customer": payload["customer_id"], "rental_state": "Quote",
                "starts_at": payload["starts_at"], "ends_at": payload["ends_at"],
                "project_name": payload.get("project_name") or "",
                "tax_rate": 0, "notes": payload.get("notes") or "",
                "items": [{
                    "item_code": line["item_code"], "item_name": line["item_name"],
                    "qty": line["quantity"], "rate": line["daily_rate"],
                    "discount_percentage": line["discount_percentage"],
                } for line in priced["lines"]],
            })
            doc.insert()
            AuditService.record_mutation(
                company=company, action="cortex.rental_transaction.draft_created",
                entity_type="Cortex Rental Transaction", entity_id=doc.name,
                evidence=payload.get("evidence_ids"), after_state={"state": "Quote", "total": doc.grand_total},
            )
            return doc.name

        name = with_idempotency(
            company=company, scope="rentals.create_quote_draft",
            idempotency_key=get_idempotency_key_header(), payload=payload, handler=create,
        )
        return {
            "request_id": frappe.generate_hash(length=16), "entity_id": name,
            "status": "completed", "approval_required": False,
            "mutation_performed": True,
        }

    @frappe.whitelist(methods=["POST"])
    def request_reservation(name: str, version: int = None):
        require_human_staff_role()
        company = get_company_context()
        doc = _owned_transaction(name, company)
        if version is not None and int(version) != int(doc.version or 1):
            return {"request_id": frappe.generate_hash(length=16), "entity_id": name,
                "status": "stale", "approval_required": False, "mutation_performed": False,
                "errors": [{"code": "stale_version", "message": "La location a changé. Recharge-la avant de confirmer."}]}
        doc.transition_to("Reservation", reason="Confirmed by authorized staff")
        return {"request_id": frappe.generate_hash(length=16), "entity_id": name,
            "status": "completed", "approval_required": False, "mutation_performed": True}

    @frappe.whitelist(methods=["POST"])
    def request_contract(name: str, version: int = None, override_reason: str = None):
        require_human_staff_role()
        company = get_company_context()
        doc = _owned_transaction(name, company)
        if version is not None and int(version) != int(doc.version or 1):
            return {"request_id": frappe.generate_hash(length=16), "entity_id": doc.name,
                "status": "stale", "approval_required": False, "mutation_performed": False,
                "stale_context": True,
                "errors": [{"code": "stale_version", "message": "La location a changé. Recharge-la avant de demander le contrat."}]}
        if doc.rental_state != "Reservation":
            frappe.throw("Seule une réservation peut être soumise à l’approbation du contrat.", frappe.ValidationError)
        pending = frappe.db.get_value("Approval Request", {
            "company": company, "entity_type": "Cortex Rental Transaction", "entity_id": doc.name,
            "action": "rental.transaction.transition_to_contract", "status": "Pending",
        }, "name")
        if pending:
            return {"request_id": pending, "entity_id": doc.name,
                "status": "approval_required", "approval_required": True,
                "approval_request_id": pending, "mutation_performed": False}
        request = frappe.get_doc({
            "doctype": "Approval Request", "company": company,
            "action": "rental.transaction.transition_to_contract",
            "entity_type": "Cortex Rental Transaction", "entity_id": doc.name,
            "status": "Pending", "requested_by_type": "Human",
            "requested_by_id": frappe.session.user,
            "proposed_payload": frappe.as_json({"rental_state": "Contract", "version": version}),
            "decision_reason": override_reason or "Contrat soumis à l’approbation humaine",
        })
        request.insert()
        return {"request_id": request.name, "entity_id": request.name,
            "status": "approval_required", "approval_required": True,
            "approval_request_id": request.name, "mutation_performed": False}

    @frappe.whitelist(methods=["POST"])
    def update_quote_draft():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        if isinstance(payload.get("items"), str):
            payload["items"] = frappe.parse_json(payload["items"])
        doc = _owned_transaction(payload.get("rental_id"), company)
        if doc.rental_state != "Quote":
            frappe.throw("Seuls les brouillons de devis peuvent être modifiés.", frappe.ValidationError)
        if int(payload.get("version") or 0) != int(doc.version or 1):
            return {"request_id": frappe.generate_hash(length=16), "entity_id": doc.name,
                "status": "stale", "approval_required": False, "mutation_performed": False,
                "stale_context": True,
                "errors": [{"code": "stale_version", "message": "Le devis a changé. Recharge-le avant de continuer."}]}
        merged = {
            "starts_at": payload.get("starts_at") or doc.starts_at,
            "ends_at": payload.get("ends_at") or doc.ends_at,
            "items": payload.get("items") if payload.get("items") is not None else [
                {"item_code": row.item_code, "quantity": row.qty,
                 "discount_percentage": row.discount_percentage} for row in doc.items
            ],
        }
        priced = _pricing(merged, company)
        before = {"version": int(doc.version or 1), "subtotal": float(doc.subtotal or 0)}
        doc.starts_at, doc.ends_at = merged["starts_at"], merged["ends_at"]
        doc.project_name = payload.get("project_name", doc.project_name)
        doc.notes = payload.get("notes", doc.notes)
        doc.set("items", [])
        for line in priced["lines"]:
            doc.append("items", {
                "item_code": line["item_code"], "item_name": line["item_name"],
                "qty": line["quantity"], "rate": line["daily_rate"],
                "discount_percentage": line["discount_percentage"],
            })
        doc.save()
        AuditService.record_mutation(
            company=company, action="cortex.rental_transaction.quote_updated",
            entity_type="Cortex Rental Transaction", entity_id=doc.name,
            before_state=before, after_state={"version": int(doc.version or 1), "subtotal": float(doc.subtotal or 0)},
        )
        return {"request_id": frappe.generate_hash(length=16), "entity_id": doc.name,
            "status": "completed", "approval_required": False, "mutation_performed": True}

    @frappe.whitelist(methods=["GET"])
    def get_rental_audit(rental_id: str):
        require_human_staff_role()
        company = get_company_context()
        _owned_transaction(rental_id, company)
        rows = frappe.get_all("Audit Event", filters={
            "company": company, "entity_type": "Cortex Rental Transaction", "entity_id": rental_id,
        }, fields=["name", "creation", "actor_type", "actor_id", "action", "before_state", "after_state"],
           order_by="creation desc", limit_page_length=200)
        return {"provenance": "api", "last_synced_at": frappe.utils.now_datetime().isoformat(),
            "rental_id": rental_id, "events": [{
                "id": row.name, "timestamp": str(row.creation),
                "actor": {"actor_type": row.actor_type or "System", "actor_id": row.actor_id or ""},
                "action": row.action,
                "diff_summary": f"{row.before_state or ''} → {row.after_state or ''}".strip(),
            } for row in rows]}
