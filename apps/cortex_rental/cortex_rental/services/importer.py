"""CSV import: parsing, column mapping and row validation.

Pure functions (no frappe) so every rule is unit-tested. api/v1/imports.py
runs them against the site through `lookups` and creates the documents.
"""

import csv
import io
import re
import unicodedata
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

MAX_ROWS = 5000
MAX_FILE_BYTES = 5 * 1024 * 1024

CATEGORIES = [
    "Camera Bodies",
    "Cinema Lenses",
    "Lighting",
    "Grip & Rigging",
    "Audio",
    "Monitors & Wireless Video",
    "Power & Batteries",
]

# field: (label, required, kind, aliases)
SPECS: Dict[str, Dict[str, Tuple[str, bool, str, Tuple[str, ...]]]] = {
    "Customers": {
        "customer_name": (
            "Nom du client",
            True,
            "text",
            ("nom", "name", "client", "customer", "raison sociale", "company"),
        ),
        "customer_type": ("Type (Company / Individual)", False, "customer_type", ("type",)),
        "email": ("Courriel", False, "email", ("courriel", "e-mail", "mail")),
        "phone": ("Téléphone", False, "text", ("telephone", "tel", "mobile", "cellulaire")),
        "insurance_valid_until": ("Assurance valide jusqu’au", False, "date", ("assurance", "insurance")),
    },
    "Equipment": {
        "item_code": ("Code article", True, "text", ("code", "sku", "item", "article")),
        "item_name": ("Nom", True, "text", ("nom", "name", "designation", "description")),
        "daily_rate": ("Tarif journalier", True, "money", ("tarif", "rate", "prix", "price", "daily rate")),
        "replacement_value": ("Valeur de remplacement", False, "money", ("valeur", "replacement", "value")),
        "deposit_required": ("Dépôt requis", False, "money", ("depot", "deposit", "garantie")),
        "category": ("Catégorie", False, "category", ("categorie", "category")),
        "is_serialized": ("Suivi par numéro de série", False, "bool", ("serialise", "serialized", "serie")),
    },
    "Serial Numbers": {
        "serial_no": ("Numéro de série", True, "text", ("serial", "numero de serie", "sn", "serie")),
        "item_code": ("Code article", True, "text", ("code", "sku", "item", "article")),
        "consignment_owner": ("Propriétaire (code)", False, "text", ("proprietaire", "owner", "consignataire")),
        "warranty_expiry_date": ("Fin de garantie", False, "date", ("garantie", "warranty")),
    },
}

TRUE_VALUES = {"1", "oui", "yes", "true", "vrai", "x", "y", "o"}
FALSE_VALUES = {"0", "non", "no", "false", "faux", "n", ""}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse_csv(content: bytes) -> Tuple[List[str], List[List[str]]]:
    """Headers and data rows. Accepts UTF-8 (with or without BOM) or Latin-1, `,` `;` or tab."""
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Fichier trop volumineux (5 Mo maximum).")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    if not text.strip():
        raise ValueError("Le fichier est vide.")
    first_line = text.splitlines()[0]
    delimiter = max((",", ";", "\t"), key=first_line.count)
    rows = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter) if any(cell.strip() for cell in row)]
    headers = [cell.strip() for cell in rows[0]]
    if not all(headers):
        raise ValueError("Chaque colonne doit avoir un en-tête.")
    if len({_norm(h) for h in headers}) != len(headers):
        raise ValueError("Deux colonnes portent le même en-tête.")
    data = rows[1:]
    if not data:
        raise ValueError("Le fichier ne contient aucune ligne de données.")
    if len(data) > MAX_ROWS:
        raise ValueError(f"Trop de lignes ({len(data)}) : {MAX_ROWS} maximum par lot.")
    width = len(headers)
    return headers, [(row + [""] * width)[:width] for row in data]


def suggest_mapping(import_type: str, headers: List[str]) -> Dict[str, Optional[str]]:
    """Target field -> source header, matched on the field name, its label or an alias."""
    spec = SPECS[import_type]
    by_norm = {_norm(h): h for h in headers}
    mapping: Dict[str, Optional[str]] = {}
    used = set()
    for field, (label, _required, _kind, aliases) in spec.items():
        match = None
        for candidate in (field, label, *aliases):
            header = by_norm.get(_norm(candidate))
            if header and header not in used:
                match = header
                break
        mapping[field] = match
        if match:
            used.add(match)
    return mapping


