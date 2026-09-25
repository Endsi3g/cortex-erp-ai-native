"""
Rental billing on ERPNext's own documents (advance + balance model).

1. Reservation  -> a submitted Sales Order carrying the server-priced lines
   (billable days, discounts) and the company's sales tax template. The
   requested advance is computed here: a share of the order's grand total
   (Cortex Company Settings, 30% by default) plus, when enabled, the
   equipment guarantee (profile `deposit_required` x quantity).
2. Advance      -> a native ERPNext Payment Entry against the Sales Order
   (ERPNext records it as an advance). Submitted when the person recording
   it holds an accounting role; otherwise left as a draft for accounting.
3. Return       -> a DRAFT balance Sales Invoice mapped from the Sales
   Order, advances allocated automatically, plus damage / loss lines from
   the completed check-ins. A person submits it in ERPNext.

ERPNext calls used (v15): erpnext.controllers.accounts_controller
.get_taxes_and_charges, erpnext.accounts.doctype.payment_entry
.payment_entry.get_payment_entry, erpnext.selling.doctype.sales_order
.sales_order.make_sales_invoice, erpnext.accounts.doctype.sales_invoice
.sales_invoice.get_bank_cash_account. Not exercised against a live bench
in this repository's CI.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.audit import AuditService

DEFAULT_ADVANCE_PERCENTAGE = 30.0
ACCOUNTING_ROLES = {"Accounts User", "Accounts Manager", "System Manager", "Cortex Finance Manager"}


def get_settings(company: str) -> Dict[str, Any]:
    row = None
    if frappe.db.exists("Cortex Company Settings", company):
        row = frappe.db.get_value(
            "Cortex Company Settings",
            company,
            ["advance_percentage", "include_equipment_guarantee", "taxes_and_charges", "damage_item", "loss_item"],
            as_dict=True,
        )
    row = row or {}
    return {
        "advance_percentage": float(
            row.get("advance_percentage") if row.get("advance_percentage") is not None else DEFAULT_ADVANCE_PERCENTAGE
        ),
        "include_equipment_guarantee": bool(
            row.get("include_equipment_guarantee") if row.get("include_equipment_guarantee") is not None else 1
        ),
        "taxes_and_charges": row.get("taxes_and_charges")
        or frappe.db.get_value("Sales Taxes and Charges Template", {"company": company, "is_default": 1}, "name"),
        "damage_item": row.get("damage_item"),
        "loss_item": row.get("loss_item"),
        "configured": bool(row),
    }


def compute_guarantee(doc) -> float:
    total = 0.0
    for row in doc.items or []:
        deposit = frappe.db.get_value(
            "Cortex Rental Item Profile", {"company": doc.company, "item_code": row.item_code}, "deposit_required"
        )
        total += float(deposit or 0) * float(row.qty or 0)
    return round(total, 2)


def compute_advance(grand_total: float, guarantee: float, settings: Dict[str, Any]) -> Dict[str, float]:
    share = round(float(grand_total or 0) * settings["advance_percentage"] / 100.0, 2)
    guarantee = round(guarantee if settings["include_equipment_guarantee"] else 0.0, 2)
    return {"percentage_amount": share, "guarantee_amount": guarantee, "total": round(share + guarantee, 2)}


def _line_description(doc, row) -> str:
    return (
        f"{row.item_name or row.item_code} — location du {frappe.utils.formatdate(doc.starts_at)} "
        f"au {frappe.utils.formatdate(doc.ends_at)} ({int(doc.calendar_days or 0)} j calendaires = "
        f"{float(doc.billable_days or 0):g} j facturables)"
    )


def create_sales_order(doc) -> str:
    """Create and submit the ERPNext Sales Order for a rental that became a Reservation."""
    if doc.erpnext_sales_order:
        return doc.erpnext_sales_order

    from erpnext.controllers.accounts_controller import get_taxes_and_charges

    settings = get_settings(doc.company)
    so = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "customer": doc.customer,
            "company": doc.company,
            "transaction_date": frappe.utils.today(),
            "delivery_date": frappe.utils.getdate(doc.starts_at),
            "cortex_rental_transaction": doc.name,
            "items": [
                {
                    "item_code": row.item_code,
                    "qty": float(row.qty or 0),
                    # Rental price for the whole period, already including the
                    # billable-days rule and the line discount (PricingService).
                    "rate": round(float(row.amount or 0) / float(row.qty or 1), 2),
                    "delivery_date": frappe.utils.getdate(doc.starts_at),
                    "description": _line_description(doc, row),
                }
                for row in doc.items or []
            ],
        }
    )
    if settings["taxes_and_charges"]:
        so.taxes_and_charges = settings["taxes_and_charges"]
        so.set("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", settings["taxes_and_charges"]))
    so.flags.ignore_permissions = True
    so.insert()
    so.submit()

    advance = compute_advance(so.grand_total, compute_guarantee(doc), settings)
    doc.db_set(
        {
            "erpnext_sales_order": so.name,
            "tax_amount": float(so.total_taxes_and_charges or 0),
            "grand_total": float(so.grand_total or 0),
            "advance_percentage_amount": advance["percentage_amount"],
            "guarantee_amount": advance["guarantee_amount"],
            "advance_amount": advance["total"],
        }
    )
    AuditService.record_mutation(
        company=doc.company,
        action="cortex.billing.sales_order_created",
        entity_type="Cortex Rental Transaction",
        entity_id=doc.name,
        after_state={"sales_order": so.name, "grand_total": float(so.grand_total or 0), "advance": advance},
    )
    return so.name


def _refresh_payment_readiness(doc) -> None:
    """payment_ready follows ERPNext: the order's advance_paid covers the requested advance."""
    if not doc.erpnext_sales_order:
        return
    advance_paid = float(frappe.db.get_value("Sales Order", doc.erpnext_sales_order, "advance_paid") or 0)
    ready = 1 if float(doc.advance_amount or 0) > 0 and advance_paid + 0.005 >= float(doc.advance_amount or 0) else 0
    if int(doc.payment_ready or 0) != ready:
        doc.db_set("payment_ready", ready)


