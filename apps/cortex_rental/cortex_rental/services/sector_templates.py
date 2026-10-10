"""Modèles de secteur : un point de départ complet (catégories, règles de prix, réglages) pour un domaine de location.

Déterministe : tout est écrit ici, relu par une personne; aucun modèle d'IA n'est appelé et aucun jeton n'est consommé.
Appliquer un modèle passe par le moteur d'actions (aperçu → approbation → exécution → annulation, services/ai/actions.py).

Règles :
- appliquer **ajoute** (catégories, règles manquantes) ou **change** un réglage seulement quand il diffère; rien n'est retiré;
- jamais de taxes, de comptes comptables ni de textes juridiques;
- la liste des catégories est propre au **site** (un site par client) : une *Property Setter* sur la fiche équipement.
"""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

PROFILE = "Cortex Rental Item Profile"
RULE = "Rental Pricing Rule"
SETTINGS = "Cortex Finance Settings"
OWNER_ROLES = ("Cortex System Manager", "System Manager")

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "cinema_video": {
        "label": "Cinéma et vidéo",
        "description": "Location de caméras, optiques, éclairage, grip, audio, moniteurs et alimentation pour le tournage.",
        # Les valeurs techniques sont celles qui existent déjà : aucune donnée ne change de catégorie.
        "categories": [
            "Camera Bodies",
            "Cinema Lenses",
            "Lighting",
            "Grip & Rigging",
            "Audio",
            "Monitors & Wireless Video",
            "Power & Batteries",
        ],
        "pricing_rules": [
            {
                "rule_name": "7 jours pour 3",
                "calendar_days": 7,
                "billable_days": 3.0,
                "is_active": 1,
                "description": "Une semaine de location est facturée 3 jours (règle canonique du produit).",
            },
            {
                "rule_name": "Fin de semaine : 3 jours pour 1",
                "calendar_days": 3,
                "billable_days": 1.0,
                "is_active": 0,
                "description": "Suggestion : un week-end facturé 1 jour. Créée inactive : activez-la si elle vous convient.",
            },
        ],
        "settings": {
            "deposit_percent": 30,
            "invoice_due_days": 0,
            "quote_hold_enabled": 1,
            "quote_hold_hours": 72,
            "late_fee_enabled": 1,
            "late_fee_grace_minutes": 60,
            "late_fee_percent": 100,
            "damage_billing_enabled": 1,
            "missing_billing_percent": 100,
        },
    },
}


# --- Pur ---------------------------------------------------------------------------------------------------------


def parse_options(options: Any) -> List[str]:
    """Pur : les choix d'une liste Frappe (une valeur par ligne), sans lignes vides ni doublons, dans l'ordre."""
    seen, out = set(), []
    for line in str(options or "").split("\n"):
        value = line.strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def merge_categories(current: List[str], wanted: List[str]) -> List[str]:
    """Pur : les catégories à ajouter (celles de `wanted` absentes de `current`), dans l'ordre du modèle."""
    have = set(current)
    return [c for c in wanted if c not in have]


def without_categories(current: List[str], remove: List[str], used: List[str]) -> List[str]:
    """Pur : `current` sans les catégories de `remove`, sauf celles qu'une fiche utilise encore (jamais retirées)."""
    keep_anyway = set(used)
    gone = {c for c in remove if c not in keep_anyway}
    return [c for c in current if c not in gone]


def template(key: str) -> Dict[str, Any]:
    spec = TEMPLATES.get(str(key or "").strip())
    if not spec:
        raise ValueError("Ce modèle de secteur n'existe pas. Modèles : " + ", ".join(sorted(TEMPLATES)) + ".")
    return spec


def catalog() -> List[Dict[str, Any]]:
    """Pur : la liste des modèles pour la page (clé, nom, description, ce qu'ils contiennent)."""
    return [
        {
            "key": key,
            "label": spec["label"],
            "description": spec["description"],
            "categories": len(spec["categories"]),
            "pricing_rules": len(spec["pricing_rules"]),
            "settings": len(spec["settings"]),
        }
        for key, spec in sorted(TEMPLATES.items())
    ]


# --- Lecture de l'état du site -------------------------------------------------------------------------------------


