"""Portail client : demandes de location sans compte, calendrier public du matériel, suivi de la réponse.

Règles (docs/adr/ADR-009-portail-client-et-signature.md) :
- Une demande n'est **pas** une réservation : elle arrive comme une demande entrante (`Cortex Inbound Request`,
  canal « Web Portal ») que l'équipe traite. Rien n'est bloqué, facturé ni confirmé par le portail.
- Le calendrier public n'affiche que des statuts par jour (libre, en partie réservé, complet) : jamais de quantités,
  de clients ni de numéros de dossier. La vérification qui fait foi reste celle du serveur à la réservation.
- Le suivi se fait par un jeton aléatoire dont seule l'empreinte (SHA-256) est conservée; la page de suivi ne montre
  rien de personnel (ni courriel, ni téléphone) et ne montre que le message que l'équipe a choisi d'adresser au client.
- Chaque société active son portail et choisit son identifiant (`portal_slug`); un portail désactivé répond comme s'il
  n'existait pas.
"""

import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

try:
    import frappe
    from frappe.utils import get_url, now_datetime
except ImportError:
    frappe = None

SETTINGS = "Cortex Finance Settings"
INBOUND = "Cortex Inbound Request"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s.]{2,}$")
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,25}$")
MAX_SPAN_DAYS = 90
MAX_AHEAD_DAYS = 730
MAX_ITEMS = 30
MAX_MESSAGE = 1500
DAILY_CAP = 50  # demandes du portail acceptées par société et par jour (protège l'équipe d'un envoi massif)

STATE_TEXT = {
    "Received": ("received", "Reçue", "Votre demande est bien reçue. Une personne de l'équipe vous répondra."),
    "Processing": ("review", "En cours d'examen", "Votre demande est en cours d'examen par l'équipe."),
    "Processed": ("done", "Traitée", "Votre demande a été traitée : l'équipe vous envoie un devis."),
    "Rejected": ("declined", "Refusée", "L'équipe ne peut pas donner suite à cette demande."),
}


class PortalError(ValueError):
    """Erreur de règle affichable telle quelle au visiteur (message en français, sans détail technique)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def clean(value: Any, limit: int, multiline: bool = False) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]*>", "", text)  # aucune balise : le texte est affiché, jamais interprété
    text = text.replace("\r", "")
    text = text.strip() if multiline else " ".join(text.split())
    return text[:limit]


def parse_day(value: Any, label: str) -> date:
    try:
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        raise PortalError("bad_date", f"La date « {label} » est invalide.") from None


def validate_period(starts: Any, ends: Any, today: date) -> Tuple[date, date]:
    first, last = parse_day(starts, "début"), parse_day(ends, "fin")
    if first < today:
        raise PortalError("past_date", "La date de début est déjà passée.")
    if last < first:
        raise PortalError("bad_period", "La fin doit être après le début.")
    if (last - first).days + 1 > MAX_SPAN_DAYS:
        raise PortalError("too_long", f"La période ne peut pas dépasser {MAX_SPAN_DAYS} jours.")
    if (first - today).days > MAX_AHEAD_DAYS:
        raise PortalError("too_far", "La date de début est trop éloignée.")
    return first, last


def validate_request(form: Dict[str, Any], today: date, known_items: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Pur : nettoie et valide une demande. `known_items` associe code → nom pour les équipements de la société."""
    if clean(form.get("website"), 200):  # champ piège invisible : un robot le remplit, une personne jamais
        raise PortalError("rejected", "Votre demande n'a pas pu être envoyée.")
    name = clean(form.get("name"), 80)
    if len(name) < 2:
        raise PortalError("name", "Indiquez votre nom.")
    email = clean(form.get("email"), 254).lower()
    if not EMAIL_RE.match(email):
        raise PortalError("email", "Indiquez un courriel valide pour que l'équipe puisse vous répondre.")
    phone = clean(form.get("phone"), 25)
    if phone and not PHONE_RE.match(phone):
        raise PortalError("phone", "Le numéro de téléphone semble invalide.")
    first, last = validate_period(form.get("starts"), form.get("ends"), today)
    if str(form.get("consent")).lower() not in ("1", "true", "on", "yes"):
        raise PortalError("consent", "Acceptez d'être contacté au sujet de votre demande.")
    message = clean(form.get("message"), MAX_MESSAGE, multiline=True)

    raw_items = form.get("items") or []
    if isinstance(raw_items, str):
        try:
            raw_items = json.loads(raw_items)
        except ValueError:
            raise PortalError("items", "La liste du matériel est invalide.") from None
    if not isinstance(raw_items, list) or len(raw_items) > MAX_ITEMS:
        raise PortalError("items", f"Choisissez au plus {MAX_ITEMS} équipements.")
    items = []
    seen = set()
    for entry in raw_items:
        code = clean((entry or {}).get("item_code") if isinstance(entry, dict) else entry, 140)
        if not code or code in seen:
            continue
        if known_items is not None and code not in known_items:
            raise PortalError("items", "Un des équipements choisis n'est pas offert par cette entreprise.")
        try:
            quantity = int((entry or {}).get("quantity", 1)) if isinstance(entry, dict) else 1
        except (TypeError, ValueError):
            raise PortalError("items", "Une quantité est invalide.") from None
        if not 1 <= quantity <= 99:
            raise PortalError("items", "Chaque quantité doit être comprise entre 1 et 99.")
        seen.add(code)
        items.append({"item_code": code, "item_name": (known_items or {}).get(code, code), "quantity": quantity})
    if not items and len(message) < 10:
        raise PortalError("empty", "Choisissez du matériel ou décrivez votre besoin en quelques mots.")
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "organisation": clean(form.get("organisation"), 120),
        "project": clean(form.get("project"), 120),
        "starts": first.isoformat(),
        "ends": last.isoformat(),
        "items": items,
        "message": message,
    }


