"""Facturation Cortex : taxes, acompte à la réservation, facture à la clôture, frais de retard et paiements.

Les taux, l'acompte et la règle de retard sont ceux de la société (`Cortex Finance Settings`) ; le navigateur n'envoie
jamais un montant de confiance. Les factures sont des instantanés : une fois émises, seuls les paiements les font
évoluer. Tout passe par le serveur et laisse une trace dans le journal d'audit.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

try:
    import frappe
    from frappe.utils import add_days, flt, get_datetime, today
except ImportError:  # tests purs sans Frappe
    frappe = None

    def flt(value, precision=None):
        value = float(value or 0)
        return round(value, precision) if precision is not None else value


SETTINGS_DOCTYPE = "Cortex Finance Settings"
INVOICE = "Cortex Rental Invoice"
PAYMENT = "Cortex Rental Payment"

DEFAULTS: Dict[str, Any] = {
    "apply_taxes": 1,
    "tps_rate": 5.0,
    "tvq_rate": 9.975,
    "tps_number": "",
    "tvq_number": "",
    "deposit_percent": 30.0,
    "invoice_due_days": 0,
    "late_fee_enabled": 0,
    "late_fee_grace_minutes": 60,
    "late_fee_percent": 100.0,
    "late_fee_cap_days": 0.0,
    "damage_billing_enabled": 0,
    "missing_billing_percent": 100.0,
}
CENT = 0.005


def get_settings(company: Optional[str]) -> Dict[str, Any]:
    """Réglages financiers de la société, avec les valeurs par défaut pour ce qui n'est pas configuré."""
    merged = dict(DEFAULTS)
    if frappe and company and frappe.db.exists(SETTINGS_DOCTYPE, company):
        row = frappe.db.get_value(SETTINGS_DOCTYPE, company, list(DEFAULTS), as_dict=True) or {}
        merged.update({key: row[key] for key in DEFAULTS if row.get(key) is not None})
    return merged


def ensure_settings(company: str) -> str:
    """Crée les réglages par défaut d'une société (idempotent)."""
    if not frappe.db.exists(SETTINGS_DOCTYPE, company):
        frappe.get_doc({"doctype": SETTINGS_DOCTYPE, "company": company}).insert(ignore_permissions=True)
    return company


def compute_taxes(subtotal: float, settings: Dict[str, Any]) -> Tuple[float, float]:
    """(TPS, TVQ) sur un sous-total. La TVQ se calcule sur le sous-total, pas sur la TPS."""
    if not settings.get("apply_taxes"):
        return 0.0, 0.0
    return (
        flt(flt(subtotal) * flt(settings.get("tps_rate")) / 100.0, 2),
        flt(flt(subtotal) * flt(settings.get("tvq_rate")) / 100.0, 2),
    )


def combined_rate(settings: Dict[str, Any]) -> float:
    if not settings.get("apply_taxes"):
        return 0.0
    return flt(flt(settings.get("tps_rate")) + flt(settings.get("tvq_rate")), 3)


# ------------------------------------------------------------------ émission
def _active_invoice(transaction: str, invoice_type: str) -> Optional[str]:
    return frappe.db.get_value(
        INVOICE,
        {"rental_transaction": transaction, "invoice_type": invoice_type, "status": ["!=", "Cancelled"]},
        "name",
    )


