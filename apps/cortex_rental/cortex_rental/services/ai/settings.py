"""Réglages de la passerelle IA (un seul endroit : le modèle, la clé, les limites, le prix)."""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

DOCTYPE = "Cortex AI Settings"

# Valeurs par défaut : le modèle et les prix se changent dans les réglages, jamais dans le code.
DEFAULTS: Dict[str, Any] = {
    "enabled": 1,
    "model": "gemini-3.8-flash",
    "fallback_model": "",
    "temperature": 0.2,
    "max_output_tokens": 1024,
    "max_tool_steps": 5,
    "timeout_seconds": 60,
    "price_input_per_mtok": 0.0,
    "price_output_per_mtok": 0.0,
    "default_monthly_budget": 0.0,
    "default_monthly_token_cap": 0,
    "warn_percent": 80,
}


def load() -> Dict[str, Any]:
    """Réglages effectifs : valeurs des réglages du site, sinon valeurs par défaut ; la clé vient du coffre ou de la config."""
    values = dict(DEFAULTS)
    values["company_limits"] = {}
    values["api_key"] = ""
    if not frappe:
        return values
    if frappe.db.exists("DocType", DOCTYPE):
        doc = frappe.get_single(DOCTYPE)
        for key in DEFAULTS:
            value = doc.get(key)
            if value not in (None, ""):
                values[key] = value
        for row in doc.get("company_budgets") or []:
            values["company_limits"][row.company] = {
                "budget": float(row.monthly_budget or 0),
                "tokens": int(row.monthly_token_cap or 0),
            }
        try:
            from frappe.utils.password import get_decrypted_password

            values["api_key"] = get_decrypted_password(DOCTYPE, DOCTYPE, "api_key", raise_exception=False) or ""
        except Exception:
            values["api_key"] = ""
    if not values["api_key"]:
        values["api_key"] = (getattr(frappe, "conf", None) or {}).get("gemini_api_key") or ""
    return values
