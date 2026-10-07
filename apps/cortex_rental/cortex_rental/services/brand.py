"""Image de marque d'une société reflétée chez ses clients (portail, devis) : seuls les fichiers publics sont exposés."""

import re
from typing import Any, Dict, Optional

ACCENT_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_ACCENT = "#066336"


def public_file(url: Optional[str]) -> str:
    """L'adresse d'un fichier public (`/files/…`) ou une chaîne vide : un fichier privé n'est jamais montré à un visiteur."""
    value = (url or "").strip()
    if value.startswith("/files/") and ".." not in value and "?" not in value and "\\" not in value:
        return value
    return ""


def accent(color: Optional[str]) -> str:
    value = (color or "").strip()
    return value.lower() if ACCENT_RE.match(value) else DEFAULT_ACCENT


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        v = int(h[i : i + 2], 16) / 255
        channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def readable_text_on(hex_color: str) -> str:
    """Blanc ou presque noir, selon ce qui se lit le mieux sur cette couleur d'accent (bouton principal)."""
    lum = _luminance(hex_color)
    white = 1.05 / (lum + 0.05)
    black = (lum + 0.05) / 0.0537
    return "#ffffff" if white >= black else "#09090b"


def _get(row: Any, key: str) -> Any:
    """Lit un champ d'un dict ou d'un objet à attributs (frappe._dict, ligne de base de données)."""
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def branding(row: Optional[Dict[str, Any]], company: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Pur : l'identité visuelle publique (logo, bannière, phrase d'accueil, couleur) d'une société."""
    row = row or {}
    company = company or {}
    color = accent(_get(row, "portal_accent_color"))
    return {
        "logo": public_file(_get(company, "company_logo")),
        "banner": public_file(_get(row, "portal_banner_image")),
        "tagline": " ".join(str(_get(row, "portal_tagline") or "").split())[:140],
        "accent": color,
        "accent_ink": readable_text_on(color),
    }
