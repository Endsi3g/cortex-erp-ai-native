"""Modèles de taxes canadiens par défaut, configurables par société et validés côté serveur.

Le modèle de données de Cortex porte deux taux (TPS fédérale et TVQ). Les modèles proposés sont donc ceux que ces deux
taux peuvent exprimer : Québec (TPS 5 % + TVQ 9,975 %), TPS seule, ou aucune taxe. Les provinces à taxe de vente
harmonisée (TVH) ou à taxe provinciale distincte ne sont **pas** couvertes : la société saisit alors ses taux à la main
(le serveur borne chacun entre 0 et 30 %). Taux à confirmer avec le comptable de la société avant usage réel.
"""

from typing import Any, Dict, Optional

try:
    import frappe
except ImportError:
    frappe = None

DOCTYPE = "Cortex Finance Settings"

PRESETS: Dict[str, Dict[str, Any]] = {
    "qc": {
        "label": "Québec : TPS 5 % + TVQ 9,975 %",
        "apply_taxes": 1,
        "tps_rate": 5.0,
        "tvq_rate": 9.975,
    },
    "tps": {
        "label": "TPS 5 % seulement (sans taxe de vente provinciale)",
        "apply_taxes": 1,
        "tps_rate": 5.0,
        "tvq_rate": 0.0,
    },
    "none": {
        "label": "Aucune taxe (société exonérée)",
        "apply_taxes": 0,
        "tps_rate": 0.0,
        "tvq_rate": 0.0,
    },
}
FIELDS = ("apply_taxes", "tps_rate", "tvq_rate")
MAX_RATE = 30.0


def _same(a: Any, b: Any) -> bool:
    return abs(float(a or 0) - float(b or 0)) < 1e-9


def matching_preset(values: Dict[str, Any]) -> str:
    """La clé du modèle qui correspond exactement aux réglages, sinon « custom » (taux saisis à la main)."""
    for key, preset in PRESETS.items():
        if all(_same(values.get(field), preset[field]) for field in FIELDS):
            return key
    return "custom"


def list_presets(company: str) -> Dict[str, Any]:
    current = {field: 0 for field in FIELDS}
    if frappe and frappe.db.exists(DOCTYPE, company):
        row = frappe.db.get_value(DOCTYPE, company, list(FIELDS), as_dict=True) or {}
        current = {field: row.get(field) or 0 for field in FIELDS}
    else:
        current = {"apply_taxes": 1, "tps_rate": 5.0, "tvq_rate": 9.975}  # défauts du DocType, jamais écrits ici
    return {
        "presets": [{"key": key, **preset} for key, preset in PRESETS.items()],
        "current": current,
        "matches": matching_preset(current),
        "limits": {"max_rate": MAX_RATE},
        "not_covered": "Les provinces à taxe de vente harmonisée (TVH) ou à taxe provinciale distincte : saisissez les taux à la main.",
    }


def apply_preset(company: str, key: str, user: Optional[str] = None) -> Dict[str, Any]:
    """Applique un modèle aux réglages financiers de la société (droit d'écriture requis, audité)."""
    if key not in PRESETS:
        frappe.throw("Ce modèle de taxes n'existe pas.", frappe.ValidationError)
    if not frappe.has_permission(DOCTYPE, "write"):
        frappe.throw("Votre rôle ne permet pas de modifier les réglages financiers.", frappe.PermissionError)
    preset = PRESETS[key]
    existing = frappe.db.exists(DOCTYPE, company)
    doc = frappe.get_doc(DOCTYPE, company) if existing else frappe.get_doc({"doctype": DOCTYPE, "company": company})
    before = {field: doc.get(field) for field in FIELDS}
    for field in FIELDS:
        doc.set(field, preset[field])
    doc.save() if existing else doc.insert()  # `validate` borne encore les taux
    from cortex_rental.services.audit import AuditService

    AuditService.record_mutation(
        company=company,
        action="cortex.finance.tax_preset_applied",
        entity_type=DOCTYPE,
        entity_id=company,
        before_state=before,
        after_state={**{field: preset[field] for field in FIELDS}, "preset": key},
    )
    return list_presets(company)
