"""Lecture et modification générique d'enregistrements pour l'assistant (phase 13).

Deux règles gardent cela sûr :
- **liste blanche** de types (lecture) et de champs (modification) : l'assistant ne touche jamais une table technique,
  un statut, un montant calculé ou un champ en lecture seule; ajouter un champ = une ligne ici, relue par une personne;
- la **société** de l'enregistrement doit être celle de la personne, et tout passe par les droits de Frappe
  (`get_list`, `has_permission`, `doc.save()` avec les validations de l'écran).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

from cortex_rental.services.ai.actions import ActionError, ActionSpec, Prepared, href_for, register
from cortex_rental.services.ai.stats import fr_number, money

SHORT_TEXT = 140
LONG_TEXT = 1000
MAX_FIND = 15
MAX_CHILD_ROWS = 30


@dataclass(frozen=True)
class Readable:
    label: str  # « Client »
    company_field: str
    search_fields: Tuple[str, ...]
    list_fields: Tuple[str, ...]


READABLE: Dict[str, Readable] = {
    "Customer": Readable("Client", "cortex_company", ("name", "customer_name"), ("name", "customer_name")),
    "Cortex Rental Item Profile": Readable(
        "Profil d'équipement",
        "company",
        ("name", "item_code", "item_name"),
        ("name", "item_code", "item_name", "category", "daily_rate", "total_quantity"),
    ),
    "Cortex Rental Transaction": Readable(
        "Location",
        "company",
        ("name", "customer", "project_name"),
        ("name", "customer", "project_name", "rental_state", "starts_at", "ends_at", "grand_total"),
    ),
    "Cortex Rental Invoice": Readable(
        "Facture",
        "company",
        ("name", "customer"),
        ("name", "customer", "status", "total", "balance", "due_date"),
    ),
    "Cortex Rental Payment": Readable(
        "Paiement",
        "company",
        ("name", "customer", "invoice"),
        ("name", "customer", "invoice", "method", "amount", "paid_on"),
    ),
    "Approval Request": Readable(
        "Demande d'approbation", "company", ("name", "action", "entity_id"), ("name", "action", "status", "entity_id")
    ),
    "Cortex Check-In": Readable(
        "Retour de matériel", "company", ("name", "transaction"), ("name", "transaction", "status", "checked_in_at")
    ),
    "Rental Pricing Rule": Readable(
        "Règle de prix",
        "company",
        ("name", "rule_name"),
        ("name", "rule_name", "is_active", "calendar_days", "billable_days", "multiplier"),
    ),
}

# Champs modifiables, type par type. Volontairement petite : on l'élargit à la demande, jamais « tout champ ».
EDITABLE: Dict[str, Dict[str, str]] = {
    "Cortex Rental Item Profile": {
        "item_name": "Nom affiché",
        "daily_rate": "Tarif journalier",
        "replacement_value": "Valeur de remplacement",
        "deposit_required": "Dépôt exigé",
        "prep_hours": "Heures de préparation",
        "required_accessories": "Accessoires requis",
        "is_consignment_allowed": "Consignation permise",
    },
    "Cortex Rental Transaction": {"notes": "Notes", "project_name": "Nom du projet"},
    "Customer": {"customer_details": "Notes sur le client", "website": "Site web"},
    "Rental Pricing Rule": {
        "is_active": "Règle active",
        "multiplier": "Multiplicateur",
        "billable_days": "Jours facturables",
        "description": "Description",
    },
}
# Une location ne se modifie par ce chemin que tant qu'elle n'est pas engagée (devis ou réservation).
EDITABLE_STATES = {"Cortex Rental Transaction": ("Quote", "Reservation")}

NUMERIC = ("Currency", "Float", "Int", "Percent")
TEXT = ("Data", "Small Text", "Text")
SUPPORTED = NUMERIC + TEXT + ("Check", "Select")
SKIP_TYPES = (
    "Table", "Table MultiSelect", "Password", "Attach", "Attach Image", "Code", "JSON", "HTML", "Image", "Signature",
    "Section Break", "Column Break", "Tab Break", "Button", "Heading", "HTML Editor", "Markdown Editor",
)  # fmt: skip


# --- Pur ---------------------------------------------------------------------------------------------------------


def company_field_of(doctype: str) -> str:
    spec = READABLE.get(doctype)
    return spec.company_field if spec else "company"


def label_of(doctype: str) -> str:
    spec = READABLE.get(doctype)
    return spec.label if spec else doctype


def coerce_value(fieldtype: str, value: Any, label: str, options: str = "") -> Any:
    """Pur : la valeur propre pour ce type de champ, ou un refus clair en français (jamais une valeur devinée)."""
    if fieldtype not in SUPPORTED:
        raise ActionError(f"Le champ « {label} » ne peut pas être modifié par l'assistant.")
    if fieldtype == "Check":
        if isinstance(value, bool):
            return int(value)
        text = str(value).strip().lower()
        if text in ("1", "true", "oui", "vrai", "yes"):
            return 1
        if text in ("0", "false", "non", "faux", "no"):
            return 0
        raise ActionError(f"« {label} » est une case à cocher : indiquez oui ou non.")
    if fieldtype in NUMERIC:
        if isinstance(value, bool) or value is None or str(value).strip() == "":
            raise ActionError(f"« {label} » doit être un nombre.")
        try:
            number = float(str(value).replace(" ", "").replace(" ", "").replace(",", "."))
        except ValueError:
            raise ActionError(f"« {label} » doit être un nombre.")
        if number != number or number in (float("inf"), float("-inf")):
            raise ActionError(f"« {label} » doit être un nombre.")
        if number < 0:
            raise ActionError(f"« {label} » ne peut pas être négatif.")
        if fieldtype == "Int":
            if number != int(number):
                raise ActionError(f"« {label} » doit être un nombre entier.")
            return int(number)
        if fieldtype == "Percent" and number > 100:
            raise ActionError(f"« {label} » ne peut pas dépasser 100.")
        return round(number, 6)
    text = (
        " ".join(str(value if value is not None else "").split()) if fieldtype == "Data" else str(value or "").strip()
    )
    limit = SHORT_TEXT if fieldtype == "Data" else LONG_TEXT
    if len(text) > limit:
        raise ActionError(f"« {label} » est trop long ({limit} caractères au plus).")
    if fieldtype == "Select":
        choices = [o.strip() for o in str(options or "").split("\n") if o.strip()]
        if text not in choices:
            raise ActionError(f"« {label} » doit être l'une de ces valeurs : {', '.join(choices)}.")
    return text


def same_value(fieldtype: str, a: Any, b: Any) -> bool:
    """Pur : deux valeurs sont-elles les mêmes pour ce type (les nombres se comparent à 6 décimales, le vide = vide)?"""
    if fieldtype in NUMERIC or fieldtype == "Check":
        try:
            return round(float(a or 0), 6) == round(float(b or 0), 6)
        except (TypeError, ValueError):
            return False
    return str(a if a is not None else "").strip() == str(b if b is not None else "").strip()


def storable(fieldtype: str, value: Any) -> Any:
    """Pur : la valeur sous une forme que JSON garde sans perte (nombres en nombres, le reste en texte)."""
    if fieldtype == "Check":
        return int(bool(value))
    if fieldtype in NUMERIC:
        return round(float(value or 0), 6)
    return str(value if value is not None else "")


def display_value(fieldtype: str, value: Any) -> str:
    """Pur : la valeur telle qu'on la lit à l'écran (« 150,00 $ », « Oui », « (vide) »)."""
    if fieldtype == "Check":
        return "Oui" if value else "Non"
    if fieldtype == "Currency":
        return money(value or 0)
    if fieldtype in NUMERIC:
        return fr_number(value or 0)
    text = str(value if value is not None else "").strip()
    return text if text else "(vide)"


# --- Lecture -----------------------------------------------------------------------------------------------------


def _readable(doctype: str) -> Readable:
    spec = READABLE.get(doctype)
    if not spec:
        raise ActionError(
            f"Ce type n'est pas consultable par l'assistant. Types permis : {', '.join(sorted(READABLE))}."
        )
    if not frappe.has_permission(doctype, "read"):
        raise ActionError(f"Votre rôle ne permet pas de consulter ce type ({spec.label.lower()}).")
    return spec


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


def find(doctype: str, query: str, company: str, limit: int = 10) -> Dict[str, Any]:
    """Cherche dans un type permis, limité à la société de la personne et à ses droits."""
    spec = _readable(doctype)
    text = str(query or "").strip()
    meta = frappe.get_meta(doctype)
    fields = [f for f in spec.list_fields if f == "name" or meta.has_field(f)]
    search = [f for f in spec.search_fields if f == "name" or meta.has_field(f)]
    rows = frappe.get_list(
        doctype,
        filters={spec.company_field: company},
        or_filters=[[f, "like", f"%{text}%"] for f in search] if text else None,
        fields=fields,
        order_by="modified desc",
        limit_page_length=max(1, min(int(limit or 10), MAX_FIND)),
    )
    return {
        "type": spec.label,
        "doctype": doctype,
        "records": [{**{k: _plain(v) for k, v in dict(r).items()}, "href": href_for(doctype, r["name"])} for r in rows],
    }


def get(doctype: str, name: str, company: str) -> Dict[str, Any]:
    """Détail d'un enregistrement : champs simples seulement (jamais mot de passe, pièce jointe ni code)."""
    spec = _readable(doctype)
    if not frappe.db.exists(doctype, {"name": str(name or ""), spec.company_field: company}):
        raise ActionError("Cet enregistrement n'existe pas dans votre société.")
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, "read", doc=doc):
        raise ActionError("Votre rôle ne permet pas de consulter cet enregistrement.")
    meta = frappe.get_meta(doctype)
    fields: Dict[str, Any] = {}
    labels: Dict[str, str] = {}
    children: Dict[str, List[Dict[str, Any]]] = {}
    for df in meta.fields:
        if df.fieldtype in ("Table", "Table MultiSelect"):
            keep = [c for c in frappe.get_meta(df.options).fields if c.fieldtype not in SKIP_TYPES]
            rows = [
                {c.fieldname: _plain(row.get(c.fieldname)) for c in keep if row.get(c.fieldname) not in (None, "")}
                for row in (doc.get(df.fieldname) or [])[:MAX_CHILD_ROWS]
            ]
            if rows:
                children[df.fieldname] = rows
        elif df.fieldtype not in SKIP_TYPES and doc.get(df.fieldname) not in (None, ""):
            fields[df.fieldname] = _plain(doc.get(df.fieldname))
            labels[df.fieldname] = frappe._(df.label or df.fieldname)
    return {
        "type": spec.label,
        "doctype": doctype,
        "name": doc.name,
        "fields": fields,  # nom technique → valeur
        "labels": labels,  # nom technique → libellé affiché
        "tables": children,
        "editable_fields": sorted(EDITABLE.get(doctype, {})),
        "href": href_for(doctype, doc.name),
    }


