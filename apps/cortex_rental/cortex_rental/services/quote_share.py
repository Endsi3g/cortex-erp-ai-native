"""Devis partagé avec le client : lien à copier ou envoyé par courriel, consultation publique, réponse du client.

Règles (docs/adr/ADR-007-portail-de-devis.md) :
- Le lien contient un jeton aléatoire ; seule son empreinte (SHA-256) est conservée. Le jeton n'est montré qu'une fois.
- Le client voit un **instantané** du devis au moment de l'envoi (prix et lignes figés). Si le devis change ensuite, le
  lien n'est plus « à jour » et le client ne peut plus accepter : il faut envoyer un nouveau lien.
- « Accepter » est une réponse du client, **pas une réservation** : le matériel n'est bloqué que lorsque l'équipe réserve
  (la disponibilité est revérifiée sous verrou). Rien n'est facturé ni bloqué par le portail.
- Toute réponse est auditée (acteur « Customer »), avertit l'équipe en temps réel et par notification.
"""

import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, Optional

try:
    import frappe
    from frappe.utils import add_to_date, get_url, now_datetime
except ImportError:
    frappe = None

SHARE = "Cortex Quote Share"
DEFAULT_DAYS = 14
MAX_DAYS = 60
MAX_MESSAGE = 1000
ACTIONS = {"accept": "Accepted", "decline": "Declined", "changes": "Changes Requested"}
ACTION_TEXT = {
    "Accepted": "a accepté le devis",
    "Declined": "a refusé le devis",
    "Changes Requested": "demande une modification du devis",
}


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def clean_text(value: Optional[str], limit: int = MAX_MESSAGE) -> str:
    text = frappe.utils.strip_html_tags(value or "") if frappe else (value or "")
    return " ".join(text.split())[:limit] if "\n" not in text else text.strip()[:limit]


def build_snapshot(tx, sender_name: str, message: str, valid_until) -> Dict[str, Any]:
    """Ce que le client verra : calculé par le serveur à partir du devis, jamais fourni par le navigateur."""
    from cortex_rental.services import billing

    settings = billing.get_settings(tx.company)
    subtotal = float(tx.subtotal or 0)
    tps = float(tx.tps_amount or 0)
    tvq = float(tx.tvq_amount or 0)
    if not (tps or tvq) and subtotal:
        tps, tvq = billing.compute_taxes(subtotal, settings)
    total = float(tx.grand_total or 0) or round(subtotal + tps + tvq, 2)
    percent = float(settings.get("deposit_percent") or 0)
    deposit = 0.0
    if percent > 0 and subtotal > 0:
        base = round(subtotal * percent / 100.0, 2)
        d_tps, d_tvq = billing.compute_taxes(base, settings)
        deposit = round(base + d_tps + d_tvq, 2)
    company = (
        frappe.db.get_value("Company", tx.company, ["company_name", "company_logo", "default_currency"], as_dict=True)
        or {}
    )
    logo = company.get("company_logo") or ""
    customer = frappe.db.get_value("Customer", tx.customer, "customer_name") or tx.customer
    lines = [
        {
            "item_name": row.item_name or row.item_code,
            "quantity": float(row.qty or 0),
            "daily_rate": float(row.rate or 0),
            "discount_percentage": float(row.discount_percentage or 0),
            "billable_days": float(row.billable_days or tx.billable_days or 0),
            "amount": float(row.amount or 0),
        }
        for row in tx.items or []
    ]
    return {
        "reference": tx.name,
        "company": company.get("company_name") or tx.company,
        "logo": logo if logo.startswith("/files/") else "",
        "customer": customer,
        "project": tx.project_name or "",
        "starts_at": str(tx.starts_at),
        "ends_at": str(tx.ends_at),
        "billable_days": float(tx.billable_days or 0),
        "lines": lines,
        "subtotal": subtotal,
        "tps": tps,
        "tvq": tvq,
        "total": total,
        "currency": company.get("default_currency") or "CAD",
        "deposit_percent": percent,
        "deposit_total": deposit,
        "prepared_by": sender_name,
        "message": message,
        "valid_until": str(valid_until),
    }


