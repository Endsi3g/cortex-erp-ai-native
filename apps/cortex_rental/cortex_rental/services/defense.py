"""Garde-fous partagés : limites de débit, validation des fichiers et en-têtes de sécurité.

Principes :
- on ne fait jamais confiance à l'extension d'un fichier : on lit ses premiers octets (`sniff_image`);
- le débit est limité par personne (ou par adresse IP pour les visiteurs) avec un compteur Redis atomique;
- si Redis est indisponible, on laisse passer (la disponibilité du service prime sur le frein) mais on le journalise;
- aucune fonction ici n'écrit dans la base de données.
"""

import functools
import re
from typing import Callable, Optional

try:
    import frappe
except ImportError:  # tests unitaires sans bench
    frappe = None

# Frein global : très au-dessus d'un usage humain (un écran fait ~10 appels), il ne vise que les boucles folles et l'abus.
USER_PER_MINUTE = 900
GUEST_PER_MINUTE = 120
SKIPPED_PREFIXES = ("/assets/", "/files/", "/private/files/")

_SIGNATURES = (
    ("png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ("jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ("webp", lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    ("gif", lambda b: b[:6] in (b"GIF87a", b"GIF89a")),
)


def sniff_image(content: Optional[bytes], allowed=("png", "jpg", "webp")) -> Optional[str]:
    """Le vrai type d'une image d'après ses premiers octets, ou None si ce n'est pas un format autorisé.

    Un fichier renommé « logo.png » qui contient du SVG, du HTML ou un exécutable est refusé."""
    if not content:
        return None
    if isinstance(content, str):  # Frappe renvoie du texte pour un contenu lisible en UTF-8 : jamais une image valide
        content = content.encode("utf-8", "ignore")
    head = bytes(content[:16])
    for kind, matches in _SIGNATURES:
        if kind in allowed and matches(head):
            return kind
    return None


def _cache():
    return frappe.cache() if callable(getattr(frappe, "cache", None)) else frappe.cache


def _factor() -> float:
    """Multiplicateur des limites (site_config `cortex_rate_limit_factor`, 1 par défaut) : sert aux essais de charge, jamais en production."""
    try:
        return max(1.0, float(frappe.conf.get("cortex_rate_limit_factor") or 1))
    except (TypeError, ValueError):
        return 1.0


def hit(bucket: str, limit: int, seconds: int) -> bool:
    """Compte un appel dans `bucket` : True s'il reste de la marge, False si la limite est dépassée.

    Compteur atomique (INCR) dont l'expiration est posée au premier appel de la fenêtre."""
    if not frappe:
        return True
    try:
        cache = _cache()
        key = cache.make_key(f"cortex_rl:{bucket}")
        count = cache.incrby(key, 1)
        if count == 1:
            cache.expire(key, seconds)
        return int(count) <= limit * _factor()
    except Exception:
        frappe.log_error(title="Cortex : frein de débit indisponible")
        return True


def enforce(bucket: str, limit: int, seconds: int, message: str = "") -> None:
    """Lève une erreur 429 (français) quand la limite est dépassée."""
    if not hit(bucket, limit, seconds):
        frappe.throw(
            message or "Trop de demandes en peu de temps. Patientez un moment avant de réessayer.",
            frappe.TooManyRequestsError,
        )


def limit_user(action: str, limit: int, seconds: int = 3600) -> Callable:
    """Décorateur : limite une action sensible par personne connectée (envoi d'invitations, téléversements…)."""

    def decorate(function: Callable) -> Callable:
        @functools.wraps(function)  # Frappe lit la signature d'origine (inspect.signature suit __wrapped__)
        def wrapper(*args, **kwargs):
            enforce(f"{action}:{frappe.session.user}", limit, seconds)
            return function(*args, **kwargs)

        return wrapper

    return decorate


TECHNICAL_MESSAGE = re.compile(
    r"^(invalid literal|could not convert|Expecting|Extra data|Unterminated|unsupported|not enough|too many|"
    r"math domain|time data|Invalid isoformat|Out of range|cannot convert|float|int\()",
    re.IGNORECASE,
)


def safe_input(function: Callable) -> Callable:
    """Décorateur d'endpoint : une valeur d'entrée invalide (ValueError, JSON cassé, clé absente) devient une réponse 417
    claire en français, jamais une erreur serveur 500. Les autres erreurs (vrais bogues) restent des 500 et sont journalisées."""

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as error:  # inclut json.JSONDecodeError
            message = str(error).strip()
            if not message or TECHNICAL_MESSAGE.match(message):
                message = "Une des valeurs envoyées est invalide."
            frappe.throw(message, frappe.ValidationError)
        except KeyError as error:
            frappe.throw(f"Champ obligatoire manquant : {error.args[0] if error.args else ''}.", frappe.ValidationError)

    return wrapper


def json_object(value, label: str = "Les réglages") -> dict:
    """Un objet JSON (dict) venant d'un formulaire, ou une erreur 417 claire si ce n'est pas un objet."""
    if isinstance(value, dict):
        return value
    try:
        parsed = frappe.parse_json(value) if value not in (None, "") else {}
    except ValueError:
        parsed = None
    if not isinstance(parsed, dict):
        frappe.throw(f"{label} doivent être envoyés sous forme d'objet JSON.", frappe.ValidationError)
    return parsed


# ---- crochets Frappe (hooks.py) -----------------------------------------------------------------------


def request_brake() -> None:
    """Frein global avant chaque requête d'API : par personne (ou par adresse IP pour un visiteur), par minute."""
    if not frappe:
        return
    request = getattr(frappe.local, "request", None)
    path = getattr(request, "path", "") or ""
    if request is None or path.startswith(SKIPPED_PREFIXES):
        return
    if not (path.startswith("/api/") or path.startswith("/devis")):
        return
    user = frappe.session.user
    if user == "Guest":
        ip = getattr(frappe.local, "request_ip", None) or "inconnue"
        enforce(f"guest:{ip}:{_minute()}", GUEST_PER_MINUTE, 90)
    else:
        enforce(f"user:{user}:{_minute()}", USER_PER_MINUTE, 90)


def _minute() -> int:
    import time

    return int(time.time() // 60)


def security_headers(response=None, request=None) -> None:
    """En-têtes de sécurité sur chaque réponse. Le HSTS n'est posé que derrière HTTPS (jamais en développement)."""
    if response is None:
        return
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    # Le micro est permis à la page Cortex elle-même (saisie vocale de l'assistant), jamais à un contenu tiers intégré.
    # `microphone=()` bloquait la reconnaissance vocale pour tout le monde, quel que soit le réglage du navigateur.
    headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=(), payment=(self)")
    secure = bool(request is not None and (request.is_secure or request.headers.get("X-Forwarded-Proto") == "https"))
    if secure and not (frappe and frappe.conf.get("developer_mode")):
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


LOCKOUT_MARKER = "has been locked"


def normalize_lockout(response=None, request=None) -> None:
    """Un compte verrouillé après trop d'échecs de connexion répond 429 + `Retry-After` (Frappe répond 500 pour cela).

    Un 500 fausse la surveillance (fausses alertes) et trompe les clients HTTP; 429 dit exactement ce qui se passe."""
    if response is None or response.status_code != 500 or request is None:
        return
    if not (getattr(request, "path", "") or "").endswith("/api/method/login"):
        return
    try:
        body = response.get_data(as_text=True)
    except Exception:
        return
    if "SecurityException" in body and LOCKOUT_MARKER in body:
        response.status_code = 429
        match = re.search(r"(\d+) seconds", body)
        if match:
            response.headers["Retry-After"] = match.group(1)