def _issue(tx, invoice_type: str, lines: List[Dict[str, Any]], settings: Dict[str, Any]):
    subtotal = flt(sum(flt(line["amount"]) for line in lines), 2)
    tps, tvq = compute_taxes(subtotal, settings)
    total = flt(subtotal + tps + tvq, 2)
    doc = frappe.get_doc(
        {
            "doctype": INVOICE,
            "company": tx.company,
            "customer": tx.customer,
            "rental_transaction": tx.name,
            "invoice_type": invoice_type,
            "status": "Issued",
            "issue_date": today(),
            "due_date": add_days(today(), int(settings.get("invoice_due_days") or 0)),
            "lines": lines,
            "subtotal": subtotal,
            "tps_amount": tps,
            "tvq_amount": tvq,
            "tax_amount": flt(tps + tvq, 2),
            "total": total,
            "amount_paid": 0,
            "balance": total,
            "tps_number": settings.get("tps_number") or "",
            "tvq_number": settings.get("tvq_number") or "",
        }
    )
    doc.flags.from_billing = True
    doc.insert(ignore_permissions=True)
    from cortex_rental.services import ledger
    from cortex_rental.services.audit import AuditService

    ledger.post_invoice(doc)
    AuditService.record_mutation(
        company=tx.company,
        action="cortex.invoice.issued",
        entity_type=INVOICE,
        entity_id=doc.name,
        after_state={"rental": tx.name, "type": invoice_type, "total": total},
    )
    return doc


def create_deposit_invoice(tx):
    """Facture d'acompte à la réservation (une seule par location). Sans effet si la société n'en demande pas."""
    settings = get_settings(tx.company)
    percent = flt(settings.get("deposit_percent"))
    if percent <= 0 or flt(tx.subtotal) <= 0:
        return None
    existing = _active_invoice(tx.name, "Deposit")
    if existing:
        return frappe.get_doc(INVOICE, existing)
    amount = flt(flt(tx.subtotal) * percent / 100.0, 2)
    lines = [
        {
            "description": f"Acompte de {percent:g} % — location {tx.name}",
            "line_kind": "Deposit",
            "qty": 1,
            "days": 1,
            "rate": amount,
            "amount": amount,
        }
    ]
    return _issue(tx, "Deposit", lines, settings)


def compute_late_fee(tx, settings: Dict[str, Any]) -> Tuple[float, int]:
    """(montant, jours) de frais de retard selon la règle de la société ; (0, 0) si désactivée ou à l'heure."""
    if not settings.get("late_fee_enabled"):
        return 0.0, 0
    returned_at = frappe.db.sql(
        "SELECT MAX(checked_in_at) FROM `tabCortex Check-In` WHERE transaction = %s AND checked_in_at IS NOT NULL",
        tx.name,
    )[0][0]
    if not returned_at:
        return 0.0, 0
    late_minutes = (get_datetime(returned_at) - get_datetime(tx.ends_at)).total_seconds() / 60.0
    late_minutes -= int(settings.get("late_fee_grace_minutes") or 0)
    if late_minutes <= 0:
        return 0.0, 0
    days = math.ceil(late_minutes / 1440.0)
    cap = flt(settings.get("late_fee_cap_days"))
    if cap > 0:
        days = min(days, int(math.ceil(cap)))
    daily = sum(flt(i.rate) * flt(i.qty) * (1 - flt(i.discount_percentage) / 100.0) for i in tx.items or [])
    return flt(daily * days * flt(settings.get("late_fee_percent")) / 100.0, 2), days


