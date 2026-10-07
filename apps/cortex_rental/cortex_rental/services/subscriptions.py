"""Abonnements Cortex (Stripe) : plan de base, modules et niveaux d'IA payants, droits lus par le serveur.

Règles (docs/adr/ADR-010-abonnements-cortex.md) :
- **Désactivé par défaut.** Tant que la facturation n'est pas activée, aucune restriction n'est appliquée et rien n'est
  facturé. L'activation exige les clés Stripe, un prix de base **confirmé par un humain** et, pour chaque option offerte,
  un identifiant de prix Stripe et un prix confirmé : aucun frais ne part avec un prix supposé.
- **Séparé des paiements de location.** Ici : le compte Stripe de la plateforme Cortex (abonnement d'une société).
  Là : la clé Stripe de chaque société (acompte d'un client final, `payments.py`). Deux webhooks, deux secrets.
- **Les droits viennent de Stripe, jamais du navigateur.** Seul le webhook signé écrit l'état de l'abonnement. Un
  événement est traité une seule fois (idempotence par identifiant d'événement) et dans l'ordre (un événement plus
  ancien que le dernier appliqué est ignoré).
- Stripe émet lui-même les factures de l'abonnement et prélève automatiquement (mode abonnement).
- Non éprouvé avec un vrai compte Stripe : testé par signatures et événements simulés seulement.
"""

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

try:
    import frappe
    from frappe.utils import get_url
except ImportError:
    frappe = None

from cortex_rental.services.payments import API, PaymentError, verify_signature

SETTINGS = "Cortex Subscription Settings"
SUBSCRIPTION = "Cortex Subscription"
EVENT = "Cortex Stripe Event"

ALL_TIERS = ("rapide", "equilibre", "avance", "luna")
MODULES = ("portal",)
MODULE_LABELS = {"portal": "Portail client (demandes et suivi)"}
KINDS = {"Module": MODULES, "AI Tier": ALL_TIERS}
CURRENCIES = ("CAD", "USD")
# Accès conservé en retard de paiement : Stripe relance puis annule lui-même; l'accès suit son état.
ACCESS_STATUSES = ("Active", "Trialing", "Past Due")
STRIPE_STATUS = {
    "active": "Active",
    "trialing": "Trialing",
    "past_due": "Past Due",
    "unpaid": "Canceled",
    "canceled": "Canceled",
    "incomplete_expired": "Canceled",
    "incomplete": "Inactive",
    "paused": "Inactive",
}


# ------------------------------------------------------------------ réglages (pur)
def _split(text: Any) -> List[str]:
    return [p.strip() for chunk in str(text or "").splitlines() for p in chunk.split(",") if p.strip()]


