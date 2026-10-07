"""Résumé de disponibilité par équipement pour une période : libre au pire jour, pic de réservations, statut.

Même règle que la grille de disponibilité (réservations, contrats et sorties bloquent; un devis retient tant que sa
retenue est valide). Calculé par le serveur : l'assistant ne dit « libre » que d'après ce calcul."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

BLOCKING = ("Reservation", "Contract", "Checked Out")
MAX_DAYS = 90
FMT = "%Y-%m-%d %H:%M:%S"


def _day_start(value: Any) -> datetime:
    text = str(value)[:10]
    return datetime.strptime(text, "%Y-%m-%d")


def summarize(items: List[Dict[str, Any]], starts_at: Any, ends_at: Any, now: datetime) -> List[Dict[str, Any]]:
    """Pur : transforme les équipements (avec leurs `blocks`) en résumé par équipement."""
    first = _day_start(starts_at)
    last = _day_start(ends_at)
    if last < first:
        raise ValueError("La fin de la période doit être après son début.")
    days = (last - first).days + 1
    if days > MAX_DAYS:
        raise ValueError(f"La période dépasse {MAX_DAYS} jours : choisissez une période plus courte.")
    now_text = now.strftime(FMT)
    rows = []
    for item in items:
        fleet = float(item.get("fleet_quantity") or 0)
        worst_free = fleet
        peak_booked = peak_held = 0.0
        for offset in range(days):
            start = (first + timedelta(days=offset)).strftime(FMT)
            end = (first + timedelta(days=offset + 1)).strftime(FMT)
            overlapping = [
                b for b in item.get("blocks") or [] if str(b["starts_at"]) < end and str(b["ends_at"]) > start
            ]
            booked = sum(float(b.get("qty") or 0) for b in overlapping if b.get("rental_state") in BLOCKING)
            held = sum(
                float(b.get("qty") or 0)
                for b in overlapping
                if b.get("rental_state") == "Quote" and b.get("hold_until") and str(b["hold_until"]) > now_text
            )
            worst_free = min(worst_free, fleet - booked - held)
            peak_booked = max(peak_booked, booked)
            peak_held = max(peak_held, held)
        if fleet <= 0:
            status = "none"
        elif worst_free <= 0:
            status = "full"
        elif peak_booked + peak_held > 0:
            status = "partial"
        else:
            status = "ok"
        rows.append(
            {
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "category": item.get("category"),
                "fleet": fleet,
                "free": max(worst_free, 0.0),
                "booked": peak_booked,
                "held": peak_held,
                "status": status,
            }
        )
    return rows


def day_statuses(items: List[Dict[str, Any]], first_day: Any, days: int, now: datetime) -> List[Dict[str, Any]]:
    """Pur : un statut par jour et par équipement, sans aucune quantité ni nom de client (affichage public).

    ok = libre; partial = en partie réservé ou retenu; full = complet; none = aucun parc réservable.
    Même règle que la grille interne (réservations, contrats et sorties bloquent; un devis retient tant que sa retenue
    est valide)."""
    first = _day_start(first_day)
    if days < 1 or days > MAX_DAYS:
        raise ValueError(f"La période doit compter de 1 à {MAX_DAYS} jours.")
    now_text = now.strftime(FMT)
    rows = []
    for item in items:
        fleet = float(item.get("fleet_quantity") or 0)
        statuses = []
        for offset in range(days):
            start = (first + timedelta(days=offset)).strftime(FMT)
            end = (first + timedelta(days=offset + 1)).strftime(FMT)
            overlapping = [
                b for b in item.get("blocks") or [] if str(b["starts_at"]) < end and str(b["ends_at"]) > start
            ]
            booked = sum(float(b.get("qty") or 0) for b in overlapping if b.get("rental_state") in BLOCKING)
            held = sum(
                float(b.get("qty") or 0)
                for b in overlapping
                if b.get("rental_state") == "Quote" and b.get("hold_until") and str(b["hold_until"]) > now_text
            )
            free = fleet - booked - held
            if fleet <= 0:
                statuses.append("none")
            elif free <= 0:
                statuses.append("full")
            elif booked + held > 0:
                statuses.append("partial")
            else:
                statuses.append("ok")
        rows.append(
            {
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "category": item.get("category"),
                "days": statuses,
            }
        )
    return rows