def create_share(
    tx,
    channel: str,
    sender: str,
    recipient_email: str = "",
    recipient_name: str = "",
    message: str = "",
    valid_days: int = DEFAULT_DAYS,
) -> Dict[str, Any]:
    """Crée le lien (et envoie le courriel si demandé). `tx` est déjà vérifié : société et droits."""
    if channel not in ("Link", "Email"):
        frappe.throw("Choisissez « Lien à copier » ou « Courriel ».", frappe.ValidationError)
    if tx.rental_state != "Quote":
        frappe.throw("Seul un devis peut être partagé avec le client.", frappe.ValidationError)
    if not (tx.items or []) or float(tx.subtotal or 0) <= 0:
        frappe.throw("Ajoutez du matériel au devis avant de le partager.", frappe.ValidationError)
    days = max(1, min(int(valid_days or DEFAULT_DAYS), MAX_DAYS))
    email = (recipient_email or "").strip()
    if channel == "Email":
        if not email or not frappe.utils.validate_email_address(email):
            frappe.throw("Saisissez une adresse courriel valide pour envoyer le devis.", frappe.ValidationError)
    message = clean_text(message)
    expires = add_to_date(now_datetime(), days=days)
    sender_name = frappe.db.get_value("User", sender, "full_name") or sender
    snapshot = build_snapshot(tx, sender_name, message, expires)
    token = new_token()
    doc = frappe.get_doc(
        {
            "doctype": SHARE,
            "company": tx.company,
            "rental_transaction": tx.name,
            "customer_name": snapshot["customer"],
            "status": "Active",
            "channel": channel,
            "expires_at": expires,
            "recipient_name": clean_text(recipient_name, 140),
            "recipient_email": email if channel == "Email" else "",
            "message": message,
            "rental_version": int(tx.version or 1),
            "token_hash": hash_token(token),
            "snapshot_json": json.dumps(snapshot, ensure_ascii=False),
        }
    )
    doc.flags.from_quote_share = True
    doc.insert(ignore_permissions=True)
    url = get_url(f"/devis/{token}")
    sent = False
    if channel == "Email":
        sent = _send_email(doc, snapshot, url, sender)
        frappe.db.set_value(
            SHARE, doc.name, {"email_status": "Sent" if sent else "Failed", "sent_at": now_datetime() if sent else None}
        )
    _audit(
        tx.company,
        "Human",
        sender,
        "cortex.quote.shared",
        tx.name,
        {"share": doc.name, "channel": channel, "email_sent": sent},
    )
    return {"name": doc.name, "url": url, "channel": channel, "email_sent": sent, "expires_at": str(expires)}


def _send_email(doc, snapshot: Dict[str, Any], url: str, sender: str) -> bool:
    try:
        frappe.sendmail(
            recipients=[doc.recipient_email],
            reply_to=sender if sender not in ("Administrator", "Guest") else None,
            subject=f"Votre devis de {snapshot['company']}",
            template="cortex_quote_share",
            args={
                "recipient_name": doc.recipient_name,
                "company": snapshot["company"],
                "customer": snapshot["customer"],
                "sender_name": snapshot["prepared_by"],
                "message": snapshot["message"],
                "total": frappe.utils.fmt_money(snapshot["total"], currency=snapshot["currency"]),
                "valid_until": frappe.utils.format_date(snapshot["valid_until"][:10]),
                "link": url,
            },
            delayed=False,
        )
        return True
    except Exception:
        frappe.clear_messages()
        frappe.log_error(title="Cortex quote email failed")
        return False


def revoke(name: str, company: str, user: str) -> None:
    row = frappe.db.get_value(SHARE, name, ["company", "status", "rental_transaction"], as_dict=True)
    if not row or row.company != company:
        frappe.throw("Lien introuvable.", frappe.PermissionError)
    if row.status != "Active":
        frappe.throw("Ce lien a déjà reçu une réponse ou a été révoqué.", frappe.ValidationError)
    frappe.db.set_value(SHARE, name, "status", "Revoked")
    _audit(company, "Human", user, "cortex.quote.share_revoked", row.rental_transaction, {"share": name})


# ------------------------------------------------------------------ côté client (sans compte)
def _find(token: str, for_update: bool = False):
    token = (token or "").strip()
    if len(token) < 20 or len(token) > 100:
        return None
    digest = hash_token(token)
    name = frappe.db.get_value(SHARE, {"token_hash": digest}, "name")
    if not name:
        return None
    doc = frappe.get_doc(SHARE, name, for_update=for_update)
    return doc if hmac.compare_digest(doc.token_hash or "", digest) else None


