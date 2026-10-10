"""Mesure d'usage avec PostHog : ce que Cortex apprend de l'usage réel, sans jamais exposer de données d'affaires.

Principes :
- la clé de projet PostHog (`phc_…`, publique par conception) et l'hôte vivent dans la configuration du site, jamais dans le
  dépôt (`bench --site <site> set-config posthog_key phc_…`); sans clé valide, rien n'est chargé ni envoyé;
- la personne est identifiée par une empreinte à clé secrète (HMAC), jamais par son courriel ni son nom; la société sert de
  « groupe » PostHog pour comparer les clients entre eux;
- on capture tous les clics, pages, erreurs et performances, et les enregistrements de session masquent par défaut les champs
  de saisie et le texte des données d'affaires (Loi 25 : ni montants, ni noms de clients, ni messages de l'assistant);
- `posthog_capture_pii` (booléen du site) lève le masquage; c'est une décision du propriétaire de l'instance, pas un défaut;
- le navigateur de la personne peut refuser (Do Not Track / Global Privacy Control) : on le respecte.
"""

import hashlib
import hmac
import re
from typing import Any, Dict, Optional

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

KEY_RE = re.compile(r"^phc_[A-Za-z0-9]{20,80}$")
HOST_RE = re.compile(r"^https://[a-z0-9.-]+\.posthog\.com$|^https://[a-z0-9.-]+\.[a-z]{2,}(:\d{2,5})?$")
DEFAULT_HOST = "https://us.i.posthog.com"
EXCLUDED_USERS = ("Administrator", "Guest")

# Texte et zones jamais lisibles dans un enregistrement de session tant que `posthog_capture_pii` n'est pas levé.
MASK_TEXT_SELECTOR = ", ".join(
    [
        ".form-control",
        ".frappe-control .control-value",
        ".dt-cell__content",
        ".list-row",
        ".report-wrapper",
        ".cx-chat-message",
        ".cx-home-composer",
        ".cx-sensitive",
        ".ph-mask",
    ]
)


def clean_key(value: Any) -> str:
    """Pur : la clé de projet si elle a la forme d'une clé PostHog, sinon une chaîne vide."""
    text = str(value or "").strip()
    return text if KEY_RE.match(text) else ""


def clean_host(value: Any) -> str:
    """Pur : l'hôte PostHog en https (région ou instance dédiée), sans chemin; sinon l'hôte américain par défaut."""
    text = str(value or "").strip().rstrip("/")
    return text if text and len(text) <= 120 and HOST_RE.match(text) else DEFAULT_HOST


def distinct_id(user: str, secret: str) -> str:
    """Pur : identifiant stable et anonyme d'une personne (HMAC-SHA256 du compte, tronqué), non réversible sans la clé du site."""
    digest = hmac.new(str(secret or "").encode("utf-8"), str(user or "").lower().encode("utf-8"), hashlib.sha256)
    return "u_" + digest.hexdigest()[:32]


def build_config(
    user: str,
    company: str = "",
    roles=(),
    *,
    key: Any = None,
    host: Any = None,
    secret: str = "",
    capture_pii: bool = False,
    disabled: bool = False,
    version: str = "",
) -> Optional[Dict[str, Any]]:
    """Pur : la configuration remise au navigateur, ou None quand la mesure doit rester éteinte."""
    project_key = clean_key(key)
    if disabled or not project_key or not user or user in EXCLUDED_USERS or not secret:
        return None
    config = {
        "key": project_key,
        "host": clean_host(host),
        "distinct_id": distinct_id(user, secret),
        "capture_pii": bool(capture_pii),
        "mask_text_selector": "" if capture_pii else MASK_TEXT_SELECTOR,
        "person": {"roles": sorted({str(r) for r in roles if r})[:30], "app_version": str(version or "")[:20]},
    }
    if company:
        config["group"] = {"company": str(company)[:140]}
    return config


def boot_config(user: str, company: str = "") -> Optional[Dict[str, Any]]:
    """Lecture seule : la configuration de mesure de la personne connectée, à partir de la configuration du site."""
    if not frappe:
        return None
    conf = frappe.conf
    secret = str(conf.get("encryption_key") or "")
    try:
        roles = frappe.get_roles(user)
    except Exception:
        roles = []
    try:
        from cortex_rental import __version__ as version
    except Exception:
        version = ""
    return build_config(
        user,
        company,
        roles,
        key=conf.get("posthog_key"),
        host=conf.get("posthog_host"),
        secret=secret,
        capture_pii=bool(conf.get("posthog_capture_pii")),
        disabled=bool(conf.get("posthog_disabled")),
        version=version,
    )