# --- Modifier un champ -------------------------------------------------------------------------------------------


def _editable_doc(doctype: str, name: str, company: str):
    if doctype not in EDITABLE:
        raise ActionError(
            "Ce type n'est pas modifiable par l'assistant. Types permis : "
            + ", ".join(label_of(d) for d in EDITABLE)
            + "."
        )
    cfield = company_field_of(doctype) if doctype in READABLE else "company"
    if not name or not frappe.db.exists(doctype, {"name": name, cfield: company}):
        raise ActionError("Cet enregistrement n'existe pas dans votre société.")
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, "write", doc=doc):
        raise ActionError(f"Votre rôle ne permet pas de modifier cet enregistrement ({label_of(doctype).lower()}).")
    states = EDITABLE_STATES.get(doctype)
    if states and doc.get("rental_state") not in states:
        raise ActionError("Cette location est déjà engagée : elle ne se modifie plus par l'assistant.")
    return doc


def _field(doctype: str, fieldname: str):
    allowed = EDITABLE.get(doctype, {})
    if fieldname not in allowed:
        raise ActionError(
            f"Ce champ n'est pas modifiable par l'assistant. Champs permis pour {label_of(doctype).lower()} : "
            + ", ".join(f"{label} ({code})" for code, label in allowed.items())
            + "."
        )
    df = frappe.get_meta(doctype).get_field(fieldname)
    if not df or df.read_only or df.fieldtype not in SUPPORTED:
        raise ActionError(f"Le champ « {allowed[fieldname]} » ne peut pas être modifié par l'assistant.")
    return df