def effective_state(doc) -> str:
    """État montré au client : ok | accepted | declined | changes | revoked | expired | outdated."""
    if doc.status == "Accepted":
        return "accepted"
    if doc.status == "Declined":
        return "declined"
    if doc.status == "Changes Requested":
        return "changes"
    if doc.status == "Revoked":
        return "revoked"
    if doc.expires_at and frappe.utils.get_datetime(doc.expires_at) < now_datetime():
        return "expired"
    current = frappe.db.get_value(
        "Cortex Rental Transaction", doc.rental_transaction, ["rental_state", "version"], as_dict=True
    )
    if not current or current.rental_state != "Quote" or int(current.version or 1) != int(doc.rental_version or 1):
        return "outdated"
    return "ok"


def public_view(token: str) -> Dict[str, Any]:
    doc = _find(token)
    if not doc:
        return {"state": "not_found"}
    now = now_datetime()
    frappe.db.set_value(
        SHARE,
        doc.name,
        {
            "view_count": int(doc.view_count or 0) + 1,
            "last_viewed_at": now,
            "first_viewed_at": doc.first_viewed_at or now,
        },
        update_modified=False,
    )
    snapshot = json.loads(doc.snapshot_json or "{}")
    state = effective_state(doc)
    view = {"state": state, "quote": snapshot, "responded_at": str(doc.responded_at or "")}
    if state == "ok":
        view["token_hint"] = doc.name
    return view


def respond(token: str, action: str, message: str = "", responder_name: str = "") -> Dict[str, Any]:
    if action not in ACTIONS:
        frappe.throw("Action inconnue.", frappe.ValidationError)
    doc = _find(token, for_update=True)
    if not doc:
        frappe.throw("Ce lien n'est pas valide.", frappe.DoesNotExistError)
    state = effective_state(doc)
    if state != "ok":
        frappe.throw(_STATE_MESSAGES.get(state, "Ce lien n'accepte plus de réponse."), frappe.ValidationError)
    name = clean_text(responder_name, 140)
    text = clean_text(message)
    if action == "accept" and len(name) < 2:
        frappe.throw("Indiquez votre nom pour accepter le devis.", frappe.ValidationError)
    if action == "changes" and len(text) < 3:
        frappe.throw("Décrivez la modification souhaitée.", frappe.ValidationError)
    status = ACTIONS[action]
    frappe.db.set_value(
        SHARE,
        doc.name,
        {"status": status, "responded_at": now_datetime(), "responder_name": name, "response_message": text},
    )
    snapshot = json.loads(doc.snapshot_json or "{}")
    who = name or snapshot.get("customer") or "Le client"
    _audit(
        doc.company,
        "Customer",
        snapshot.get("customer") or who,
        f"cortex.quote.{status.lower().replace(' ', '_')}",
        doc.rental_transaction,
        {"share": doc.name, "responder": name, "message": text},
    )
    _notify_team(doc, status, who, snapshot)
    return {"state": {"Accepted": "accepted", "Declined": "declined", "Changes Requested": "changes"}[status]}


_STATE_MESSAGES = {
    "accepted": "Ce devis a déjà été accepté.",
    "declined": "Ce devis a déjà reçu une réponse.",
    "changes": "Une demande de modification a déjà été envoyée pour ce devis.",
    "revoked": "Ce lien a été désactivé par l'entreprise. Demandez-lui un nouveau lien.",
    "expired": "Ce devis est expiré. Demandez à l'entreprise de vous en envoyer un nouveau.",
    "outdated": "Ce devis a été mis à jour. Demandez à l'entreprise de vous envoyer le lien à jour.",
}


def _audit(company: str, actor_type: str, actor_id: str, action: str, entity: str, detail: Dict[str, Any]) -> None:
    from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event

    log_audit_event(
        company=company,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type="Cortex Rental Transaction",
        entity_id=entity,
        after_state=detail,
    )


def _notify_team(doc, status: str, who: str, snapshot: Dict[str, Any]) -> None:
    """Prévient la personne qui a préparé le devis (notification) et toute l'équipe de la société (temps réel)."""
    text = ACTION_TEXT[status]
    try:
        from cortex_rental.services import team_activity

        owner = frappe.db.get_value("Cortex Rental Transaction", doc.rental_transaction, "owner")
        if owner and owner not in ("Administrator", "Guest"):
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": owner,
                    "type": "Alert",
                    "subject": f"{who} {text} {doc.rental_transaction}",
                    "document_type": "Cortex Rental Transaction",
                    "document_name": doc.rental_transaction,
                }
            ).insert(ignore_permissions=True)
        team_activity.publish_company_activity(
            doc.company,
            {
                "actor": who,
                "text": text,
                "entity_type": "Cortex Rental Transaction",
                "entity_id": doc.rental_transaction,
            },
        )
    except Exception:
        frappe.log_error(title="Cortex quote response notification failed")
