"""Écritures comptables à partie double, générées à chaque facture et paiement pour le comptable de la société.

Plan de comptes : celui de `Cortex Finance Settings` (format « numéro - nom »), modifiable par la société. Une
écriture est toujours équilibrée, liée à sa source (facture ou paiement) et immuable ; une annulation passe par une
écriture inverse. Une même source ne produit jamais deux écritures.

  Facture d'acompte     Dr Comptes clients        Cr Acomptes clients, TPS à remettre, TVQ à remettre
  Facture finale        Dr Comptes clients, Acomptes clients (acompte appliqué)
                        Cr Revenus de location, Frais de retard, TPS à remettre, TVQ à remettre
  Paiement              Dr Encaisse et banque     Cr Comptes clients
  Remboursement         Dr Comptes clients        Cr Encaisse et banque
  Acompte annulé        Dr Acomptes clients, TPS, TVQ    Cr Comptes clients
"""

from typing import Any, Dict, List, Optional, Tuple

try:
    import frappe
    from frappe.utils import flt
except ImportError:
    frappe = None

    def flt(value, precision=None):
        value = float(value or 0)
        return round(value, precision) if precision is not None else value


JOURNAL = "Cortex Journal Entry"
SETTING_FIELDS = {
    "receivable": "acct_receivable",
    "cash": "acct_cash",
    "deposits": "acct_deposits",
    "tps": "acct_tps",
    "tvq": "acct_tvq",
    "revenue": "acct_revenue",
    "late_fees": "acct_late_fees",
    "damages": "acct_damages",
}
DEFAULT_ACCOUNTS = {
    "receivable": "1100 - Comptes clients",
    "cash": "1000 - Encaisse et banque",
    "deposits": "2400 - Acomptes clients",
    "tps": "2310 - TPS à remettre",
    "tvq": "2320 - TVQ à remettre",
    "revenue": "4000 - Revenus de location",
    "late_fees": "4100 - Frais de retard",
    "damages": "4200 - Dommages et pertes facturés",
}
TOLERANCE = 0.005

Line = Tuple[str, float, float]  # (clé de compte, débit, crédit)


def split_account(value: str) -> Tuple[str, str]:
    """« 1100 - Comptes clients » → (« 1100 », « Comptes clients »)."""
    number, _, name = (value or "").partition(" - ")
    return (number.strip(), name.strip() or number.strip()) if name else ("", (value or "").strip())


def accounts_for(company: str) -> Dict[str, Tuple[str, str]]:
    values = dict(DEFAULT_ACCOUNTS)
    if frappe and company and frappe.db.exists("Cortex Finance Settings", company):
        row = frappe.db.get_value("Cortex Finance Settings", company, list(SETTING_FIELDS.values()), as_dict=True) or {}
        for key, field in SETTING_FIELDS.items():
            if row.get(field):
                values[key] = row[field]
    return {key: split_account(value) for key, value in values.items()}


def is_balanced(lines: List[Line]) -> bool:
    return abs(sum(d for _, d, _ in lines) - sum(c for _, _, c in lines)) <= TOLERANCE


def _exists(source_doctype: str, source_name: str, source_type: str) -> bool:
    return bool(
        frappe.db.exists(
            JOURNAL, {"source_doctype": source_doctype, "source_name": source_name, "source_type": source_type}
        )
    )


def post(
    company: str,
    posting_date: Any,
    source_type: str,
    source_doctype: str,
    source_name: str,
    description: str,
    lines: List[Line],
    rental: Optional[str] = None,
    customer: Optional[str] = None,
):
    """Crée l'écriture (idempotent par source et type). Les lignes à zéro sont omises."""
    lines = [(key, flt(d, 2), flt(c, 2)) for key, d, c in lines if flt(d, 2) or flt(c, 2)]
    if not lines:
        return None
    if not is_balanced(lines):
        frappe.throw(f"Écriture déséquilibrée pour {source_name} : {lines}", frappe.ValidationError)
    if _exists(source_doctype, source_name, source_type):
        return None
    accounts = accounts_for(company)
    doc = frappe.get_doc(
        {
            "doctype": JOURNAL,
            "company": company,
            "posting_date": posting_date,
            "source_type": source_type,
            "source_doctype": source_doctype,
            "source_name": source_name,
            "rental_transaction": rental,
            "customer": customer,
            "description": description,
            "lines": [
                {
                    "account_number": accounts[key][0],
                    "account_name": accounts[key][1],
                    "debit": d,
                    "credit": c,
                }
                for key, d, c in lines
            ],
        }
    )
    doc.flags.from_ledger = True
    doc.insert(ignore_permissions=True)
    return doc


def post_invoice(invoice):
    """Écriture d'une facture émise (acompte ou finale)."""
    total, tps, tvq = flt(invoice.total), flt(invoice.tps_amount), flt(invoice.tvq_amount)
    by_kind: Dict[str, float] = {}
    for line in invoice.lines or []:
        kind = line.line_kind or "Rental"
        by_kind[kind] = by_kind.get(kind, 0.0) + flt(line.amount)
    lines: List[Line] = [("receivable", total, 0)]
    if invoice.invoice_type == "Deposit":
        lines += [("deposits", 0, by_kind.get("Deposit", 0.0))]
    else:
        applied = -by_kind.get("Deposit Credit", 0.0)  # ligne négative : acompte déjà facturé
        lines += [
            ("deposits", applied, 0),
            ("revenue", 0, by_kind.get("Rental", 0.0)),
            ("late_fees", 0, by_kind.get("Late Fee", 0.0)),
            ("damages", 0, by_kind.get("Damage", 0.0)),
        ]
    lines += [("tps", 0, tps), ("tvq", 0, tvq)]
    label = "Facture d'acompte" if invoice.invoice_type == "Deposit" else "Facture finale"
    return post(
        invoice.company,
        invoice.issue_date,
        "Invoice",
        "Cortex Rental Invoice",
        invoice.name,
        f"{label} {invoice.name} — location {invoice.rental_transaction}",
        lines,
        rental=invoice.rental_transaction,
        customer=invoice.customer,
    )


def post_payment(payment):
    """Écriture d'un paiement ou d'un remboursement."""
    amount = flt(payment.amount)
    refund = payment.kind == "Refund"
    lines: List[Line] = (
        [("receivable", amount, 0), ("cash", 0, amount)] if refund else [("cash", amount, 0), ("receivable", 0, amount)]
    )
    label = "Remboursement" if refund else "Paiement"
    return post(
        payment.company,
        payment.paid_on,
        "Payment",
        "Cortex Rental Payment",
        payment.name,
        f"{label} {payment.name} — facture {payment.invoice}",
        lines,
        rental=payment.rental_transaction,
        customer=payment.customer,
    )


def post_reversal(invoice):
    """Écriture inverse d'une facture d'acompte annulée (aucun paiement reçu)."""
    deposit = sum(flt(line.amount) for line in invoice.lines or [] if (line.line_kind or "") == "Deposit")
    lines: List[Line] = [
        ("deposits", deposit, 0),
        ("tps", flt(invoice.tps_amount), 0),
        ("tvq", flt(invoice.tvq_amount), 0),
        ("receivable", 0, flt(invoice.total)),
    ]
    return post(
        invoice.company,
        frappe.utils.today(),
        "Reversal",
        "Cortex Rental Invoice",
        invoice.name,
        f"Annulation de la facture d'acompte {invoice.name}",
        lines,
        rental=invoice.rental_transaction,
        customer=invoice.customer,
    )
