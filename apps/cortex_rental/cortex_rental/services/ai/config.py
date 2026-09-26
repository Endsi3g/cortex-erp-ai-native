"""Which AI provider a company uses, and whether it can answer."""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.ai.anthropic_provider import DEFAULT_MODEL

PROVIDERS = ("Anthropic", "Onyx")


def ai_settings(company: str) -> Dict[str, Any]:
    """Provider and model per company (Cortex Company Settings); secrets stay in site_config."""
    provider, model = "Anthropic", DEFAULT_MODEL
    if frappe and frappe.db.exists("Cortex Company Settings", company):
        row = frappe.db.get_value("Cortex Company Settings", company, ["ai_provider", "ai_model"], as_dict=True) or {}
        provider = row.get("ai_provider") if row.get("ai_provider") in PROVIDERS else provider
        model = (row.get("ai_model") or "").strip() or model
    conf = frappe.conf if frappe else {}
    dev_mock = str(conf.get("cortex_chat_provider", "")).lower() == "mock" and bool(conf.get("developer_mode"))
    if dev_mock:
        return {"provider": "mock", "model": "Réponses simulées (développement)", "available": True}
    if provider == "Anthropic":
        return {"provider": "anthropic", "model": model, "available": bool(conf.get("anthropic_api_key"))}
    configured = bool(conf.get("onyx_base_url") and conf.get("onyx_api_key"))
    return {"provider": "onyx", "model": conf.get("onyx_model_name") if configured else None, "available": configured}
