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
from typing import Any, Dict, List, Optional

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


SECTION_PREFIX = f"{CUSTOM_PREFIX}sec_"
MAX_SHORTCUTS = 12
SHORTCUT_TYPES = {"DocType": "Liste d'un type", "Report": "Rapport", "Page": "Page"}
WORKSPACE_PREFIX = "Cortex "


def section_slug(label: str) -> str:
    """Pur : nom technique d'une section (« Numéros d'assurance » → « cx_sec_numeros_d_assurance »)."""
    return SECTION_PREFIX + field_slug(label)[len(CUSTOM_PREFIX) :]


def normalize_shortcut_type(value: Any) -> str:
    """Pur : « DocType », « Report » ou « Page » (ou leur nom français)."""
    text = str(value or "").strip().lower()
    for code, french in SHORTCUT_TYPES.items():
        if text in (code.lower(), french.lower()):
            return code
    raise ActionError("Type de raccourci permis : " + ", ".join(f"{f} ({c})" for c, f in SHORTCUT_TYPES.items()) + ".")


def clean_shortcut_label(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if len(text) < 2 or len(text) > 40:
        raise ActionError("Le nom du raccourci est obligatoire (2 à 40 caractères).")
    return text


def section_end(fields: List[Dict[str, Any]], section_fieldname: str) -> Optional[str]:
    """Pur : le dernier champ de la section (celui après lequel on insère), la section elle-même si elle est vide, None si absente.

    `fields` est la liste ordonnée de la fiche : [{"fieldname", "fieldtype"}…]. Une section se termine au prochain saut de
    section ou d'onglet."""
    names = [f["fieldname"] for f in fields]
    if section_fieldname not in names:
        return None
    last = section_fieldname
    for f in fields[names.index(section_fieldname) + 1 :]:
        if f["fieldtype"] in ("Section Break", "Tab Break"):
            break
        if f["fieldname"]:
            last = f["fieldname"]
    return last


def fields_after_section(fields: List[Dict[str, Any]], section_fieldname: str) -> List[str]:
    """Pur : les champs (hors sauts de colonne) que contient la section, dans l'ordre."""
    names = [f["fieldname"] for f in fields]
    if section_fieldname not in names:
        return []
    out = []
    for f in fields[names.index(section_fieldname) + 1 :]:
        if f["fieldtype"] in ("Section Break", "Tab Break"):
            break
        if f["fieldtype"] != "Column Break" and f["fieldname"]:
            out.append(f["fieldname"])
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
    section = " ".join(str(args.get("section") or "").split())
    if section:
        _section_fieldname(doctype, section)  # refuse tout de suite une section inconnue (et liste celles qui existent)
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
    if section:
        rows.insert(1, {"label": "Section", "value": section})
        lines.append(f"Section : {section}")
    if options:
        rows.append({"label": "Choix", "detail": ", ".join(options.split("\n"))})
        lines.append("Choix : " + ", ".join(options.split("\n")))
    return Prepared(
        {
            "doctype": doctype,
            "label": label,
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "options": options,
            "section": section,
        },
        f"Ajouter le champ « {label} » à {label_of(doctype).lower()}",
        lines,
        rows=rows,
        subtitle=(
            f"Le champ s'ajoute dans la section « {section} »; rien d'existant ne change"
            if section
            else "Le champ s'ajoute à la fin de la fiche; rien d'existant ne change"
        ),
        approve_label="Ajouter le champ",
    )


def _run_field(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    doctype, fieldname = payload["doctype"], payload["fieldname"]
    if doctype not in STRUCTURE_TYPES or not fieldname.startswith(CUSTOM_PREFIX):
        raise ActionError("Ce champ ne peut pas être ajouté.")
    if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
        raise ActionError("Ce champ existe déjà.")
    if payload.get("section"):
        anchor = section_end(_ordered_fields(doctype), _section_fieldname(doctype, payload["section"]))
    else:
        last = [f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldname][-1:]
        anchor = last[0] if last else None
    doc = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": doctype,
            "insert_after": anchor,  # dans la section demandée, sinon à la fin de la fiche : jamais en tête
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


# --- Sections -----------------------------------------------------------------------------------------------------


def _ordered_fields(doctype: str) -> List[Dict[str, Any]]:
    return [
        {"fieldname": f.fieldname, "fieldtype": f.fieldtype, "label": f.label} for f in frappe.get_meta(doctype).fields
    ]


def _section_fieldname(doctype: str, label: str) -> str:
    """Le nom technique de la section ajoutée (cx_sec_…) de ce titre sur cette fiche, sinon un refus qui liste celles qui existent."""
    found = frappe.get_all(
        "Custom Field",
        filters={"dt": doctype, "fieldtype": "Section Break", "hidden": 0},
        fields=["fieldname", "label"],
    )
    mine = [r for r in found if r.fieldname.startswith(SECTION_PREFIX)]
    for r in mine:
        if (r.label or "").strip().lower() == label.strip().lower():
            return r.fieldname
    names = ", ".join(f"« {r.label} »" for r in mine) or "aucune"
    raise ActionError(f"Section « {label} » introuvable sur cette fiche. Sections ajoutées : {names}.")


def _prepare_section(args: Dict[str, Any], company: str) -> Prepared:
    st.require_owner(OWNER_MESSAGE)
    doctype = str(args.get("doctype") or "").strip()
    if doctype not in STRUCTURE_TYPES:
        raise ActionError(
            "On peut ajouter une section à : " + ", ".join(f"{label_of(d)} ({d})" for d in STRUCTURE_TYPES) + "."
        )
    label = " ".join(str(args.get("label") or "").split())
    if len(label) < 2 or len(label) > MAX_LABEL:
        raise ActionError(f"Le titre de la section est obligatoire (2 à {MAX_LABEL} caractères).")
    fieldname = section_slug(label)
    meta = frappe.get_meta(doctype)
    if meta.has_field(fieldname) or any((f.label or "").strip().lower() == label.lower() for f in meta.fields):
        raise ActionError(f"Un champ ou une section « {label} » existe déjà sur cette fiche.")
    if len(_existing_custom(doctype)) >= MAX_CUSTOM_PER_TYPE:
        raise ActionError(f"Cette fiche a déjà {MAX_CUSTOM_PER_TYPE} éléments ajoutés : c'est le maximum.")
    rows = [
        {"label": "Fiche", "value": label_of(doctype)},
        {"label": "Nouvelle section", "detail": f"Nom technique : {fieldname}", "value": label},
    ]
    return Prepared(
        {"doctype": doctype, "label": label, "fieldname": fieldname},
        f"Ajouter la section « {label} » à {label_of(doctype).lower()}",
        [f"Fiche : {doctype}", f"Section : {label} ({fieldname})"],
        rows=rows,
        subtitle="La section s'ajoute à la fin de la fiche; vous pourrez y placer des champs",
        approve_label="Ajouter la section",
    )


def _run_section(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    doctype, fieldname = payload["doctype"], payload["fieldname"]
    if doctype not in STRUCTURE_TYPES or not fieldname.startswith(SECTION_PREFIX):
        raise ActionError("Cette section ne peut pas être ajoutée.")
    if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
        raise ActionError("Cette section existe déjà.")
    last = [f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldname][-1:]
    doc = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": doctype,
            "insert_after": last[0] if last else None,
            "fieldname": fieldname,
            "label": payload["label"],
            "fieldtype": "Section Break",
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


def _undo_section(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    st.require_owner(OWNER_MESSAGE)
    doctype, fieldname, label = info["doctype"], info["fieldname"], info["label"]
    if doctype not in STRUCTURE_TYPES or not fieldname.startswith(SECTION_PREFIX):
        raise ActionError("Cette section ne peut pas être annulée ici.")
    name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": fieldname})
    href = f"/app/{doctype.lower().replace(' ', '-')}"
    if not name:
        return {"label": "Ouvrir la fiche", "href": href, "message": f"La section « {label} » n'existe plus."}
    inside = fields_after_section(_ordered_fields(doctype), fieldname)
    if inside:
        raise ActionError(
            f"Impossible d'annuler : la section « {label} » contient encore {len(inside)} champ(s) "
            f"({', '.join(inside[:4])}). Annulez ou retirez d'abord ces champs. Rien n'a été retiré."
        )
    frappe.delete_doc("Custom Field", name, ignore_permissions=True)
    frappe.clear_cache(doctype=doctype)
    return {"label": "Ouvrir la fiche", "href": href, "message": f"Section « {label} » retirée (elle était vide)."}


# --- Raccourci d'un espace de travail --------------------------------------------------------------------------------


def _workspace(name: str):
    name = str(name or "").strip()
    if not name.startswith(WORKSPACE_PREFIX) or not frappe.db.exists("Workspace", name):
        names = ", ".join(frappe.get_all("Workspace", filters={"name": ["like", f"{WORKSPACE_PREFIX}%"]}, pluck="name"))
        raise ActionError(f"Espace de travail inconnu. Espaces Cortex : {names or 'aucun'}.")
    return frappe.get_doc("Workspace", name)


def _check_target(link_type: str, link_to: str) -> None:
    if link_type == "DocType":
        ok = frappe.db.exists("DocType", link_to) and frappe.has_permission(link_to, "read")
    elif link_type == "Report":
        ok = frappe.db.exists("Report", link_to) and frappe.has_permission("Report", "read", doc=link_to)
    else:
        ok = frappe.db.exists("Page", link_to)
    if not ok:
        raise ActionError(f"« {link_to} » n'existe pas ou n'est pas accessible avec votre rôle.")


def _prepare_shortcut(args: Dict[str, Any], company: str) -> Prepared:
    st.require_owner(OWNER_MESSAGE)
    doc = _workspace(args.get("workspace"))
    label = clean_shortcut_label(args.get("label"))
    link_type = normalize_shortcut_type(args.get("link_type"))
    link_to = str(args.get("link_to") or "").strip()
    if not link_to:
        raise ActionError("La destination du raccourci est obligatoire.")
    _check_target(link_type, link_to)
    if any((r.label or "").strip().lower() == label.lower() for r in doc.shortcuts):
        raise ActionError(f"Un raccourci « {label} » existe déjà dans cet espace.")
    if len(doc.shortcuts) >= 40 or len(_added_shortcuts(doc)) >= MAX_SHORTCUTS:
        raise ActionError(f"Cet espace a déjà {MAX_SHORTCUTS} raccourcis ajoutés : c'est le maximum.")
    rows = [
        {"label": "Espace de travail", "value": doc.name},
        {"label": "Nouveau raccourci", "value": label},
        {"label": SHORTCUT_TYPES[link_type], "value": link_to},
    ]
    return Prepared(
        {"workspace": doc.name, "label": label, "link_type": link_type, "link_to": link_to},
        f"Ajouter le raccourci « {label} » à l'espace « {doc.name} »",
        [f"Espace : {doc.name}", f"Raccourci : {label} → {link_type} {link_to}"],
        rows=rows,
        subtitle="Le raccourci s'ajoute à la fin des raccourcis de l'espace; rien d'existant ne change",
        approve_label="Ajouter le raccourci",
    )


class _as_administrator:
    """Frappe réserve la modification d'un espace de travail public au rôle « Workspace Manager » (même avec
    `ignore_permissions`). Le rôle de propriétaire a déjà été vérifié par l'action : on écrit le temps d'une sauvegarde au nom
    de l'administrateur, puis on rend la session à la personne (même exception bornée que pour les autres changements de
    structure; l'enregistrement de l'action garde la vraie personne)."""

    def __enter__(self):
        self.user = frappe.session.user
        # Sur un banc de développement, Frappe réécrit aussi le fichier JSON de l'espace dans le code de l'application
        # (dans un dossier au nom du titre, qui n'est pas celui du dépôt) : on l'évite pour cette sauvegarde seulement.
        self.dev = frappe.conf.get("developer_mode")
        frappe.conf.developer_mode = 0
        frappe.set_user("Administrator")

    def __exit__(self, *exc):
        frappe.set_user(self.user)
        frappe.conf.developer_mode = self.dev
        return False


def _content_blocks(doc) -> List[Dict[str, Any]]:
    import json

    try:
        blocks = json.loads(doc.content or "[]")
    except ValueError:
        return []
    return blocks if isinstance(blocks, list) else []


def _added_shortcuts(doc) -> List[str]:
    """Les raccourcis ajoutés par l'assistant : leur bloc porte un identifiant préfixé « cxs-»."""
    return [b["id"] for b in _content_blocks(doc) if str(b.get("id", "")).startswith("cxs-")]


def _run_shortcut(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    import json

    st.require_owner(OWNER_MESSAGE)
    doc = _workspace(payload["workspace"])
    label, link_type, link_to = payload["label"], payload["link_type"], payload["link_to"]
    _check_target(link_type, link_to)
    if any((r.label or "").strip().lower() == label.lower() for r in doc.shortcuts):
        raise ActionError(f"Un raccourci « {label} » existe déjà dans cet espace.")
    blocks = _content_blocks(doc)
    block_id = "cxs-" + frappe.generate_hash(length=8)
    added_header = False
    last_shortcut = max((i for i, b in enumerate(blocks) if b.get("type") == "shortcut"), default=None)
    block = {"id": block_id, "type": "shortcut", "data": {"shortcut_name": label, "col": 3}}
    if last_shortcut is None:
        header_id = "cxs-" + frappe.generate_hash(length=8)
        blocks += [
            {
                "id": header_id,
                "type": "header",
                "data": {"text": '<span class="h4"><b>Raccourcis</b></span>', "col": 12},
            },
            block,
        ]
        added_header = header_id
    else:
        blocks.insert(last_shortcut + 1, block)
    doc.append(
        "shortcuts",
        {"label": label, "type": link_type, "link_to": link_to, "doc_view": "List" if link_type == "DocType" else None},
    )
    doc.content = json.dumps(blocks, ensure_ascii=False)
    doc.flags.ignore_permissions = True  # le rôle de propriétaire vient d'être vérifié ci-dessus
    with _as_administrator():
        doc.save()
    return {
        "id": doc.name,
        "label": "Ouvrir l'espace",
        "href": f"/app/{doc.name.lower().replace(' ', '-')}",
        "undo": {"workspace": doc.name, "label": label, "block_id": block_id, "header_id": added_header or ""},
    }


def _undo_shortcut(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    import json

    st.require_owner(OWNER_MESSAGE)
    doc = _workspace(info["workspace"])
    label = info["label"]
    blocks = [
        b for b in _content_blocks(doc) if b.get("id") not in (info.get("block_id"), info.get("header_id") or "-")
    ]
    rows = [r for r in doc.shortcuts if (r.label or "").strip().lower() != label.lower()]
    removed = len(doc.shortcuts) - len(rows)
    doc.set("shortcuts", rows)
    doc.content = json.dumps(blocks, ensure_ascii=False)
    doc.flags.ignore_permissions = True
    with _as_administrator():
        doc.save()
    href = f"/app/{doc.name.lower().replace(' ', '-')}"
    message = f"Raccourci « {label} » retiré." if removed else f"Le raccourci « {label} » n'existait plus."
    return {"label": "Ouvrir l'espace", "href": href, "message": message}


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
    register(
        ActionSpec(
            "add_section",
            "Ajouter une section",
            "",
            "write",
            _prepare_section,
            _run_section,
            effects=(
                "Ajoute une section (un titre) à la fin de la fiche choisie; vous pourrez ensuite y placer des champs ajoutés.",
                "Ne modifie ni ne déplace aucun champ existant.",
                "Pour revenir en arrière : « Annuler » retire la section si elle est vide; sinon il faut d'abord annuler ses champs.",
            ),
            undo=_undo_section,
            undo_label="Annuler la section",
        )
    )
    register(
        ActionSpec(
            "add_workspace_shortcut",
            "Ajouter un raccourci",
            "",
            "write",
            _prepare_shortcut,
            _run_shortcut,
            effects=(
                "Ajoute un raccourci (liste d'un type, rapport ou page) aux raccourcis d'un espace de travail Cortex.",
                "Ne modifie aucun autre raccourci, graphique ni carte de l'espace.",
                "Le raccourci n'ouvre que ce que chaque personne a le droit de voir.",
                "Pour revenir en arrière : « Annuler » retire le raccourci.",
            ),
            undo=_undo_shortcut,
            undo_label="Annuler le raccourci",
        )
    )


# S'enregistre à l'import, que `actions` ou ce module soit importé en premier (voir le bas de services/ai/actions.py).
register_actions()