def categories() -> List[str]:
    """Les catégories d'équipement du site (celles que Frappe accepte dans la fiche équipement)."""
    df = frappe.get_meta(PROFILE).get_field("category")
    return parse_options(df.options if df else "")


def _set_categories(values: List[str]) -> None:
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    make_property_setter(PROFILE, "category", "options", "\n".join(values), "Text", validate_fields_for_doctype=False)
    frappe.clear_cache(doctype=PROFILE)


def _used_categories() -> List[str]:
    return [
        r[0] for r in frappe.db.sql(f"select distinct category from `tab{PROFILE}` where ifnull(category,'') != ''")
    ]


def _settings_doc(company: str):
    if frappe.db.exists(SETTINGS, company):
        return frappe.get_doc(SETTINGS, company)
    return frappe.get_doc(
        {"doctype": SETTINGS, "company": company}
    )  # valeurs par défaut de la fiche, pas encore enregistrée


def require_owner() -> None:
    from cortex_rental.services.ai.actions import ActionError

    if not set(OWNER_ROLES) & set(frappe.get_roles()):
        raise ActionError("Seul le propriétaire de la société peut appliquer un modèle de secteur.")


def require_owner_or_throw() -> None:
    """Pour les points d'accès : même contrôle, mais en erreur Frappe lisible."""
    from cortex_rental.services.ai.actions import ActionError

    try:
        require_owner()
    except ActionError as exc:
        frappe.throw(str(exc), frappe.PermissionError)


def plan(key: str, company: str) -> Dict[str, Any]:
    """Ce qu'appliquer le modèle ferait sur ce site, sans rien écrire : ajouts (catégories, règles) et changements (réglages)."""
    from cortex_rental.services.ai import records

    spec = template(key)
    add_categories = merge_categories(categories(), spec["categories"])
    existing_rules = set(frappe.get_all(RULE, filters={"company": company}, pluck="rule_name"))
    rules = [r for r in spec["pricing_rules"] if r["rule_name"] not in existing_rules]
    doc = _settings_doc(company)
    meta = frappe.get_meta(SETTINGS)
    changes = []
    for fieldname, after in spec["settings"].items():
        df = meta.get_field(fieldname)
        before = doc.get(fieldname)
        if not records.same_value(df.fieldtype, before, after):
            changes.append(
                {
                    "fieldname": fieldname,
                    "label": records.EDITABLE[SETTINGS][fieldname],
                    "fieldtype": df.fieldtype,
                    "before": records.storable(df.fieldtype, before),
                    "after": records.storable(df.fieldtype, after),
                }
            )
    return {"template": key, "categories": add_categories, "rules": rules, "settings": changes}


# --- Action « appliquer un modèle » ----------------------------------------------------------------------------------


def _prepare(args: Dict[str, Any], company: str):
    from cortex_rental.services.ai.actions import ActionError, Prepared
    from cortex_rental.services.ai.records import display_value

    require_owner()
    try:
        spec = template(args.get("template"))
    except ValueError as exc:
        raise ActionError(str(exc))
    key = str(args.get("template")).strip()
    found = plan(key, company)
    if not (found["categories"] or found["rules"] or found["settings"]):
        raise ActionError(f"Le modèle « {spec['label']} » est déjà appliqué : rien à ajouter ni à changer.")
    rows, lines = [], []
    if found["categories"]:
        rows.append({"label": "Catégories d'équipement à ajouter", "detail": ", ".join(found["categories"])})
        lines.append("Catégories : " + ", ".join(found["categories"]))
    for rule in found["rules"]:
        state = "active" if rule["is_active"] else "inactive (à activer par vous)"
        rows.append(
            {
                "label": f"Règle de prix « {rule['rule_name']} »",
                "detail": f"{rule['calendar_days']} jours du calendrier facturés {rule['billable_days']:g} · {state}",
            }
        )
        lines.append(f"Règle : {rule['rule_name']} ({rule['calendar_days']}→{rule['billable_days']:g}, {state})")
    for change in found["settings"]:
        shown_before = display_value(change["fieldtype"], change["before"])
        shown_after = display_value(change["fieldtype"], change["after"])
        rows.append({"label": change["label"], "detail": f"Avant : {shown_before}", "value": f"Après : {shown_after}"})
        lines.append(f"Réglage {change['fieldname']} : {shown_before} → {shown_after}")
    return Prepared(
        {"template": key},
        f"Appliquer le modèle « {spec['label']} »",
        lines,
        rows=rows,
        subtitle="Ajoute ce qui manque et ne retire rien; vous pourrez annuler après coup",
        approve_label="Appliquer le modèle",
    )