def record_advance_payment(
    doc,
    amount: float,
    mode_of_payment: Optional[str],
    reference_no: Optional[str],
    reference_date: Optional[str],
    user: str,
) -> Dict[str, Any]:
    if doc.rental_state not in ("Reservation", "Contract", "Checked Out"):
        frappe.throw(
            "Un acompte ne peut être enregistré que sur une location réservée ou en cours.", frappe.ValidationError
        )
    if not doc.erpnext_sales_order:
        frappe.throw("Cette location n’a pas encore de commande ERPNext.", frappe.ValidationError)
    amount = round(float(amount or 0), 2)
    if amount <= 0:
        frappe.throw("Le montant de l’acompte doit être positif.", frappe.ValidationError)

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

    pe = get_payment_entry("Sales Order", doc.erpnext_sales_order, party_amount=amount, ignore_permissions=True)
    if mode_of_payment:
        pe.mode_of_payment = mode_of_payment
        account = (get_bank_cash_account(mode_of_payment, doc.company) or {}).get("account")
        if account:
            pe.paid_to = account
    pe.reference_no = reference_no or doc.name
    pe.reference_date = reference_date or frappe.utils.today()
    pe.cortex_rental_transaction = doc.name
    pe.flags.ignore_permissions = True
    pe.insert()

    submitted = bool(set(frappe.get_roles(user)) & ACCOUNTING_ROLES)
    if submitted:
        pe.submit()
        _refresh_payment_readiness(doc)

    AuditService.record_mutation(
        company=doc.company,
        action="cortex.billing.advance_recorded",
        entity_type="Cortex Rental Transaction",
        entity_id=doc.name,
        after_state={"payment_entry": pe.name, "amount": amount, "submitted": submitted},
    )
    return {"payment_entry": pe.name, "amount": amount, "submitted": submitted}


