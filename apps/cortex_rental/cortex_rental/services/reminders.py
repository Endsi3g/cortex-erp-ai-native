"""Rappels automatiques (planificateur, toutes les heures) : ce qui expire, ce qui est en retard, ce qui attend une réponse.

Chaque rappel est une notification pour la personne responsable du dossier (celle qui l'a créé), sans doublon sur 24 h.
Rien n'est modifié dans les dossiers : les rappels informent, les gens décident.
"""

from typing import Any, Dict, List

try:
    import frappe
    from frappe.utils import add_to_date, now_datetime, today
except ImportError:
    frappe = None

SKIP_USERS = ("Administrator", "Guest")


def _notify(user: str, subject: str, doctype: str, name: str) -> bool:
    if not user or user in SKIP_USERS:
        return False
    since = add_to_date(now_datetime(), hours=-24)
    if frappe.db.exists(
        "Notification Log",
        {"for_user": user, "subject": subject, "document_name": name, "creation": [">", since]},
    ):
        return False
    frappe.get_doc(
        {
            "doctype": "Notification Log",
            "for_user": user,
            "type": "Alert",
            "subject": subject,
            "document_type": doctype,
            "document_name": name,
        }
    ).insert(ignore_permissions=True)
    return True


def holds_expiring() -> int:
    """Devis dont la retenue expire dans moins de 24 h : on prévient avant que le matériel soit relâché."""
    soon = add_to_date(now_datetime(), hours=24)
    rows = frappe.get_all(
        "Cortex Rental Transaction",
        filters={
            "rental_state": "Quote",
            "hold_status": "Active",
            "hold_notified": 0,
            "hold_until": ["between", [now_datetime(), soon]],
        },
        fields=["name", "owner", "hold_until"],
        limit_page_length=500,
    )
    count = 0
    for row in rows:
        if _notify(
            row.owner,
            f"La retenue du devis {row.name} expire bientôt : prolongez-la ou réservez.",
            "Cortex Rental Transaction",
            row.name,
        ):
            count += 1
        frappe.db.set_value("Cortex Rental Transaction", row.name, "hold_notified", 1, update_modified=False)
    return count


def late_returns() -> int:
    """Matériel sorti dont la date de retour est dépassée (les frais de retard sont calculés à la clôture)."""
    rows = frappe.get_all(
        "Cortex Rental Transaction",
        filters={"rental_state": "Checked Out", "ends_at": ["<", add_to_date(now_datetime(), hours=-1)]},
        fields=["name", "owner", "customer", "ends_at"],
        limit_page_length=500,
    )
    return sum(
        1
        for r in rows
        if _notify(
            r.owner,
            f"Retour en retard : {r.name} ({r.customer}) devait revenir le {str(r.ends_at)[:16]}.",
            "Cortex Rental Transaction",
            r.name,
        )
    )


def quotes_without_answer() -> int:
    """Liens de devis envoyés, ouverts ou non, qui expirent dans 48 h sans réponse du client."""
    rows = frappe.get_all(
        "Cortex Quote Share",
        filters={
            "status": "Active",
            "expires_at": ["between", [now_datetime(), add_to_date(now_datetime(), hours=48)]],
        },
        fields=["name", "owner", "rental_transaction", "customer_name", "view_count"],
        limit_page_length=500,
    )
    return sum(
        1
        for r in rows
        if _notify(
            r.owner,
            f"{r.customer_name} n'a pas répondu au devis {r.rental_transaction} ({'ouvert' if r.view_count else 'jamais ouvert'}) : le lien expire dans moins de 48 h.",
            "Cortex Rental Transaction",
            r.rental_transaction,
        )
    )


def unpaid_invoices() -> int:
    """Factures échues et impayées : rappel à la personne qui a créé la location."""
    rows = frappe.get_all(
        "Cortex Rental Invoice",
        filters={"status": ["in", ["Issued", "Partially Paid"]], "due_date": ["<", today()], "balance": [">", 0]},
        fields=["name", "rental_transaction", "customer", "balance"],
        limit_page_length=500,
    )
    count = 0
    for r in rows:
        owner = (
            frappe.db.get_value("Cortex Rental Transaction", r.rental_transaction, "owner")
            if r.rental_transaction
            else None
        )
        if _notify(
            owner,
            f"Facture {r.name} échue et impayée ({r.customer}) : solde {r.balance:.2f} $.",
            "Cortex Rental Invoice",
            r.name,
        ):
            count += 1
    return count


def hourly() -> Dict[str, Any]:
    """Point d'entrée du planificateur : une panne d'un rappel n'empêche pas les autres."""
    out: Dict[str, Any] = {}
    jobs: List = [holds_expiring, late_returns, quotes_without_answer, unpaid_invoices]
    for job in jobs:
        try:
            out[job.__name__] = job()
        except Exception:
            frappe.log_error(title=f"Cortex reminder failed: {job.__name__}")
            out[job.__name__] = "error"
    return out