def settings_problems(values: Dict[str, Any]) -> List[str]:
    """Pur : ce qui empêche d'enregistrer ces réglages. Liste vide = valides. Activée = exige tout ce qui facture."""
    problems: List[str] = []
    if values.get("currency") and values["currency"] not in CURRENCIES:
        problems.append("La devise doit être CAD ou USD.")
    for field in ("base_monthly_price", "included_ai_budget"):
        if float(values.get(field) or 0) < 0:
            problems.append("Les prix et l'enveloppe ne peuvent pas être négatifs.")
    base_id = (values.get("base_price_id") or "").strip()
    if base_id and not base_id.startswith("price_"):
        problems.append("L'identifiant de prix Stripe du plan de base commence par « price_ ».")
    unknown = [t for t in _split(values.get("base_includes_tiers")) if t not in ALL_TIERS]
    if unknown:
        problems.append(f"Niveaux d'IA inconnus dans le plan de base : {', '.join(unknown)}.")
    seen: Set[tuple] = set()
    for row in values.get("plan_items") or []:
        kind, key = row.get("kind"), (row.get("key") or "").strip()
        if kind not in KINDS or key not in KINDS[kind]:
            problems.append(f"Option inconnue : {kind or '?'} « {key} ».")
            continue
        if (kind, key) in seen:
            problems.append(f"L'option {kind} « {key} » est en double.")
        seen.add((kind, key))
        pid = (row.get("stripe_price_id") or "").strip()
        if pid and not pid.startswith("price_"):
            problems.append(f"L'identifiant de prix de « {key} » commence par « price_ ».")
        if float(row.get("monthly_price") or 0) < 0:
            problems.append(f"Le prix de « {key} » ne peut pas être négatif.")
    if values.get("enabled"):
        if not values.get("stripe_secret_key"):
            problems.append("Saisissez la clé secrète Stripe avant d'activer la facturation.")
        if not values.get("stripe_webhook_secret"):
            problems.append("Saisissez le secret du webhook Stripe avant d'activer la facturation.")
        if float(values.get("base_monthly_price") or 0) <= 0:
            problems.append("Le prix de base doit être supérieur à zéro.")
        if not base_id:
            problems.append("Saisissez l'identifiant de prix Stripe du plan de base.")
        if not values.get("base_price_confirmed"):
            problems.append(
                "Confirmez le prix de base (case à cocher) : aucun frais n'est activé avec un prix supposé."
            )
        for row in values.get("plan_items") or []:
            if row.get("enabled"):
                label = (row.get("key") or "").strip()
                if not row.get("price_confirmed"):
                    problems.append(f"Confirmez le prix de l'option « {label} » ou retirez-la de l'offre.")
                if not (row.get("stripe_price_id") or "").strip():
                    problems.append(f"Saisissez l'identifiant de prix Stripe de l'option « {label} ».")
                if float(row.get("monthly_price") or 0) <= 0:
                    problems.append(f"Le prix de l'option « {label} » doit être supérieur à zéro.")
    return problems


# ------------------------------------------------------------------ droits (pur)
def entitlements_from_items(price_ids: List[str], settings: Dict[str, Any]) -> Dict[str, List[str]]:
    """Pur : modules et niveaux d'IA acquis d'après les prix de l'abonnement (seuls les prix connus comptent)."""
    modules: Set[str] = set()
    tiers: Set[str] = set()
    by_price = {
        (r.get("stripe_price_id") or "").strip(): r
        for r in settings.get("plan_items") or []
        if r.get("stripe_price_id")
    }
    for pid in price_ids:
        row = by_price.get(pid)
        if not row:
            continue
        if row.get("kind") == "Module":
            modules.add(row["key"])
        elif row.get("kind") == "AI Tier":
            tiers.add(row["key"])
    return {"modules": sorted(modules), "ai_tiers": sorted(tiers)}