def public_state(status: str) -> Dict[str, str]:
    key, label, text = STATE_TEXT.get(status or "Received", STATE_TEXT["Received"])
    return {"state": key, "label": label, "text": text}


# ------------------------------------------------------------------ accès aux données
def company_for_slug(slug: str) -> Optional[Dict[str, Any]]:
    """La société dont le portail est activé à cet identifiant, sinon `None` (même réponse qu'un portail inexistant)."""
    slug = (slug or "").strip().lower()
    if not SLUG_RE.match(slug):
        return None
    row = frappe.db.get_value(
        SETTINGS,
        {"portal_slug": slug, "portal_requests_enabled": 1},
        ["name", "portal_slug", "portal_tagline", "portal_banner_image", "portal_accent_color"],
        as_dict=True,
    )
    if not row:
        return None
    company = row.name
    from cortex_rental.services import subscriptions

    if not subscriptions.allows_module(company, "portal"):
        return None  # module non inclus dans l'abonnement : même réponse qu'un portail inexistant
    info = frappe.db.get_value("Company", company, ["company_name", "company_logo"], as_dict=True) or {}
    from cortex_rental.services import brand

    look = brand.branding(row, info)
    return {"company": company, "name": info.get("company_name") or company, **look}


def known_items(company: str) -> Dict[str, str]:
    rows = frappe.get_all(
        "Cortex Rental Item Profile",
        filters={"company": company},
        fields=["item_code", "item_name"],
        limit_page_length=500,
    )
    return {r.item_code: r.item_name or r.item_code for r in rows}


def item_images(company: str) -> Dict[str, str]:
    """Photos publiques des équipements (jamais un fichier privé)."""
    from cortex_rental.services import brand

    rows = frappe.get_all(
        "Cortex Rental Item Profile", filters={"company": company}, fields=["item_code", "image"], limit_page_length=500
    )
    return {r.item_code: brand.public_file(r.image) for r in rows if brand.public_file(r.image)}


def public_calendar(slug: str, starts: str, ends: str, search: str = "") -> Dict[str, Any]:
    """Statuts par jour du matériel de la société, sans quantité ni client."""
    from cortex_rental.api.v1.availability import get_matrix_handler
    from cortex_rental.services import availability_summary

    info = company_for_slug(slug)
    if not info:
        raise PortalError("closed", "Ce portail n'est pas disponible.")
    first, last = parse_day(starts, "début"), parse_day(ends, "fin")
    if last < first or (last - first).days + 1 > 62:
        raise PortalError("bad_period", "Choisissez une période de 62 jours au plus.")
    matrix = get_matrix_handler(
        {
            "starts_at": f"{first.isoformat()} 00:00:00",
            "ends_at": f"{(last + timedelta(days=1)).isoformat()} 00:00:00",
            "search": clean(search, 60),
        },
        info["company"],
    )
    days = (last - first).days + 1
    rows = availability_summary.day_statuses(matrix.get("items", []), first.isoformat(), days, datetime.now())
    images = item_images(info["company"])
    return {
        "company": info["name"],
        "starts": first.isoformat(),
        "ends": last.isoformat(),
        "days": [(first + timedelta(days=i)).isoformat() for i in range(days)],
        "items": [
            {
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "category": r["category"],
                "image": images.get(r["item_code"], ""),
                "days": r["days"],
            }
            for r in rows
        ],
        "note": "Indicatif : l'équipe confirme la disponibilité dans son devis. Une demande ne réserve rien.",
    }