def check_mapping(import_type: str, headers: List[str], mapping: Dict[str, Optional[str]]) -> List[str]:
    spec = SPECS[import_type]
    errors = []
    unknown = sorted(set(mapping) - set(spec))
    if unknown:
        errors.append(f"Champs inconnus : {', '.join(unknown)}")
    for field, (label, required, _kind, _aliases) in spec.items():
        source = mapping.get(field)
        if source and source not in headers:
            errors.append(f"Colonne « {source} » absente du fichier.")
        if required and not source:
            errors.append(f"« {label} » doit être associé à une colonne.")
    sources = [s for s in mapping.values() if s]
    if len(sources) != len(set(sources)):
        errors.append("Une même colonne est associée à deux champs.")
    return errors


def _money(raw: str) -> float:
    text = raw.replace(" ", "").replace(" ", "").replace("$", "").replace("CAD", "")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    value = float(text)
    if value < 0:
        raise ValueError
    return round(value, 2)


def _date(raw: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError


def convert(kind: str, raw: str) -> Any:
    """Typed value, or ValueError with nothing half-parsed."""
    raw = (raw or "").strip()
    if kind in ("text",):
        return raw
    if not raw:
        return None
    if kind == "money":
        return _money(raw)
    if kind == "date":
        return _date(raw)
    if kind == "bool":
        low = raw.lower()
        if low in TRUE_VALUES:
            return True
        if low in FALSE_VALUES:
            return False
        raise ValueError
    if kind == "email":
        if not EMAIL_RE.match(raw):
            raise ValueError
        return raw
    if kind == "customer_type":
        low = _norm(raw)
        if low in ("company", "entreprise", "societe", "compagnie"):
            return "Company"
        if low in ("individual", "particulier", "individu", "personne"):
            return "Individual"
        raise ValueError
    if kind == "category":
        match = next((c for c in CATEGORIES if _norm(c) == _norm(raw)), None)
        if not match:
            raise ValueError
        return match
    raise ValueError


Lookup = Callable[[str, str], bool]


def validate_rows(
    import_type: str,
    headers: List[str],
    rows: List[List[str]],
    mapping: Dict[str, Optional[str]],
    exists: Lookup,
) -> List[Dict[str, Any]]:
    """
    One result per data row: {line, values, errors}. `line` is the
    spreadsheet line (header = 1). `exists(kind, value)` answers against
    the site for kinds: customer, profile, item, serial, owner.
    """
    spec = SPECS[import_type]
    index = {field: headers.index(source) for field, source in mapping.items() if source}
    seen: Dict[str, int] = {}
    results = []
    for offset, row in enumerate(rows):
        line = offset + 2
        values: Dict[str, Any] = {}
        errors: List[str] = []
        for field, (label, required, kind, _aliases) in spec.items():
            raw = row[index[field]] if field in index else ""
            try:
                value = convert(kind, raw)
            except ValueError:
                errors.append(f"{label} : valeur invalide « {raw.strip()} »")
                continue
            if required and (value is None or value == ""):
                errors.append(f"{label} : obligatoire")
            values[field] = value
        if not errors:
            errors.extend(_business_errors(import_type, values, exists))
        key = _row_key(import_type, values)
        if key:
            if key in seen:
                errors.append(f"Doublon de la ligne {seen[key]}")
            else:
                seen[key] = line
        results.append({"line": line, "values": values, "errors": errors})
    return results


def _row_key(import_type: str, values: Dict[str, Any]) -> Optional[str]:
    field = {"Customers": "customer_name", "Equipment": "item_code", "Serial Numbers": "serial_no"}[import_type]
    value = values.get(field)
    return _norm(str(value)) if value else None


def _business_errors(import_type: str, values: Dict[str, Any], exists: Lookup) -> List[str]:
    if import_type == "Customers":
        return ["Un client porte déjà ce nom dans la société."] if exists("customer", values["customer_name"]) else []
    if import_type == "Equipment":
        errors = []
        if exists("profile", values["item_code"]):
            errors.append("Cet article est déjà dans le catalogue locatif de la société.")
        if values.get("daily_rate") is not None and values["daily_rate"] <= 0:
            errors.append("Tarif journalier : doit être supérieur à 0")
        return errors
    if import_type == "Serial Numbers":
        errors = []
        if not exists("profile", values["item_code"]):
            errors.append(f"{values['item_code']} n’est pas dans le catalogue locatif de la société.")
        if exists("serial", values["serial_no"]):
            errors.append("Ce numéro de série existe déjà.")
        if values.get("consignment_owner") and not exists("owner", values["consignment_owner"]):
            errors.append(f"Propriétaire « {values['consignment_owner']} » introuvable.")
        return errors
    return []


def summarize(results: List[Dict[str, Any]]) -> Dict[str, int]:
    errors = sum(1 for r in results if r["errors"])
    return {"total_rows": len(results), "valid_rows": len(results) - errors, "error_rows": errors}