def _checkin_charges(doc, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Damage and loss lines from completed check-ins, priced from recorded costs / replacement value."""
    charges: List[Dict[str, Any]] = []
    checkins = frappe.get_all("Cortex Check-In", filters={"transaction": doc.name, "status": "Completed"}, pluck="name")
    if not checkins:
        return charges
    rows = frappe.get_all(
        "Cortex Check-In Item",
        filters={"parent": ["in", checkins]},
        fields=[
            "item_code",
            "serial_no",
            "condition",
            "disposition",
            "expected_qty",
            "returned_qty",
            "estimated_repair_cost",
        ],
    )
    for row in rows:
        label = f"{row.item_code}{f' ({row.serial_no})' if row.serial_no else ''}"
        if row.condition == "Damaged" and float(row.estimated_repair_cost or 0) > 0:
            if not settings["damage_item"]:
                frappe.throw(
                    "Des frais de dommages sont à facturer, mais aucun article « Frais de dommages » n’est configuré "
                    "dans Cortex Company Settings.",
                    frappe.ValidationError,
                )
            charges.append(
                {
                    "item_code": settings["damage_item"],
                    "qty": 1,
                    "rate": float(row.estimated_repair_cost),
                    "description": f"Dommages constatés au retour — {label}",
                }
            )
        missing = max(0.0, float(row.expected_qty or 0) - float(row.returned_qty or 0))
        if row.condition == "Missing" or row.disposition in ("Missing", "Write-off"):
            missing = missing or float(row.expected_qty or 1)
        if missing > 0:
            if not settings["loss_item"]:
                frappe.throw(
                    "De l’équipement manquant est à facturer, mais aucun article « Équipement perdu » n’est "
                    "configuré dans Cortex Company Settings.",
                    frappe.ValidationError,
                )
            replacement = frappe.db.get_value(
                "Cortex Rental Item Profile", {"company": doc.company, "item_code": row.item_code}, "replacement_value"
            )
            charges.append(
                {
                    "item_code": settings["loss_item"],
                    "qty": missing,
                    "rate": float(replacement or 0),
                    "description": f"Équipement non retourné — {label}",
                }
            )
    return charges


def create_final_invoice(doc) -> str:
    """Draft balance invoice from the Sales Order, with advances and check-in charges. Idempotent."""
    if doc.final_invoice and frappe.db.exists("Sales Invoice", doc.final_invoice):
        return doc.final_invoice
    if doc.rental_state not in ("Returned", "Closed", "Quarantine", "Disputed"):
        frappe.throw("La facture de solde se prépare après le retour du matériel.", frappe.ValidationError)
    if not doc.erpnext_sales_order:
        frappe.throw("Cette location n’a pas de commande ERPNext à facturer.", frappe.ValidationError)

    from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

    settings = get_settings(doc.company)
    si = make_sales_invoice(doc.erpnext_sales_order, ignore_permissions=True)
    si.cortex_rental_transaction = doc.name
    for charge in _checkin_charges(doc, settings):
        si.append("items", charge)
    si.allocate_advances_automatically = 1
    if hasattr(si, "set_advances"):
        si.set_advances()
    si.flags.ignore_permissions = True
    si.insert()

    doc.db_set("final_invoice", si.name)
    AuditService.record_mutation(
        company=doc.company,
        action="cortex.billing.final_invoice_drafted",
        entity_type="Cortex Rental Transaction",
        entity_id=doc.name,
        after_state={"sales_invoice": si.name, "grand_total": float(si.grand_total or 0)},
    )
    return si.name


def billing_summary(doc) -> Dict[str, Any]:
    _refresh_payment_readiness(doc)
    currency = frappe.db.get_value("Company", doc.company, "default_currency")
    order = None
    if doc.erpnext_sales_order:
        so = frappe.db.get_value(
            "Sales Order",
            doc.erpnext_sales_order,
            ["name", "status", "docstatus", "grand_total", "advance_paid", "per_billed"],
            as_dict=True,
        )
        if so:
            order = {
                "name": so.name,
                "status": so.status,
                "docstatus": so.docstatus,
                "grand_total": float(so.grand_total or 0),
                "advance_paid": float(so.advance_paid or 0),
                "per_billed": float(so.per_billed or 0),
            }
    payments = [
        {
            "name": pe.name,
            "docstatus": pe.docstatus,
            "posting_date": str(pe.posting_date),
            "paid_amount": float(pe.paid_amount or 0),
            "mode_of_payment": pe.mode_of_payment,
            "reference_no": pe.reference_no,
        }
        for pe in frappe.get_all(
            "Payment Entry",
            filters={"cortex_rental_transaction": doc.name, "docstatus": ["<", 2]},
            fields=["name", "docstatus", "posting_date", "paid_amount", "mode_of_payment", "reference_no"],
            order_by="posting_date asc",
        )
    ]
    invoice = None
    if doc.final_invoice:
        si = frappe.db.get_value(
            "Sales Invoice",
            doc.final_invoice,
            ["name", "status", "docstatus", "grand_total", "total_advance", "outstanding_amount"],
            as_dict=True,
        )
        if si:
            invoice = {
                "name": si.name,
                "status": si.status,
                "docstatus": si.docstatus,
                "grand_total": float(si.grand_total or 0),
                "total_advance": float(si.total_advance or 0),
                "outstanding_amount": float(si.outstanding_amount or 0),
            }
    return {
        "currency": currency,
        "sales_order": order,
        "advance": {
            "percentage_amount": float(doc.advance_percentage_amount or 0),
            "guarantee_amount": float(doc.guarantee_amount or 0),
            "requested": float(doc.advance_amount or 0),
            "received": order["advance_paid"] if order else 0.0,
            "covered": bool(doc.payment_ready),
        },
        "payments": payments,
        "final_invoice": invoice,
    }
