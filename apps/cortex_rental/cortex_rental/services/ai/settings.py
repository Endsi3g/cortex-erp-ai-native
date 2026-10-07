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
    "price_input_per_mtok": 0.75,
    "price_output_per_mtok": 3.75,
    "default_monthly_budget": 60.0,
    "default_monthly_token_cap": 0,
    "warn_percent": 80,
    # Au plafond : modèle économique (Gemini 3.1 Flash-Lite, 0,25 $ / 1,50 $ par M de jetons) jusqu'à 150 % du budget.
    "economy_model": "gemini-3.1-flash-lite",
    "economy_price_input_per_mtok": 0.25,
    "economy_price_output_per_mtok": 1.50,
    "economy_cap_percent": 150,
    # Modèles Cortex : trois niveaux de puissance et de prix. Les identifiants et les prix se changent dans les réglages.
    "default_tier": "rapide",
    "tier_rapide_enabled": 1,
    "tier_equilibre_enabled": 1,
    "tier_equilibre_model": "claude-sonnet-5-5",
    "tier_equilibre_price_input": 2.0,
    "tier_equilibre_price_output": 10.0,
    "tier_avance_enabled": 1,
    "tier_avance_model": "claude-opus-5-5",
    "tier_avance_price_input": 4.0,
    "tier_avance_price_output": 20.0,
    # Luna (OpenAI GPT-6 Luna) : désactivé tant qu'une personne autorisée n'a pas saisi la clé OpenAI et activé le niveau.
    "tier_luna_enabled": 0,
    "tier_luna_model": "gpt-6-luna",
    "tier_luna_price_input": 0.1,
    "tier_luna_price_output": 0.5,
}

# Identifiants et prix vérifiés auprès des fournisseurs le 2026-10-07 (pages officielles Anthropic et OpenAI, fiche
# Gemini API). Un identifiant annoncé n'est pas une preuve de disponibilité : les prix sont à revérifier avant chaque
# changement de tarif (Gemini 3.8 Flash passe de 0,75 $ / 3,75 $ à 1,50 $ / 7,50 $ le 1er janvier 2027).
VERIFIED_MODELS = {
    "gemini-3.8-flash": {
        "provider": "Google",
        "input": 0.75,
        "output": 3.75,
        "note": "Tarif jusqu'au 31 décembre 2026.",
    },
    "claude-sonnet-5-5": {"provider": "Anthropic", "input": 2.0, "output": 10.0, "note": ""},
    "claude-opus-5-5": {"provider": "Anthropic", "input": 4.0, "output": 20.0, "note": ""},
    "gpt-6-luna": {
        "provider": "OpenAI",
        "input": 0.1,
        "output": 0.5,
        "note": "Appels d'outils : raisonnement désactivé.",
    },
}

# Modèles annoncés mais sans API publique : affichés « à venir », jamais sélectionnables.
UPCOMING_MODELS = [
    {
        "label": "Gemini 4",
        "note": "À venir : Google n'a publié ni identifiant ni tarif d'API (vérifié le 2026-10-07).",
    }
]

TIER_KEYS = ("rapide", "equilibre", "avance", "luna")
TIER_TEXT = {
    "rapide": ("Cortex Rapide", "Réponses rapides au coût le plus bas : le bon choix pour la plupart des questions."),
    "equilibre": ("Cortex Équilibré", "Meilleur compromis entre qualité des réponses et coût."),
    "avance": (
        "Cortex Avancé",
        "Raisonnement le plus poussé, pour les demandes complexes. Consomme le budget plus vite.",
    ),
    "luna": ("Cortex Luna", "Très économique et grand contexte, pour les demandes simples et nombreuses."),
}


def provider_key_for(model: str, values: Dict[str, Any]) -> str:
    """La clé du fournisseur qui sert ce modèle (le préfixe de l'identifiant choisit le fournisseur)."""
    lowered = (model or "").strip().lower()
    if lowered.startswith("claude"):
        return values.get("anthropic_api_key") or ""
    if lowered.startswith("gpt-"):
        return values.get("openai_api_key") or ""
    return values.get("api_key") or ""


def tiers(values: Dict[str, Any]) -> list:
    """Les niveaux Cortex avec ce qui est réellement disponible : activé dans les réglages ET clé du fournisseur présente.

    `cost_index` compare le prix de sortie au niveau actif le moins cher (1 = référence) : c'est un calcul, pas une promesse."""
    rows = []
    for key in TIER_KEYS:
        if key == "rapide":
            model = values.get("model") or ""
            price_in, price_out = values.get("price_input_per_mtok"), values.get("price_output_per_mtok")
        else:
            model = values.get(f"tier_{key}_model") or ""
            price_in, price_out = values.get(f"tier_{key}_price_input"), values.get(f"tier_{key}_price_output")
        enabled = bool(values.get(f"tier_{key}_enabled")) and bool(model.strip())
        rows.append(
            {
                "key": key,
                "label": TIER_TEXT[key][0],
                "description": TIER_TEXT[key][1],
                "model": model.strip(),
                "price_input_per_mtok": float(price_in or 0),
                "price_output_per_mtok": float(price_out or 0),
                "enabled": enabled,
                "configured": enabled and bool(provider_key_for(model, values)),
            }
        )
    prices = [r["price_output_per_mtok"] for r in rows if r["configured"] and r["price_output_per_mtok"] > 0]
    floor = min(prices) if prices else 0
    for row in rows:
        row["cost_index"] = (
            round(row["price_output_per_mtok"] / floor, 1) if floor and row["price_output_per_mtok"] else 0
        )
    return rows


def default_tier(values: Dict[str, Any]) -> str:
    """Niveau par défaut : celui des réglages s'il est disponible, sinon le premier niveau disponible."""
    available = [r["key"] for r in tiers(values) if r["configured"]]
    wanted = values.get("default_tier")
    return wanted if wanted in available else (available[0] if available else "")


def load() -> Dict[str, Any]:
    """Réglages effectifs : valeurs des réglages du site, sinon valeurs par défaut ; la clé vient du coffre ou de la config."""
    values = dict(DEFAULTS)
    values["company_limits"] = {}
    values["api_key"] = ""
    values["anthropic_api_key"] = ""
    values["openai_api_key"] = ""
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
            values["anthropic_api_key"] = (
                get_decrypted_password(DOCTYPE, DOCTYPE, "anthropic_api_key", raise_exception=False) or ""
            )
            values["openai_api_key"] = (
                get_decrypted_password(DOCTYPE, DOCTYPE, "openai_api_key", raise_exception=False) or ""
            )
        except Exception:
            values["api_key"] = values["anthropic_api_key"] = values["openai_api_key"] = ""
    if not values["api_key"]:
        values["api_key"] = (getattr(frappe, "conf", None) or {}).get("gemini_api_key") or ""
    if not values["anthropic_api_key"]:
        values["anthropic_api_key"] = (getattr(frappe, "conf", None) or {}).get("anthropic_api_key") or ""
    if not values["openai_api_key"]:
        values["openai_api_key"] = (getattr(frappe, "conf", None) or {}).get("openai_api_key") or ""
    return values