def submit_request(slug: str, form: Dict[str, Any]) -> Dict[str, Any]:
    info = company_for_slug(slug)
    if not info:
        raise PortalError("closed", "Ce portail n'est pas disponible.")
    company = info["company"]
    data = validate_request(form, date.today(), known_items(company))
    today_start = now_datetime().strftime("%Y-%m-%d 00:00:00")
    if (
        frappe.db.count(INBOUND, {"company": company, "source_channel": "Web Portal", "creation": [">=", today_start]})
        >= DAILY_CAP
    ):
        raise PortalError(
            "busy", "L'entreprise a reçu beaucoup de demandes aujourd'hui. Réessayez demain ou écrivez-lui."
        )
    token = secrets.token_urlsafe(24)
    subject = f"Demande de {data['name']}" + (f" — {data['project']}" if data["project"] else "")
    doc = frappe.get_doc(
        {
            "doctype": INBOUND,
            "company": company,
            "source_channel": "Web Portal",
            "sender_email": data["email"],
            "subject": subject[:140],
            "requester_name": data["name"],
            "raw_payload": json.dumps(data, ensure_ascii=False),
            "status": "Received",
            "tracking_hash": hash_token(token),
        }
    )
    doc.insert(ignore_permissions=True)  # visiteur sans compte : seule cette fonction, après validation, écrit ici
    _notify_team(company, doc.name, data["name"])
    return {"request": doc.name, "tracking_url": get_url(f"/suivi/{token}"), "company": info["name"]}


def track(token: str) -> Dict[str, Any]:
    """Vue publique d'une demande : état, période, matériel demandé et message de l'équipe. Rien de personnel."""
    token = (token or "").strip()[:100]
    row = (
        frappe.db.get_value(
            INBOUND,
            {"tracking_hash": hash_token(token), "source_channel": "Web Portal"},
            ["name", "company", "status", "raw_payload", "public_message", "creation"],
            as_dict=True,
        )
        if token
        else None
    )
    if not row:
        return {"state": "unknown"}
    try:
        payload = json.loads(row.raw_payload or "{}")
    except ValueError:
        payload = {}
    info = frappe.db.get_value("Company", row.company, ["company_name", "company_logo"], as_dict=True) or {}
    from cortex_rental.services import brand

    look = brand.branding(
        frappe.db.get_value(
            SETTINGS, row.company, ["portal_tagline", "portal_banner_image", "portal_accent_color"], as_dict=True
        ),
        info,
    )
    status = public_state(row.status)
    images = item_images(row.company)
    return {
        **status,
        "reference": row.name,
        "company": info.get("company_name") or row.company,
        "logo": look["logo"],
        "banner": look["banner"],
        "tagline": look["tagline"],
        "accent": look["accent"],
        "accent_ink": look["accent_ink"],
        "received": str(row.creation)[:16],
        "starts": payload.get("starts", ""),
        "ends": payload.get("ends", ""),
        "items": [
            {
                "item_name": i.get("item_name", ""),
                "quantity": i.get("quantity", 1),
                "image": images.get(i.get("item_code", ""), ""),
            }
            for i in payload.get("items", [])
        ],
        "team_message": clean(row.public_message, 1000, multiline=True),
    }


def _notify_team(company: str, request_name: str, who: str) -> None:
    """Prévient l'équipe en direct et par notification (les rôles qui traitent les demandes). Jamais bloquant."""
    try:
        from cortex_rental.services import team_activity

        text = "a envoyé une demande par le portail"
        team_activity.publish_company_activity(
            company, {"actor": who, "text": text, "entity_type": INBOUND, "entity_id": request_name, "reserve": ""}
        )
        roles = ("Cortex Operations Manager", "Rental Manager", "Cortex Counter Staff")
        for user in team_activity.company_members(company):
            if user in ("Administrator", "Guest"):
                continue
            if not set(roles) & set(frappe.get_roles(user)):
                continue
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "subject": f"{who} {text}",
                    "document_type": INBOUND,
                    "document_name": request_name,
                }
            ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="Cortex portal request notification failed")
