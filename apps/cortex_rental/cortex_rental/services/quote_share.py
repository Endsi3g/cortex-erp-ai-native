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
    from cortex_rental.services import brand, contract_terms

    row_settings = (
        frappe.db.get_value(
            "Cortex Finance Settings",
            tx.company,
            [
                "contract_terms",
                "contract_terms_version",
                "contract_require_consent",
                "portal_tagline",
                "portal_banner_image",
                "portal_accent_color",
            ],
            as_dict=True,
        )
        or {}
    )
    images = {
        p.item_code: brand.public_file(p.image)
        for p in frappe.get_all(
            "Cortex Rental Item Profile",
            filters={"company": tx.company, "item_code": ["in", [r.item_code for r in tx.items]]},
            fields=["item_code", "image"],
        )
    }
    lines = [
        {
            "image": images.get(row.item_code, ""),
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
        "brand": brand.branding(row_settings, company),
        **contract_terms.snapshot_terms(row_settings),
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
    # Le matériel reste retenu tant que le lien est valide (revérifié sous verrou ; jamais raccourci).
    hold = {"status": "", "note": ""}
    try:
        from cortex_rental.services import holds

        hold = holds.extend_to(tx, expires)
    except Exception:
        frappe.log_error(title="Cortex quote hold extension failed")
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
    return {
        "name": doc.name,
        "url": url,
        "channel": channel,
        "email_sent": sent,
        "expires_at": str(expires),
        "hold_status": hold.get("status") or "",
        "hold_note": hold.get("note") or "",
    }


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
    if state == "accepted":
        view["payment"] = payment_view(doc, snapshot)
    if state == "ok":
        view["token_hint"] = doc.name
    return view


def respond(
    token: str,
    action: str,
    message: str = "",
    responder_name: str = "",
    confirmed: int = 0,
    terms_accepted: int = 0,
    proof: str = "",
) -> Dict[str, Any]:
    """`confirmed` : le client a coché la confirmation (accepter, refuser). Sans elle, rien n'est enregistré."""
    if action not in ACTIONS:
        frappe.throw("Action inconnue.", frappe.ValidationError)
    if action in ("accept", "decline") and not int(confirmed or 0):
        frappe.throw("Confirmez votre réponse avant de l'envoyer.", frappe.ValidationError)
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
    snapshot = json.loads(doc.snapshot_json or "{}")
    changes = {"status": status, "responded_at": now_datetime(), "responder_name": name, "response_message": text}
    if action == "accept":
        from cortex_rental.services import contract_terms

        problem = contract_terms.check_acceptance(snapshot, terms_accepted)
        if problem:
            frappe.throw(problem, frappe.ValidationError)
        if snapshot.get("terms_hash"):
            # Preuve du consentement : version et empreinte des conditions affichées, date, empreinte technique.
            changes.update(
                terms_version=int(snapshot.get("terms_version") or 1),
                terms_hash=snapshot["terms_hash"],
                terms_accepted_at=now_datetime(),
                terms_accept_proof=proof,
            )
    frappe.db.set_value(SHARE, doc.name, changes)
    who = name or snapshot.get("customer") or "Le client"
    _audit(
        doc.company,
        "Customer",
        snapshot.get("customer") or who,
        f"cortex.quote.{status.lower().replace(' ', '_')}",
        doc.rental_transaction,
        {
            "share": doc.name,
            "responder": name,
            "message": text,
            **(
                {"terms_version": snapshot.get("terms_version"), "terms_hash": snapshot.get("terms_hash")}
                if action == "accept" and snapshot.get("terms_hash")
                else {}
            ),
        },
    )
    follow = _after_accept(doc, who) if status == "Accepted" else {}
    _notify_team(doc, status, who, snapshot, follow)
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


def company_options(company: str) -> Dict[str, Any]:
    """Réglages de devis et de paiement de la société (les clés restent côté serveur)."""
    from frappe.utils.password import get_decrypted_password

    row = (
        frappe.db.get_value(
            "Cortex Finance Settings",
            company,
            [
                "auto_reserve_on_accept",
                "online_payment_enabled",
                "payment_instructions",
                "accept_cheque",
                "cheque_payable_to",
            ],
            as_dict=True,
        )
        or {}
    )
    secret = webhook = ""
    if row.get("online_payment_enabled"):
        secret = (
            get_decrypted_password("Cortex Finance Settings", company, "stripe_secret_key", raise_exception=False) or ""
        )
        webhook = (
            get_decrypted_password("Cortex Finance Settings", company, "stripe_webhook_secret", raise_exception=False)
            or ""
        )
    return {
        "auto_reserve": bool(row.get("auto_reserve_on_accept")),
        "online_payment": bool(row.get("online_payment_enabled") and secret and webhook),
        "instructions": row.get("payment_instructions") or "",
        "accept_cheque": bool(row.get("accept_cheque")),
        "cheque_payable_to": row.get("cheque_payable_to") or "",
        "secret_key": secret,
        "webhook_secret": webhook,
    }


def _after_accept(doc, who: str) -> Dict[str, Any]:
    """Si la société l'a demandé, réserve le matériel quand le serveur confirme la disponibilité. Sinon, l'équipe réserve."""
    options = company_options(doc.company)
    if not options["auto_reserve"]:
        return {"reserved": False, "auto": False}
    previous = frappe.session.user
    point = "cortex_auto_reserve"
    frappe.db.savepoint(point)
    try:
        # Au nom de la personne qui a envoyé le devis : ses droits bornent l'opération, l'audit le dit.
        frappe.set_user(doc.owner)
        tx = frappe.get_doc("Cortex Rental Transaction", doc.rental_transaction)
        tx.transition_to(
            "Reservation",
            reason=f"Réservation automatique : {who} a accepté le devis et la disponibilité est confirmée.",
        )
        frappe.set_user(previous)
        frappe.db.set_value(
            SHARE, doc.name, {"reservation_status": "Reserved", "reservation_note": "Réservé automatiquement."}
        )
        return {"reserved": True, "auto": True}
    except Exception as exc:  # noqa: BLE001 - toute raison (disponibilité, droits, état) renvoie vers l'équipe, rien n'est caché
        frappe.set_user(previous)
        try:
            frappe.db.rollback(save_point=point)
        except Exception:
            # La réservation valide d'abord sous verrou (avec un commit) : le point de reprise peut ne plus exister, et
            # rien n'a été écrit par la réservation refusée.
            pass
        message = str(getattr(exc, "message", None) or exc)[:300]
        frappe.clear_messages()
        frappe.db.set_value(
            SHARE,
            doc.name,
            {
                "reservation_status": "Needs Review",
                "reservation_note": f"Réservation automatique impossible : {message}",
            },
        )
        return {"reserved": False, "auto": True, "note": message}


def _notify_team(doc, status: str, who: str, snapshot: Dict[str, Any], follow: Optional[Dict[str, Any]] = None) -> None:
    """Prévient la personne qui a préparé le devis (notification) et toute l'équipe de la société (temps réel)."""
    follow = follow or {}
    text = ACTION_TEXT[status]
    if status == "Accepted":
        if follow.get("reserved"):
            text += " (matériel réservé automatiquement)"
        elif follow.get("auto"):
            text += " : réservation automatique impossible, à traiter"
        else:
            text += " : à réserver"
    _tell(doc, who, text, doc.rental_transaction if status == "Accepted" and not follow.get("reserved") else "")


def _tell(doc, who: str, text: str, reserve: str = "") -> None:
    """Notification pour la personne qui a préparé le devis + événement en direct (avec bouton « Réserver » si `reserve`)."""
    try:
        from cortex_rental.services import team_activity

        owner = frappe.db.get_value("Cortex Rental Transaction", doc.rental_transaction, "owner")
        from cortex_rental.services import account_insights

        if owner and owner not in ("Administrator", "Guest") and account_insights.wants(owner, "notify_quote_response"):
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": owner,
                    "type": "Alert",
                    "subject": f"{who} {text} — {doc.rental_transaction}",
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
                "reserve": reserve,
            },
        )
    except Exception:
        frappe.log_error(title="Cortex quote response notification failed")