def compute_entitlements(settings: Dict[str, Any], company: str, sub: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pur : droits de la société. `modules` / `ai_tiers` valent `None` (= tout) quand rien n'est appliqué."""
    if not settings.get("enabled") or company in _split(settings.get("exempt_companies")):
        return {"enforced": False, "status": (sub or {}).get("status") or "Inactive", "modules": None, "ai_tiers": None}
    status = (sub or {}).get("status") or "Inactive"
    if status not in ACCESS_STATUSES:
        return {"enforced": True, "status": status, "modules": [], "ai_tiers": []}
    included = [t for t in _split(settings.get("base_includes_tiers")) if t in ALL_TIERS]
    bought_tiers = _json_list((sub or {}).get("ai_tiers"))
    return {
        "enforced": True,
        "status": status,
        "modules": [m for m in _json_list((sub or {}).get("modules")) if m in MODULES],
        "ai_tiers": sorted(set(included) | {t for t in bought_tiers if t in ALL_TIERS}),
    }


def _json_list(text: Any) -> List[str]:
    if isinstance(text, list):
        return [str(x) for x in text]
    try:
        value = json.loads(text or "[]")
    except ValueError:
        return []
    return [str(x) for x in value] if isinstance(value, list) else []


def map_stripe_status(value: str) -> str:
    return STRIPE_STATUS.get(value or "", "Inactive")


# ------------------------------------------------------------------ lecture des données
def load_settings(with_secrets: bool = False) -> Dict[str, Any]:
    values: Dict[str, Any] = {"enabled": 0, "plan_items": [], "currency": "CAD", "base_includes_tiers": "rapide"}
    if not frappe or not frappe.db.exists("DocType", SETTINGS):
        return values
    doc = frappe.get_single(SETTINGS)
    for field in (
        "enabled",
        "currency",
        "base_label",
        "base_monthly_price",
        "base_price_id",
        "base_price_confirmed",
        "included_ai_budget",
        "base_includes_tiers",
        "exempt_companies",
    ):
        values[field] = doc.get(field)
    values["plan_items"] = [
        {
            k: row.get(k)
            for k in ("kind", "key", "label", "monthly_price", "stripe_price_id", "enabled", "price_confirmed")
        }
        for row in doc.get("plan_items") or []
    ]
    if with_secrets:
        from frappe.utils.password import get_decrypted_password

        for field in ("stripe_secret_key", "stripe_webhook_secret"):
            values[field] = get_decrypted_password(SETTINGS, SETTINGS, field, raise_exception=False) or ""
    return values


def subscription_row(company: str) -> Optional[Dict[str, Any]]:
    if not frappe or not frappe.db.exists(SUBSCRIPTION, company):
        return None
    return frappe.db.get_value(
        SUBSCRIPTION,
        company,
        [
            "status",
            "stripe_customer_id",
            "stripe_subscription_id",
            "current_period_end",
            "cancel_at_period_end",
            "modules",
            "ai_tiers",
            "last_event_created",
        ],
        as_dict=True,
    )


def entitlements(company: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = settings if settings is not None else load_settings()
    return compute_entitlements(settings, company, subscription_row(company) if settings.get("enabled") else None)


def allows_tier(company: str, tier_key: str) -> bool:
    ent = entitlements(company)
    return ent["ai_tiers"] is None or tier_key in ent["ai_tiers"]


def allows_module(company: str, module: str) -> bool:
    ent = entitlements(company)
    return ent["modules"] is None or module in ent["modules"]


def catalog(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Ce que le propriétaire peut acheter, sans aucun secret ni identifiant Stripe."""
    options = [
        {
            "kind": r["kind"],
            "key": r["key"],
            "label": r.get("label") or MODULE_LABELS.get(r["key"]) or r["key"],
            "monthly_price": float(r.get("monthly_price") or 0),
        }
        for r in settings.get("plan_items") or []
        if r.get("enabled") and r.get("price_confirmed") and r.get("stripe_price_id")
    ]
    return {
        "currency": settings.get("currency") or "CAD",
        "base": {
            "label": settings.get("base_label") or "Cortex : abonnement de base",
            "monthly_price": float(settings.get("base_monthly_price") or 0),
            "includes_tiers": [t for t in _split(settings.get("base_includes_tiers")) if t in ALL_TIERS],
        },
        "options": options,
        "included_ai_budget": float(settings.get("included_ai_budget") or 0),
    }


def public_status(company: str) -> Dict[str, Any]:
    settings = load_settings()
    sub = subscription_row(company)
    ent = compute_entitlements(settings, company, sub if settings.get("enabled") else None)
    return {
        "billing_enabled": bool(settings.get("enabled")),
        "enforced": ent["enforced"],
        "status": (sub or {}).get("status") or "Inactive",
        "current_period_end": str((sub or {}).get("current_period_end") or "")[:16],
        "cancel_at_period_end": bool((sub or {}).get("cancel_at_period_end")),
        "modules": ent["modules"],
        "ai_tiers": ent["ai_tiers"],
        "has_customer": bool((sub or {}).get("stripe_customer_id")),
        "catalog": catalog(settings) if settings.get("enabled") else None,
    }


# ------------------------------------------------------------------ Stripe (compte de la plateforme)
def _stripe(path: str, form: Dict[str, str], secret: str, idempotency_key: str, timeout: int = 30) -> Dict[str, Any]:
    if not secret:
        raise PaymentError("La facturation des abonnements n'est pas configurée.")
    request = urllib.request.Request(
        f"{API}{path}",
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise PaymentError("Le service de paiement a refusé la demande. Réessayez ou contactez le support.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PaymentError("Le service de paiement ne répond pas. Réessayez dans un instant.") from exc


def checkout_form(
    company: str, settings: Dict[str, Any], selection: List[Dict[str, str]], customer: str, return_base: str
) -> Dict[str, str]:
    """Pur : formulaire Stripe Checkout (mode abonnement). Les prix viennent des réglages, jamais du navigateur."""
    items = [(settings["base_price_id"], 1)]
    by_key = {(r["kind"], r["key"]): r for r in settings.get("plan_items") or []}
    for choice in selection:
        row = by_key.get((choice.get("kind"), choice.get("key")))
        if not row or not (row.get("enabled") and row.get("price_confirmed") and row.get("stripe_price_id")):
            raise PaymentError("Une des options choisies n'est pas offerte.")
        items.append((row["stripe_price_id"], 1))
    form = {
        "mode": "subscription",
        "success_url": return_base + "?abonnement=ok",
        "cancel_url": return_base,
        "client_reference_id": company,
        "metadata[company]": company,
        "subscription_data[metadata][company]": company,
        "allow_promotion_codes": "false",
    }
    if customer:
        form["customer"] = customer
    for index, (price, quantity) in enumerate(items):
        form[f"line_items[{index}][price]"] = price
        form[f"line_items[{index}][quantity]"] = str(quantity)
    return form


def start_checkout(company: str, selection: List[Dict[str, str]]) -> Dict[str, Any]:
    settings = load_settings(with_secrets=True)
    if not settings.get("enabled"):
        raise PaymentError("La facturation des abonnements n'est pas activée.")
    problems = settings_problems(settings)
    if problems:
        raise PaymentError("La facturation n'est pas prête : " + problems[0])
    sub = subscription_row(company) or {}
    if sub.get("status") in ("Active", "Trialing", "Past Due"):
        raise PaymentError("Cette société a déjà un abonnement : utilisez « Gérer l'abonnement » pour le modifier.")
    form = checkout_form(
        company, settings, selection, sub.get("stripe_customer_id") or "", get_url("/app/cortex-account/societe")
    )
    digest = hashlib.sha256(json.dumps(sorted((c["kind"], c["key"]) for c in selection)).encode("utf-8")).hexdigest()[
        :16
    ]
    key = f"sub-{company}-{digest}-{frappe.utils.today()}"
    session = _stripe("/checkout/sessions", form, settings["stripe_secret_key"], key)
    return {"url": session.get("url")}


def open_portal(company: str) -> Dict[str, Any]:
    settings = load_settings(with_secrets=True)
    sub = subscription_row(company) or {}
    if not settings.get("enabled") or not sub.get("stripe_customer_id"):
        raise PaymentError("Aucun abonnement à gérer pour cette société.")
    session = _stripe(
        "/billing_portal/sessions",
        {"customer": sub["stripe_customer_id"], "return_url": get_url("/app/cortex-account/societe")},
        settings["stripe_secret_key"],
        f"portal-{company}-{frappe.utils.now()}",
    )
    return {"url": session.get("url")}


# ------------------------------------------------------------------ webhook signé
def _price_ids(subscription: Dict[str, Any]) -> List[str]:
    items = ((subscription.get("items") or {}).get("data")) or []
    return [((i.get("price") or {}).get("id") or "") for i in items]


def _period_end(subscription: Dict[str, Any]) -> Optional[int]:
    if subscription.get("current_period_end"):
        return int(subscription["current_period_end"])
    ends = [
        int(i["current_period_end"])
        for i in ((subscription.get("items") or {}).get("data")) or []
        if i.get("current_period_end")
    ]
    return min(ends) if ends else None


def _company_of(obj: Dict[str, Any]) -> Optional[str]:
    company = (obj.get("metadata") or {}).get("company") or obj.get("client_reference_id")
    if not company and obj.get("customer"):
        company = frappe.db.get_value(SUBSCRIPTION, {"stripe_customer_id": obj["customer"]}, "name")
    if not company and obj.get("subscription"):
        company = frappe.db.get_value(SUBSCRIPTION, {"stripe_subscription_id": obj["subscription"]}, "name")
    return company if company and frappe.db.exists("Company", company) else None


def plan_event(
    event: Dict[str, Any], settings: Dict[str, Any], current: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Pur : les champs de l'abonnement à écrire pour cet événement (ou `None` : rien à faire).

    Un événement plus ancien que le dernier appliqué est ignoré (Stripe ne garantit pas l'ordre)."""
    kind = event.get("type") or ""
    obj = (event.get("data") or {}).get("object") or {}
    created = int(event.get("created") or 0)
    last = int((current or {}).get("last_event_created") or 0)
    if kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        if created < last:
            return None
        if kind.endswith("deleted"):
            changes = {"status": "Canceled", "modules": "[]", "ai_tiers": "[]", "cancel_at_period_end": 0}
        else:
            ent = entitlements_from_items(_price_ids(obj), settings)
            changes = {
                "status": map_stripe_status(obj.get("status")),
                "modules": json.dumps(ent["modules"]),
                "ai_tiers": json.dumps(ent["ai_tiers"]),
                "cancel_at_period_end": 1 if obj.get("cancel_at_period_end") else 0,
            }
            end = _period_end(obj)
            if end:
                changes["current_period_end"] = datetime.fromtimestamp(end, tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        changes.update(stripe_subscription_id=obj.get("id") or "", stripe_customer_id=obj.get("customer") or "")
    elif kind == "checkout.session.completed":
        if obj.get("mode") != "subscription":
            return None  # un acompte de location : autre webhook, autre secret
        changes = {
            "stripe_customer_id": obj.get("customer") or "",
            "stripe_subscription_id": obj.get("subscription") or "",
        }
    elif kind == "invoice.payment_failed":
        if created < last or (current or {}).get("status") != "Active":
            return None
        changes = {"status": "Past Due"}
    elif kind == "invoice.paid":
        if created < last or (current or {}).get("status") != "Past Due":
            return None
        changes = {"status": "Active"}
    else:
        return None
    changes["last_event_created"] = max(created, last)
    changes["last_event_id"] = event.get("id") or ""
    return changes


def handle_event(payload: bytes, signature: str) -> Dict[str, Any]:
    """Webhook Stripe de la plateforme : signature vérifiée avec SON secret, événement traité une seule fois."""
    settings = load_settings(with_secrets=True)
    if not settings.get("enabled") or not verify_signature(
        payload, signature, settings.get("stripe_webhook_secret") or ""
    ):
        return {"ok": False, "code": "bad_signature"}
    try:
        event = json.loads(payload.decode("utf-8"))
        event_id = str(event["id"])
    except (ValueError, KeyError, AttributeError):
        return {"ok": False, "code": "bad_payload"}
    if frappe.db.exists(EVENT, event_id):
        return {"ok": True, "duplicate": True}
    obj = (event.get("data") or {}).get("object") or {}
    company = _company_of(obj)
    outcome = "ignored"
    if company:
        current = subscription_row(company)
        changes = plan_event(event, settings, current)
        if changes is not None:
            before = dict(current or {})
            if current is None:
                frappe.get_doc({"doctype": SUBSCRIPTION, "company": company, "status": "Inactive"}).insert(
                    ignore_permissions=True
                )
            frappe.db.set_value(SUBSCRIPTION, company, changes)
            outcome = changes.get("status") or "updated"
            _audit(company, event, before, changes)
        else:
            outcome = "skipped"
    frappe.get_doc(
        {
            "doctype": EVENT,
            "event_id": event_id,
            "event_type": event.get("type") or "",
            "company": company,
            "outcome": outcome,
        }
    ).insert(ignore_permissions=True)
    return {"ok": True, "outcome": outcome}


def _audit(company: str, event: Dict[str, Any], before: Dict[str, Any], after: Dict[str, Any]) -> None:
    try:
        from cortex_rental.services.audit import AuditService

        AuditService.record_mutation(
            company=company,
            action=f"cortex.subscription.{(event.get('type') or 'event').replace('customer.subscription.', '')}",
            entity_type=SUBSCRIPTION,
            entity_id=company,
            before_state={k: before.get(k) for k in ("status", "modules", "ai_tiers")},
            after_state={k: after.get(k) for k in ("status", "modules", "ai_tiers") if k in after},
        )
    except Exception:
        frappe.log_error(title="Cortex subscription audit failed")
