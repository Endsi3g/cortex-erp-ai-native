"""Small helpers shared by the read-only Cortex UI endpoints."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

try:
    import frappe
except ImportError:
    frappe = None

MAX_PAGE_SIZE = 100
MAX_RAW_TEXT = 20000


def now_iso() -> str:
    if frappe:
        return frappe.utils.now_datetime().isoformat()
    return datetime.now(timezone.utc).isoformat()


def envelope(data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap a payload with the provenance fields every Cortex read contract carries."""
    return {"data": {"provenance": "api", "last_synced_at": now_iso(), **data}}


MAX_PAGE = 100_000


def to_int(value: Any, default: int, low: int, high: int) -> int:
    """Entier tolérant : une valeur absente, vide, non numérique ou démesurée donne le défaut ou la borne, jamais une erreur."""
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError, OverflowError):
        return default
    return max(low, min(number, high))


def page_args(page: Any, page_size: Any) -> Tuple[int, int]:
    return to_int(page, 1, 1, MAX_PAGE), to_int(page_size, 20, 1, MAX_PAGE_SIZE)


def parse_json(value: Any, default: Any) -> Any:
    """Parse a Code/Small Text field that stores JSON; never raise on bad data."""
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return default
    return parsed if isinstance(parsed, type(default)) else default


def split_lines(value: Any) -> List[str]:
    """Split a Small Text list stored one entry per line or comma separated."""
    if not value:
        return []
    return [part.strip() for chunk in str(value).splitlines() for part in chunk.split(",") if part.strip()]


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
