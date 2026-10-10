"""Modifier la structure par l'assistant, avec approbation du propriétaire (phase 14.2).

Deux actions seulement, volontairement étroites et annulables **sans perte de données** :
- `add_category` : ajoute une catégorie d'équipement à la liste du site (retirée à l'annulation seulement si aucune fiche ne l'utilise);
- `add_custom_field` : ajoute un champ (nom technique `cx_…`) à la fiche équipement, au client ou à la location; à l'annulation
  il est **supprimé s'il est encore vide partout, sinon masqué** (les données restent).

Propriétaire seulement (`Cortex System Manager` ou `System Manager`) : un changement de structure touche tout le site.
Jamais : modifier ou supprimer un champ existant, sections, espaces de travail. Voir ADR-011 et le handoff, phase 14.
"""

import re
import unicodedata
from typing import Any, Dict, List

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

from cortex_rental.services import sector_templates as st
from cortex_rental.services.ai.actions import ActionError, ActionSpec, Prepared, register
from cortex_rental.services.ai.records import CUSTOM_PREFIX, label_of

OWNER_MESSAGE = "Seul le propriétaire de la société peut modifier la structure."
STRUCTURE_TYPES = ("Cortex Rental Item Profile", "Customer", "Cortex Rental Transaction")
FIELD_TYPES = {
    "Data": "Texte court",
    "Small Text": "Texte long",
    "Int": "Nombre entier",
    "Float": "Nombre",
    "Currency": "Montant",
    "Check": "Case à cocher",
    "Date": "Date",
    "Select": "Liste de choix",
}
MAX_CUSTOM_PER_TYPE = 20
MAX_CATEGORY = 40
MAX_LABEL = 60
MAX_CHOICES = 20


# --- Pur ---------------------------------------------------------------------------------------------------------


def clean_category(value: Any) -> str:
    """Pur : le nom d'une catégorie (une ligne, espaces nettoyés, 2 à 40 caractères)."""
    text = " ".join(str(value or "").split())
    if len(text) < 2:
        raise ActionError("Le nom de la catégorie est obligatoire (2 caractères au moins).")
    if len(text) > MAX_CATEGORY:
        raise ActionError(f"Le nom de la catégorie est trop long ({MAX_CATEGORY} caractères au plus).")
    return text


def normalize_type(value: Any) -> str:
    """Pur : le type Frappe d'un champ à partir de son nom technique ou français (« Montant », « Currency »…)."""
    text = str(value or "").strip().lower()
    for code, french in FIELD_TYPES.items():
        if text in (code.lower(), french.lower()):
            return code
    raise ActionError("Type de champ permis : " + ", ".join(f"{f} ({c})" for c, f in FIELD_TYPES.items()) + ".")