# ------------------------------------------------------------------ paiement de l'acompte
def payment_view(doc, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    options = company_options(doc.company)
    invoice = (
        frappe.db.get_value("Cortex Rental Invoice", doc.deposit_invoice, ["balance", "status"], as_dict=True)
        if doc.deposit_invoice
        else None
    )
    paid = bool(invoice and invoice.status == "Paid") or doc.payment_status == "Paid"
    amount = float(invoice.balance) if invoice and not paid else float(snapshot.get("deposit_total") or 0)
    chosen_cheque = doc.get("payment_method_choice") == "Cheque" and not paid
    return {
        "amount": amount,
        "online": options["online_payment"] and amount > 0 and not paid,
        "cheque": {
            "accepted": bool(options["accept_cheque"] and amount > 0 and not paid and not chosen_cheque),
            "chosen": chosen_cheque,
            "payable_to": options["cheque_payable_to"],
            "reference": doc.deposit_invoice or "",
        },
        "paid": paid,
        "pending": doc.payment_status == "Pending" and not paid and not chosen_cheque,
        "instructions": options["instructions"],
        "needed": bool(snapshot.get("deposit_total")),
    }


def start_payment(token: str) -> Dict[str, Any]:
    """Crée la session de paiement Stripe de l'acompte (facture d'acompte créée au besoin) et renvoie son adresse."""
    from cortex_rental.services import billing, payments

    doc = _find(token, for_update=True)
    if not doc or doc.status != "Accepted":
        frappe.throw("Acceptez d'abord le devis pour payer l'acompte.", frappe.ValidationError)
    options = company_options(doc.company)
    if not options["online_payment"]:
        frappe.throw("Le paiement en ligne n'est pas offert par cette entreprise.", frappe.ValidationError)
    tx = frappe.get_doc("Cortex Rental Transaction", doc.rental_transaction)
    invoice = billing.create_deposit_invoice(tx)
    if not invoice or float(invoice.balance or 0) <= 0:
        frappe.throw("Aucun acompte n'est à payer pour ce devis.", frappe.ValidationError)
    snapshot = json.loads(doc.snapshot_json or "{}")
    cents = int(round(float(invoice.balance) * 100))
    base = get_url(f"/devis/{token}")
    form = payments.checkout_form(
        cents,
        snapshot.get("currency") or "CAD",
        f"Acompte — {snapshot.get('company', '')} — devis {tx.name}",
        base + "?paiement=ok",
        base,
        {"share": doc.name, "invoice": invoice.name, "company": doc.company},
    )
    session = payments.create_checkout_session(options["secret_key"], form, idempotency_key=f"{doc.name}-{cents}")
    frappe.db.set_value(
        SHARE,
        doc.name,
        {"deposit_invoice": invoice.name, "payment_status": "Pending", "payment_session_id": session.get("id", "")},
    )
    return {"url": session.get("url")}


def choose_cheque(token: str) -> Dict[str, Any]:
    """Le client annonce un paiement par chèque : la facture d'acompte est créée (référence à inscrire au chèque) et
    l'équipe est prévenue. Rien n'est marqué payé : l'entreprise enregistre le paiement à la réception du chèque
    (mode « Chèque », sur la facture), ce qui règle aussi l'acompte de cette page."""
    from cortex_rental.services import billing

    doc = _find(token, for_update=True)
    if not doc or doc.status != "Accepted":
        frappe.throw("Acceptez d'abord le devis pour payer l'acompte.", frappe.ValidationError)
    options = company_options(doc.company)
    if not options["accept_cheque"]:
        frappe.throw("Le paiement par chèque n'est pas offert par cette entreprise.", frappe.ValidationError)
    tx = frappe.get_doc("Cortex Rental Transaction", doc.rental_transaction)
    invoice = billing.create_deposit_invoice(tx)
    if not invoice or float(invoice.balance or 0) <= 0:
        frappe.throw("Aucun acompte n'est à payer pour ce devis.", frappe.ValidationError)
    frappe.db.set_value(
        SHARE,
        doc.name,
        {"deposit_invoice": invoice.name, "payment_status": "Pending", "payment_method_choice": "Cheque"},
    )
    who = doc.responder_name or doc.customer_name or "Le client"
    _tell(doc, who, f"annonce un chèque de {float(invoice.balance):.2f} $ pour l'acompte (facture {invoice.name})")
    return {
        "payable_to": options["cheque_payable_to"],
        "amount": float(invoice.balance),
        "reference": invoice.name,
    }


def handle_payment_event(payload: bytes, signature: str) -> Dict[str, Any]:
    """Webhook Stripe : la société est retrouvée par la session, puis la signature est vérifiée avec SON secret."""
    from cortex_rental.services import billing, payments

    try:
        event = json.loads(payload.decode("utf-8"))
        session = (event.get("data") or {}).get("object") or {}
        share_name = (session.get("metadata") or {}).get("share") or ""
    except (ValueError, AttributeError):
        frappe.throw("Requête invalide.", frappe.ValidationError)
    doc = frappe.get_doc(SHARE, share_name) if share_name and frappe.db.exists(SHARE, share_name) else None
    if not doc:
        frappe.throw("Requête invalide.", frappe.ValidationError)
    options = company_options(doc.company)
    if not payments.verify_signature(payload, signature, options["webhook_secret"]):
        frappe.throw("Signature invalide.", frappe.AuthenticationError)
    if event.get("type") != "checkout.session.completed" or session.get("payment_status") != "paid":
        return {"ignored": True}
    if session.get("id") != doc.payment_session_id or not doc.deposit_invoice:
        return {"ignored": True}
    reference = session.get("id")
    if frappe.db.exists("Cortex Rental Payment", {"invoice": doc.deposit_invoice, "reference": reference}):
        return {"duplicate": True}  # Stripe peut renvoyer l'événement : un seul paiement par session
    amount = float(session.get("amount_total") or 0) / 100.0
    billing.record_payment(
        invoice=doc.deposit_invoice,
        amount=amount,
        method="Card",
        reference=reference,
        notes="Acompte payé dans le portail du devis (Stripe).",
        ignore_permissions=True,
    )
    frappe.db.set_value(SHARE, doc.name, "payment_status", "Paid")
    snapshot = json.loads(doc.snapshot_json or "{}")
    _tell(doc, snapshot.get("customer") or "Le client", "a payé l'acompte en ligne")
    _audit(
        doc.company,
        "System",
        "stripe",
        "cortex.quote.deposit_paid",
        doc.rental_transaction,
        {"share": doc.name, "invoice": doc.deposit_invoice, "amount": amount},
    )
    return {"paid": True}
