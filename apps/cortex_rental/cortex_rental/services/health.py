"""Vérifications de santé : « vivant » (le processus répond) et « prêt » (il peut vraiment servir).

Rien de sensible n'est exposé : seulement des booléens (pas de version, pas de nom de serveur). Chaque vérification est
isolée : une panne de l'une ne fait jamais planter les autres ni la page."""

import os
from typing import Any, Callable, Dict

try:
    import frappe
except ImportError:
    frappe = None

APP = "cortex_rental"
SCHEDULER_MAX_SILENCE_HOURS = 3


def pending_patches(patch_file_lines, applied) -> list:
    """Pur : les correctifs de patches.txt (hors en-têtes et commentaires) qui ne sont pas encore appliqués."""
    wanted = []
    for raw in patch_file_lines:
        line = raw.strip()
        if not line or line.startswith(("#", "[")):
            continue
        wanted.append(line.split("#")[0].strip())
    done = set(applied)
    return [p for p in wanted if p not in done]


def _database() -> bool:
    frappe.db.sql("SELECT 1")
    return True


def _cache() -> bool:
    cache = frappe.cache() if callable(getattr(frappe, "cache", None)) else frappe.cache
    key = "cortex_health_probe"
    cache.set_value(key, "1", expires_in_sec=30)
    return cache.get_value(key) == "1"


def _migrations() -> bool:
    path = os.path.join(frappe.get_app_path(APP), "patches.txt")
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    applied = frappe.get_all("Patch Log", filters={"patch": ["like", f"{APP}.%"]}, pluck="patch", limit_page_length=0)
    return not pending_patches(lines, applied)


def _scheduler() -> bool:
    """Le planificateur est actif et a exécuté une tâche récemment (des tâches horaires existent)."""
    from frappe.utils import add_to_date, now_datetime
    from frappe.utils.scheduler import is_scheduler_disabled

    if is_scheduler_disabled():
        return False
    recent = frappe.get_all(
        "Scheduled Job Log",
        filters={"creation": [">", add_to_date(now_datetime(), hours=-SCHEDULER_MAX_SILENCE_HOURS)]},
        limit_page_length=1,
    )
    return bool(recent)


CHECKS: Dict[str, Callable[[], bool]] = {
    "database": _database,
    "cache": _cache,
    "migrations": _migrations,
    "scheduler": _scheduler,
}
# Seules la base de données et le cache rendent le service inutilisable; les autres signalent un état dégradé.
CRITICAL = ("database", "cache")


def liveness() -> Dict[str, Any]:
    return {"status": "ok"}


def readiness() -> Dict[str, Any]:
    results: Dict[str, bool] = {}
    for name, check in CHECKS.items():
        try:
            results[name] = bool(check())
        except Exception:
            results[name] = False
            if frappe:
                frappe.log_error(title=f"Cortex : vérification de santé « {name} » en échec")
    critical_ok = all(results.get(name) for name in CRITICAL)
    status = "ok" if all(results.values()) else ("degraded" if critical_ok else "down")
    return {"status": status, "checks": results}
