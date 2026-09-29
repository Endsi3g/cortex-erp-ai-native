"""Pure rules for access requests: no Frappe import, unit-tested directly."""

import hashlib
import hmac
import re
import secrets
import unicodedata
from typing import Iterable, Optional, Tuple

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)

FREE_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.ca",
        "yahoo.fr",
        "icloud.com",
        "me.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "gmx.com",
        "mail.com",
        "videotron.ca",
        "bell.net",
    }
)

TEAM_SIZES = ("", "1", "2-10", "11-50", "51+")


class SignupError(ValueError):
    """A rule failed; `code` is stable for the UI, the message is French and safe to show."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def normalize_email(email: Optional[str]) -> str:
    """Trim and lower-case; accept the usual variations, refuse what cannot be an address."""
    value = (email or "").strip().lower()
    if len(value) > 254 or not EMAIL_RE.match(value):
        raise SignupError("invalid_email", "Saisissez une adresse courriel valide, par exemple nom@entreprise.com.")
    return value


def email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1]


def split_lines(value: Optional[str]) -> list:
    return [line.strip().lower().lstrip("@") for line in (value or "").replace(",", "\n").splitlines() if line.strip()]


def check_domain_policy(email: str, allowed: Iterable[str] = (), block_free: bool = True) -> None:
    """Raise SignupError when the domain is refused. An explicit allow-list wins over the free-mail rule."""
    domain = email_domain(email)
    allow = [d for d in allowed if d]
    if allow:
        if domain not in allow:
            raise SignupError(
                "domain_not_allowed",
                "Cette adresse n'appartient pas à un domaine autorisé. Utilisez votre courriel professionnel.",
            )
        return
    if block_free and domain in FREE_EMAIL_DOMAINS:
        raise SignupError(
            "free_email",
            "Utilisez votre courriel professionnel : les adresses personnelles (Gmail, Outlook…) ne sont pas acceptées.",
        )


def clean_name(value: Optional[str], label: str, maximum: int = 140) -> str:
    text = " ".join((value or "").split())
    if not text:
        raise SignupError("required", f"{label} est requis.")
    if len(text) > maximum:
        raise SignupError("too_long", f"{label} est trop long ({maximum} caractères au maximum).")
    if re.search(r"[<>]", text):
        raise SignupError("invalid_characters", f"{label} contient des caractères non permis.")
    return text


def new_token(request_id: str) -> Tuple[str, str]:
    """Return (token to email, sha256 to store). The token embeds the request id so lookup is direct."""
    secret = secrets.token_urlsafe(32)
    return f"{request_id}.{secret}", hash_secret(secret)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def split_token(token: Optional[str]) -> Tuple[str, str]:
    """`ACC-REQ-2026-00001.secret` -> (request id, secret). Raises SignupError on any other shape."""
    value = (token or "").strip()
    request_id, dot, secret = value.rpartition(".")
    if not dot or not request_id or not secret or len(value) > 200:
        raise SignupError("invalid_token", "Ce lien n'est pas valide.")
    return request_id, secret


def token_matches(secret: str, stored_hash: Optional[str]) -> bool:
    return bool(stored_hash) and hmac.compare_digest(hash_secret(secret), stored_hash)


def abbreviation(company_name: str, taken: Iterable[str]) -> str:
    """Company abbreviation from initials, made unique against `taken` (case-insensitive)."""
    used = {t.upper() for t in taken}
    ascii_name = unicodedata.normalize("NFKD", company_name).encode("ascii", "ignore").decode("ascii")
    words = [w for w in re.split(r"[^A-Za-z0-9]+", ascii_name.upper()) if w]
    base = "".join(w[0] for w in words)[:4] or "CO"
    if len(base) < 2:
        base = (words[0][:3] if words else "CO").ljust(2, "X")
    candidate, index = base, 2
    while candidate in used:
        candidate = f"{base}{index}"
        index += 1
    return candidate