def _run(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    require_owner()
    found = plan(payload["template"], company)
    before_options = categories()
    if found["categories"]:
        _set_categories(before_options + found["categories"])
    created = []
    for rule in found["rules"]:
        doc = frappe.get_doc({"doctype": RULE, "company": company, **rule})
        doc.insert(ignore_permissions=True)  # le rôle de propriétaire vient d'être vérifié ci-dessus
        created.append(doc.name)
    if found["settings"]:
        doc = _settings_doc(company)
        for change in found["settings"]:
            doc.set(change["fieldname"], change["after"])
        doc.flags.ignore_permissions = True
        doc.save()
    return {
        "id": payload["template"],
        "label": "Voir les règles de prix",
        "href": "/app/rental-pricing-rule",
        "undo": {
            "template": payload["template"],
            "categories": found["categories"],
            "rules": created,
            "settings": [
                {k: c[k] for k in ("fieldname", "fieldtype", "before", "after", "label")} for c in found["settings"]
            ],
        },
    }


def _undo(info: Dict[str, Any], company: str) -> Dict[str, Any]:
    from cortex_rental.services.ai import records

    require_owner()
    done, kept = [], []
    if info.get("categories"):
        used = _used_categories()
        current = categories()
        remaining = without_categories(current, info["categories"], used)
        if remaining != current:
            _set_categories(remaining)
        removed = [c for c in current if c not in remaining]
        stayed = [c for c in info["categories"] if c in used]
        if removed:
            done.append(f"catégories retirées : {', '.join(removed)}")
        if stayed:
            kept.append(f"catégories gardées parce qu'une fiche les utilise : {', '.join(stayed)}")
    for name in info.get("rules") or []:
        if frappe.db.exists(RULE, {"name": name, "company": company}):
            label = frappe.db.get_value(RULE, name, "rule_name") or name
            frappe.delete_doc(RULE, name, ignore_permissions=True)
            done.append(f"règle retirée : {label}")
    if info.get("settings"):
        doc = _settings_doc(company)
        restored = []
        for change in info["settings"]:
            if records.same_value(change["fieldtype"], doc.get(change["fieldname"]), change["after"]):
                doc.set(change["fieldname"], change["before"])
                restored.append(change["label"])
            else:
                kept.append(f"réglage gardé (modifié depuis) : {change['label']}")
        if restored:
            doc.flags.ignore_permissions = True
            doc.save()
            done.append(f"réglages remis : {', '.join(restored)}")
    message = "Modèle annulé" + (" — " + " ; ".join(done) if done else "") + "."
    if kept:
        message += " Laissé en place : " + " ; ".join(kept) + "."
    return {"label": "Voir les règles de prix", "href": "/app/rental-pricing-rule", "message": message}


def register_action() -> None:
    from cortex_rental.services.ai.actions import ActionSpec, register

    register(
        ActionSpec(
            "apply_sector_template",
            "Appliquer un modèle de secteur",
            "",  # pas de droit global : le rôle de propriétaire est vérifié dans l'action
            "write",
            _prepare,
            _run,
            effects=(
                "Ajoute les catégories d'équipement et les règles de prix qui manquent et change les réglages listés (avant → après).",
                "Ne retire rien, ne touche ni aux taxes, ni aux comptes, ni aux équipements ou aux documents existants.",
                "La liste des catégories est celle du site (un site par client).",
                "Pour revenir en arrière : « Annuler » sur la carte retire ce qui a été ajouté (sauf une catégorie encore utilisée) et remet les réglages qui n'ont pas changé depuis.",
            ),
            undo=_undo,
            undo_label="Annuler ce modèle",
        )
    )