def _prepare_update(args: Dict[str, Any], company: str) -> Prepared:
    doctype = str(args.get("doctype") or "").strip()
    name = str(args.get("name") or "").strip()
    fieldname = str(args.get("fieldname") or "").strip()
    doc = _editable_doc(doctype, name, company)
    df = _field(doctype, fieldname)
    label = EDITABLE[doctype][fieldname]
    if "value" not in args:
        raise ActionError("La nouvelle valeur est obligatoire.")
    after = coerce_value(df.fieldtype, args.get("value"), label, df.options or "")
    before = doc.get(fieldname)
    if same_value(df.fieldtype, before, after):
        raise ActionError(f"« {label} » a déjà cette valeur ({display_value(df.fieldtype, before)}). Rien à modifier.")
    shown_before, shown_after = display_value(df.fieldtype, before), display_value(df.fieldtype, after)
    what = f"{label_of(doctype)} {doc.name}"
    rows = [
        {"label": what},
        {"label": label, "detail": f"Avant : {shown_before}", "value": f"Après : {shown_after}"},
    ]
    return Prepared(
        {
            "doctype": doctype,
            "name": doc.name,
            "fieldname": fieldname,
            "value": after,
            "before": storable(df.fieldtype, before),
        },
        f"Modifier « {label} » de {what}",
        [f"{what} · {label} : avant {shown_before}, après {shown_after}"],
        rows=rows,
        subtitle="Une seule valeur change; vous pourrez annuler après coup",
        approve_label="Appliquer la modification",
    )


