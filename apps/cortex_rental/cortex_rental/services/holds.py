"""Retenue du matériel par un devis : dès qu'un devis existe, les unités demandées sont retenues dans la disponibilité.

Règles (docs/adr/ADR-008-retenue-par-devis.md) :
- La retenue est prise sous le verrou de réservation de chaque article et vérifiée avec la disponibilité réelle (autres
  retenues comprises) : deux devis ne retiennent jamais la même dernière unité.
- Elle expire seule (`hold_until`), sans tâche planifiée : la disponibilité ne compte que les retenues encore valides.
- Si le matériel n'est pas disponible, le devis est créé quand même (on peut négocier) mais **sans retenue**, avec la
  quantité libre indiquée : rien n'est retenu en silence ni promis.
- Une retenue n'est pas une réservation : seule la réservation (sous verrou) garantit le matériel.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
    from frappe.utils import add_to_date, now_datetime
except ImportError:
    frappe = None

DEFAULT_HOURS = 72
MAX_HOURS = 24 * 60


def settings(company: str) -> Dict[str, Any]:
    row = (
        frappe.db.get_value(
            "Cortex Finance Settings", company, ["quote_hold_enabled", "quote_hold_hours"], as_dict=True
        )
        if frappe.db.exists("Cortex Finance Settings", company)
        else None
    ) or {}
    enabled = row.get("quote_hold_enabled")
    return {
        "enabled": True if enabled is None else bool(enabled),
        "hours": max(1, min(int(row.get("quote_hold_hours") or DEFAULT_HOURS), MAX_HOURS)),
    }


def _requests(tx) -> List[Dict[str, Any]]:
    return [{"item_id": row.item_code, "quantity": float(row.qty or 0)} for row in tx.items or [] if row.item_code]


def evaluate(tx, until=None) -> Dict[str, Any]:
    """Prend (ou refuse) la retenue d'un devis. Sous verrou ; la valeur est écrite en base, puis validée avant de relâcher."""
    from contextlib import ExitStack

    from cortex_rental.services.availability import AvailabilityService
    from cortex_rental.services.locking import ReservationLockError, reservation_lock

    conf = settings(tx.company)
    if not conf["enabled"] or tx.rental_state != "Quote" or not (tx.items or []):
        return {"status": "", "until": None, "note": ""}
    until = until or add_to_date(now_datetime(), hours=conf["hours"])
    codes = sorted({row.item_code for row in tx.items or [] if row.item_code})
    with ExitStack() as locks:
        try:
            for code in codes:
                locks.enter_context(reservation_lock(tx.company, code))
        except ReservationLockError:
            return {
                "status": "",
                "until": None,
                "note": "Retenue non prise : le matériel est en cours de traitement, réessayez.",
            }
        if not frappe.flags.in_test:
            frappe.db.commit()  # nosemgrep : voir les réservations validées par celui qui vient de libérer le verrou
        checks = AvailabilityService().check(
            company=tx.company,
            starts_at=str(tx.starts_at),
            ends_at=str(tx.ends_at),
            item_requests=_requests(tx),
            exclude_transaction=tx.name,
        )
        short = [c for c in checks if not c["is_available"]]
        if short:
            note = "Disponibilité insuffisante, aucune retenue : " + "; ".join(
                f"{c['item_id']} ({c['available_quantity']:g} libre(s) sur {c['requested_quantity']:g} demandé(s))"
                for c in short
            )
            result = {"status": "Insufficient", "until": None, "note": note[:400]}
        else:
            result = {"status": "Active", "until": until, "note": ""}
        _write(tx.name, result)
        if not frappe.flags.in_test:
            frappe.db.commit()  # nosemgrep : la retenue doit être visible avant de relâcher le verrou
    return result


def _write(name: str, result: Dict[str, Any]) -> None:
    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        {
            "hold_status": result["status"],
            "hold_until": result["until"],
            "hold_note": result["note"],
            "hold_notified": 0,
        },
        update_modified=False,
    )


def release(name: str, reason: str = "") -> None:
    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        {"hold_status": "Released", "hold_until": None, "hold_note": reason[:400]},
        update_modified=False,
    )


def extend_to(tx, until) -> Dict[str, Any]:
    """Prolonge la retenue (ex. quand le devis est partagé avec le client) : revérifiée, jamais raccourcie."""
    current = tx.hold_until
    if current and frappe.utils.get_datetime(current) >= frappe.utils.get_datetime(until):
        return {"status": tx.hold_status, "until": current, "note": ""}
    return evaluate(tx, until=until)


def is_active(hold_until: Optional[Any]) -> bool:
    return bool(hold_until) and frappe.utils.get_datetime(hold_until) > now_datetime()
