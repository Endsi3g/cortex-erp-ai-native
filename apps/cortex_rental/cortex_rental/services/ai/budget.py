"""Budget et usage de l'IA par société : on compte les jetons et le coût de chaque appel, on refuse au plafond.

Le plafond est décidé par réglage (défaut) et peut être ajusté par société. 0 veut dire « aucun plafond ». Le coût
vient des prix par million de jetons saisis dans les réglages ; sans prix, seul le nombre de jetons compte.
"""

from datetime import date
from typing import Any, Dict, Optional

try:
    import frappe
except ImportError:
    frappe = None

USAGE = "Cortex AI Usage"


class BudgetExceeded(RuntimeError):
    pass


def cost_of(input_tokens: int, output_tokens: int, settings: Dict[str, Any]) -> float:
    return round(
        input_tokens / 1_000_000 * float(settings.get("price_input_per_mtok") or 0)
        + output_tokens / 1_000_000 * float(settings.get("price_output_per_mtok") or 0),
        6,
    )


def limits_for(company: str, settings: Dict[str, Any]):
    override = (settings.get("company_limits") or {}).get(company) or {}
    budget = override.get("budget") or float(settings.get("default_monthly_budget") or 0)
    tokens = override.get("tokens") or int(settings.get("default_monthly_token_cap") or 0)
    return float(budget), int(tokens)


def month_to_date(company: str) -> Dict[str, float]:
    first = date.today().replace(day=1)
    row = frappe.db.sql(
        f"SELECT COALESCE(SUM(cost),0), COALESCE(SUM(input_tokens + output_tokens),0), COUNT(*) FROM `tab{USAGE}` "
        "WHERE company=%s AND creation >= %s",
        (company, first),
    )[0]
    return {"cost": float(row[0]), "tokens": int(row[1]), "calls": int(row[2])}


def status(company: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    used = month_to_date(company)
    cost_cap, token_cap = limits_for(company, settings)
    percent = 0.0
    if cost_cap > 0:
        percent = used["cost"] / cost_cap * 100
    elif token_cap > 0:
        percent = used["tokens"] / token_cap * 100
    economy_model = (settings.get("economy_model") or "").strip()
    # Au plafond : on passe au modèle économique (si défini) jusqu'à `economy_cap_percent` % du budget, puis on refuse.
    hard = float(settings.get("economy_cap_percent") or 150) if economy_model else 100.0
    return {
        **used,
        "cost_cap": cost_cap,
        "token_cap": token_cap,
        "percent": round(percent, 1),
        "warning": percent >= float(settings.get("warn_percent") or 80) and percent < 100,
        "economy": bool(economy_model) and 100 <= percent < hard,
        "blocked": percent >= hard,
    }


def check(company: str, settings: Dict[str, Any]) -> None:
    """Refuse l'appel si le plafond mensuel de la société est atteint."""
    current = status(company, settings)
    if current["blocked"]:
        raise BudgetExceeded(
            "Le budget mensuel de l'assistant est atteint pour votre société. "
            "Il se renouvelle au début du mois ; un administrateur peut aussi l'ajuster."
        )


def record(
    company: str,
    user: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    settings: Dict[str, Any],
    request_id: Optional[str] = None,
    tool_calls: int = 0,
    prices: Optional[Dict[str, Any]] = None,
) -> None:
    """`prices` : prix du modèle réellement utilisé (le modèle économique n'a pas les mêmes prix)."""
    doc = frappe.get_doc(
        {
            "doctype": USAGE,
            "company": company,
            "user": user,
            "provider": provider,
            "model": model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost": cost_of(input_tokens, output_tokens, prices or settings),
            "tool_calls": int(tool_calls),
            "request_id": request_id or "",
        }
    )
    doc.flags.from_gateway = True
    doc.insert(ignore_permissions=True)