def _write_field(
    doctype: str, name: str, fieldname: str, value: Any, expect: Any, company: str, changed_message: str
) -> Dict[str, Any]:
    """Écrit la valeur par `doc.save()` (mêmes validations que l'écran) si, sous verrou, la valeur actuelle est `expect`."""
    doc = _editable_doc(doctype, name, company)
    df = _field(doctype, fieldname)
    frappe.db.get_value(doctype, name, "modified", for_update=True)
    doc.reload()
    if not same_value(df.fieldtype, doc.get(fieldname), expect):
        raise ActionError(changed_message.format(now=display_value(df.fieldtype, doc.get(fieldname))))
    doc.set(fieldname, value)
    doc.save()
    return {"id": doc.name, "label": f"Ouvrir : {label_of(doctype).lower()}", "href": href_for(doctype, doc.name)}


def _run_update(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    doctype, name, fieldname = payload["doctype"], payload["name"], payload["fieldname"]
    result = _write_field(
        doctype,
        name,
        fieldname,
        payload["value"],
        payload.get("before"),
        company,
        "La valeur a changé entre-temps (maintenant : {now}). Rien n'a été écrit.",
    )
    result["undo"] = {
        "doctype": doctype,
        "name": name,
        "fieldname": fieldname,
        "before": payload.get("before"),
        "after": payload["value"],
    }
    return result


def _undo_update(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    """Remet l'ancienne valeur, seulement si la valeur actuelle est encore celle que l'assistant a écrite."""
    return _write_field(
        info["doctype"],
        info["name"],
        info["fieldname"],
        info.get("before"),
        info.get("after"),
        company,
        "Impossible d'annuler : la valeur a été modifiée depuis (maintenant : {now}). Rien n'a été défait.",
    )


register(
    ActionSpec(
        "update_field",
        "Modifier un champ",
        "",  # pas de droit global : le droit d'écriture est vérifié sur l'enregistrement lui-même
        "write",
        _prepare_update,
        _run_update,
        effects=(
            "Change une seule valeur sur l'enregistrement indiqué, avec vos droits et les validations habituelles.",
            "Les documents déjà créés (devis, factures) ne sont pas recalculés.",
            "Pour revenir en arrière : le bouton « Annuler cette modification » de la carte remet l'ancienne valeur, tant que personne ne l'a changée entre-temps.",
        ),
        undo=_undo_update,
    )
)