def field_slug(label: str) -> str:
    """Pur : nom technique à partir du libellé (« Numéro de plaque » → « cx_numero_de_plaque »), 30 caractères au plus."""
    ascii_text = "".join(c for c in unicodedata.normalize("NFD", label.lower()) if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")[:24].strip("_")
    if not slug:
        raise ActionError("Le libellé du champ doit contenir des lettres ou des chiffres.")
    return f"{CUSTOM_PREFIX}{slug}"


def clean_choices(options: Any) -> List[str]:
    """Pur : les choix d'une liste (séparés par des virgules, points-virgules ou lignes), 2 à 20, sans doublon."""
    parts = [" ".join(p.split()) for p in re.split(r"[\n,;]", str(options or ""))]
    out: List[str] = []
    for part in parts:
        if part and part not in out:
            out.append(part)
    if len(out) < 2:
        raise ActionError("Une liste de choix demande au moins deux choix (séparés par des virgules).")
    if len(out) > MAX_CHOICES or any(len(c) > 40 for c in out):
        raise ActionError(f"Une liste de choix : {MAX_CHOICES} choix au plus, de 40 caractères au plus.")
    return out


# --- Catégorie d'équipement ----------------------------------------------------------------------------------------


def _prepare_category(args: Dict[str, Any], company: str) -> Prepared:
    st.require_owner(OWNER_MESSAGE)
    name = clean_category(args.get("category"))
    current = st.categories()
    if name.lower() in (c.lower() for c in current):
        raise ActionError(f"La catégorie « {name} » existe déjà.")
    rows = [
        {"label": "Nouvelle catégorie d'équipement", "value": name},
        {"label": "Catégories actuelles", "detail": ", ".join(frappe._(c) for c in current) or "(aucune)"},
    ]
    return Prepared(
        {"category": name},
        f"Ajouter la catégorie « {name} »",
        [f"Nouvelle catégorie : {name}", "Actuelles : " + ", ".join(current)],
        rows=rows,
        subtitle="La liste des catégories est celle du site (un site par client)",
        approve_label="Ajouter la catégorie",
    )


def _run_category(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    name = clean_category(payload["category"])
    current = st.categories()
    if name.lower() in (c.lower() for c in current):
        raise ActionError(f"La catégorie « {name} » existe déjà.")
    st._set_categories(current + [name])
    return {
        "id": name,
        "label": "Voir les modèles de secteur",
        "href": "/app/cortex-sector-templates",
        "undo": {"category": name},
    }


def _undo_category(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    name = info["category"]
    used = frappe.db.count(st.PROFILE, {"category": name})
    if used:
        raise ActionError(
            f"Impossible d'annuler : {used} fiche(s) d'équipement utilisent la catégorie « {name} ». Rien n'a été retiré."
        )
    current = st.categories()
    st._set_categories([c for c in current if c != name])
    return {
        "label": "Voir les modèles de secteur",
        "href": "/app/cortex-sector-templates",
        "message": f"Catégorie « {name} » retirée.",
    }


# --- Champ ajouté --------------------------------------------------------------------------------------------------


def _existing_custom(doctype: str) -> List[str]:
    names = frappe.get_all("Custom Field", filters={"dt": doctype, "fieldname": ["like", "cx_%"]}, pluck="fieldname")
    return [n for n in names if n.startswith(CUSTOM_PREFIX)]


def _prepare_field(args: Dict[str, Any], company: str) -> Prepared:
    st.require_owner(OWNER_MESSAGE)
    doctype = str(args.get("doctype") or "").strip()
    if doctype not in STRUCTURE_TYPES:
        raise ActionError(
            "On peut ajouter un champ à : " + ", ".join(f"{label_of(d)} ({d})" for d in STRUCTURE_TYPES) + "."
        )
    label = " ".join(str(args.get("label") or "").split())
    if len(label) < 2 or len(label) > MAX_LABEL:
        raise ActionError(f"Le libellé du champ est obligatoire (2 à {MAX_LABEL} caractères).")
    fieldtype = normalize_type(args.get("fieldtype"))
    options = ""
    if fieldtype == "Select":
        options = "\n".join(clean_choices(args.get("options")))
    fieldname = field_slug(label)
    meta = frappe.get_meta(doctype)
    if meta.has_field(fieldname) or any((f.label or "").strip().lower() == label.lower() for f in meta.fields):
        raise ActionError(f"Un champ « {label} » existe déjà sur cette fiche.")
    if len(_existing_custom(doctype)) >= MAX_CUSTOM_PER_TYPE:
        raise ActionError(f"Cette fiche a déjà {MAX_CUSTOM_PER_TYPE} champs ajoutés : c'est le maximum.")
    rows = [
        {"label": "Fiche", "value": label_of(doctype)},
        {"label": "Nouveau champ", "detail": f"Nom technique : {fieldname}", "value": label},
        {"label": "Type", "value": FIELD_TYPES[fieldtype]},
    ]
    lines = [f"Fiche : {doctype}", f"Champ : {label} ({fieldname}, {fieldtype})"]
    if options:
        rows.append({"label": "Choix", "detail": ", ".join(options.split("\n"))})
        lines.append("Choix : " + ", ".join(options.split("\n")))
    return Prepared(
        {"doctype": doctype, "label": label, "fieldname": fieldname, "fieldtype": fieldtype, "options": options},
        f"Ajouter le champ « {label} » à {label_of(doctype).lower()}",
        lines,
        rows=rows,
        subtitle="Le champ s'ajoute à la fin de la fiche; rien d'existant ne change",
        approve_label="Ajouter le champ",
    )


def _run_field(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    doctype, fieldname = payload["doctype"], payload["fieldname"]
    if doctype not in STRUCTURE_TYPES or not fieldname.startswith(CUSTOM_PREFIX):
        raise ActionError("Ce champ ne peut pas être ajouté.")
    if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
        raise ActionError("Ce champ existe déjà.")
    last = [f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldname][-1:]
    doc = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": doctype,
            "insert_after": last[0] if last else None,  # à la fin de la fiche, jamais en tête
            "fieldname": fieldname,
            "label": payload["label"],
            "fieldtype": payload["fieldtype"],
            "options": payload.get("options") or None,
        }
    )
    doc.insert(ignore_permissions=True)  # le rôle de propriétaire vient d'être vérifié ci-dessus
    frappe.clear_cache(doctype=doctype)
    return {
        "id": doc.name,
        "label": f"Ouvrir : {label_of(doctype).lower()}",
        "href": f"/app/{doctype.lower().replace(' ', '-')}",
        "undo": {"doctype": doctype, "fieldname": fieldname, "label": payload["label"]},
    }


def _has_data(doctype: str, fieldname: str) -> bool:
    return bool(
        frappe.db.sql(
            f"select 1 from `tab{doctype}` where ifnull(`{fieldname}`, '') not in ('', '0', '0.0', '0.00') limit 1"
        )
    )


def _undo_field(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    doctype, fieldname, label = info["doctype"], info["fieldname"], info["label"]
    if doctype not in STRUCTURE_TYPES or not fieldname.startswith(CUSTOM_PREFIX):
        raise ActionError("Ce champ ne peut pas être annulé ici.")
    name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname})
    href = f"/app/{doctype.lower().replace(' ', '-')}"
    if not name:
        return {"label": "Ouvrir la fiche", "href": href, "message": f"Le champ « {label} » n'existe plus."}
    if _has_data(doctype, fieldname):
        frappe.db.set_value("Custom Field", name, "hidden", 1)
        frappe.clear_cache(doctype=doctype)
        message = f"Champ « {label} » masqué : des fiches contiennent déjà une valeur, elles sont conservées."
    else:
        frappe.delete_doc("Custom Field", name, ignore_permissions=True)
        frappe.clear_cache(doctype=doctype)
        message = f"Champ « {label} » supprimé (il était vide partout)."
    return {"label": "Ouvrir la fiche", "href": href, "message": message}


def register_actions() -> None:
    register(
        ActionSpec(
            "add_category",
            "Ajouter une catégorie d'équipement",
            "",
            "write",
            _prepare_category,
            _run_category,
            effects=(
                "Ajoute une catégorie à la liste des catégories d'équipement du site (fiche, filtres, barre latérale).",
                "Ne change aucune fiche d'équipement existante.",
                "Pour revenir en arrière : « Annuler » retire la catégorie, sauf si une fiche l'utilise déjà.",
            ),
            undo=_undo_category,
            undo_label="Annuler la catégorie",
        )
    )
    register(
        ActionSpec(
            "add_custom_field",
            "Ajouter un champ",
            "",
            "write",
            _prepare_field,
            _run_field,
            effects=(
                "Ajoute un champ à la fin de la fiche choisie; les fiches existantes l'ont vide.",
                "Ne modifie ni ne supprime aucun champ existant.",
                "Pour revenir en arrière : « Annuler » supprime le champ s'il est vide partout, sinon le masque (les données sont gardées).",
                "Une fois ajouté, l'assistant pourra aussi proposer d'en modifier la valeur (avec avant/après).",
            ),
            undo=_undo_field,
            undo_label="Annuler le champ",
        )
    )


# S'enregistre à l'import, que `actions` ou ce module soit importé en premier (voir le bas de services/ai/actions.py).
register_actions()