def compute_damage_lines(tx, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Lignes « Dommages et pertes » issues des retours terminés : réparation estimée (abîmé) ou valeur de remplacement (manquant)."""
    if not settings.get("damage_billing_enabled"):
        return []
    rows = frappe.db.sql(
        """SELECT ci.item_code, ci.serial_no, ci.`condition`, ci.expected_qty, ci.returned_qty, ci.estimated_repair_cost
           FROM `tabCortex Check-In Item` ci JOIN `tabCortex Check-In` c ON c.name = ci.parent
           WHERE c.transaction = %s AND c.status = 'Completed' AND ci.`condition` IN ('Damaged', 'Missing')""",
        tx.name,
        as_dict=True,
    )
    lines: List[Dict[str, Any]] = []
    for row in rows:
        name = frappe.db.get_value("Item", row.item_code, "item_name") or row.item_code
        ref = f" ({row.serial_no})" if row.serial_no else ""
        if row.condition == "Damaged":
            amount = flt(row.estimated_repair_cost, 2)
            description = f"Dommages : {name}{ref} (réparation estimée)"
            qty = 1
        else:
            qty = flt(row.expected_qty) or 1
            value = flt(
                frappe.db.get_value(
                    "Cortex Rental Item Profile",
                    {"company": tx.company, "item_code": row.item_code},
                    "replacement_value",
                )
            )
            amount = flt(value * qty * flt(settings.get("missing_billing_percent")) / 100.0, 2)
            description = f"Perte : {name}{ref} × {qty:g} (valeur de remplacement)"
        if amount > 0:
            lines.append(
                {
                    "description": description,
                    "line_kind": "Damage",
                    "qty": qty,
                    "days": 1,
                    "rate": amount / qty,
                    "amount": amount,
                }
            )
    return lines


def create_final_invoice(tx):
    """Facture à la clôture : lignes louées, frais de retard éventuels, moins l'acompte déjà facturé."""
    existing = _active_invoice(tx.name, "Final")
    if existing:
        return frappe.get_doc(INVOICE, existing)
    settings = get_settings(tx.company)
    lines: List[Dict[str, Any]] = []
    for item in tx.items or []:
        label = f"{item.item_name or item.item_code} × {flt(item.qty):g}"
        if flt(item.discount_percentage):
            label += f" (remise {flt(item.discount_percentage):g} %)"
        lines.append(
            {
                "description": label,
                "line_kind": "Rental",
                "item_code": item.item_code,
                "qty": flt(item.qty),
                "days": flt(item.billable_days),
                "rate": flt(item.rate),
                "amount": flt(item.amount),
            }
        )
    fee, days = compute_late_fee(tx, settings)
    if fee > 0:
        lines.append(
            {
                "description": f"Frais de retard : {days} jour(s) supplémentaire(s)",
                "line_kind": "Late Fee",
                "qty": 1,
                "days": days,
                "rate": fee,
                "amount": fee,
            }
        )
    lines.extend(compute_damage_lines(tx, settings))
    deposits = frappe.get_all(
        INVOICE,
        filters={"rental_transaction": tx.name, "invoice_type": "Deposit", "status": ["!=", "Cancelled"]},
        fields=["name", "subtotal"],
    )
    for deposit in deposits:
        lines.append(
            {
                "description": f"Moins : acompte facturé ({deposit.name})",
                "line_kind": "Deposit Credit",
                "qty": 1,
                "days": 1,
                "rate": -flt(deposit.subtotal),
                "amount": -flt(deposit.subtotal),
            }
        )
    return _issue(tx, "Final", lines, settings)


def cancel_unpaid_deposits(tx) -> None:
    """Une location annulée n'a plus à payer son acompte ; un acompte déjà encaissé reste pour décision de la finance."""
    for name in frappe.get_all(
        INVOICE, filters={"rental_transaction": tx.name, "invoice_type": "Deposit", "status": "Issued"}, pluck="name"
    ):
        if flt(frappe.db.get_value(INVOICE, name, "amount_paid")) == 0:
            frappe.db.set_value(INVOICE, name, {"status": "Cancelled", "balance": 0})
            from cortex_rental.services import ledger

            ledger.post_reversal(frappe.get_doc(INVOICE, name))


def on_transition(tx, new_state: str) -> None:
    """Appelé par la location après un changement d'état réussi."""
    if new_state in ("Reservation", "Contract"):
        create_deposit_invoice(tx)
    elif new_state == "Closed":
        create_final_invoice(tx)
    elif new_state == "Cancelled":
        cancel_unpaid_deposits(tx)


# ------------------------------------------------------------------ paiements
def refresh_invoice(name: str) -> None:
    """Recalcule le montant payé, le solde et l'état d'une facture à partir de ses paiements."""
    invoice = frappe.db.get_value(
        INVOICE, name, ["total", "status", "rental_transaction", "invoice_type"], as_dict=True
    )
    if not invoice or invoice.status == "Cancelled":
        return
    paid = flt(
        frappe.db.sql(
            "SELECT COALESCE(SUM(signed_amount), 0) FROM `tabCortex Rental Payment` WHERE invoice = %s", name
        )[0][0],
        2,
    )
    balance = flt(flt(invoice.total) - paid, 2)
    if balance <= CENT:
        status = "Paid"
    elif paid > CENT:
        status = "Partially Paid"
    else:
        status = "Issued"
    frappe.db.set_value(INVOICE, name, {"amount_paid": paid, "balance": max(balance, 0), "status": status})
    if invoice.invoice_type == "Deposit" and status == "Paid":
        # L'acompte encaissé remplit le prérequis « paiement ou dépôt prêt » du contrat.
        frappe.db.set_value(
            "Cortex Rental Transaction", invoice.rental_transaction, "payment_ready", 1, update_modified=False
        )


def record_payment(
    invoice: str,
    amount: float,
    method: str = "Card",
    paid_on: Optional[str] = None,
    reference: Optional[str] = None,
    kind: str = "Payment",
    notes: Optional[str] = None,
    ignore_permissions: bool = False,
):
    """`ignore_permissions` : seulement pour un paiement confirmé par le fournisseur (webhook signé), jamais pour un appel d'un utilisateur."""
    company = frappe.db.get_value(INVOICE, invoice, "company")
    if not company:
        frappe.throw("Facture introuvable.", frappe.DoesNotExistError)
    doc = frappe.get_doc(
        {
            "doctype": PAYMENT,
            "company": company,
            "invoice": invoice,
            "kind": kind,
            "method": method,
            "amount": flt(amount, 2),
            "paid_on": paid_on or today(),
            "reference": reference or "",
            "notes": notes or "",
        }
    )
    doc.insert(ignore_permissions=ignore_permissions)
    _sync_share_payment(invoice)
    return doc


def _sync_share_payment(invoice: str) -> None:
    """Quand l'acompte d'un devis partagé est entièrement payé (par chèque ou autrement), la page du client le sait."""
    try:
        if frappe.db.get_value(INVOICE, invoice, "status") != "Paid":
            return
        for name in frappe.get_all(
            "Cortex Quote Share", filters={"deposit_invoice": invoice, "payment_status": ["!=", "Paid"]}, pluck="name"
        ):
            frappe.db.set_value("Cortex Quote Share", name, "payment_status", "Paid")
    except Exception:
        frappe.log_error(title="Cortex share payment sync failed")


def validate_payment(doc) -> None:
    """Règles d'un paiement : facture active de la même société, montant positif, jamais au-delà du solde."""
    invoice = frappe.db.get_value(
        INVOICE, doc.invoice, ["company", "status", "total", "amount_paid"], as_dict=True, for_update=True
    )
    if not invoice:
        frappe.throw("Facture introuvable.", frappe.DoesNotExistError)
    if invoice.company != doc.company:
        frappe.throw("Cette facture appartient à une autre société.", frappe.PermissionError)
    if invoice.status == "Cancelled":
        frappe.throw("Cette facture est annulée : aucun paiement n'est possible.", frappe.ValidationError)
    amount = flt(doc.amount, 2)
    if amount <= 0:
        frappe.throw("Le montant doit être supérieur à zéro.", frappe.ValidationError)
    if doc.kind == "Refund":
        if amount > flt(invoice.amount_paid) + CENT:
            frappe.throw("Le remboursement dépasse le montant déjà encaissé.", frappe.ValidationError)
        doc.signed_amount = -amount
    else:
        if amount > flt(invoice.total) - flt(invoice.amount_paid) + CENT:
            frappe.throw("Le paiement dépasse le solde de la facture.", frappe.ValidationError)
        doc.signed_amount = amount
    doc.amount = amount
