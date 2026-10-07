"""Paiement en ligne de l'acompte : Stripe Checkout, avec la clé de la société (jamais une clé de plateforme partagée).

Rien n'est considéré payé tant que Stripe n'a pas confirmé par un webhook **signé** ; le retour du navigateur ne prouve rien.
Les prix et les frais de Stripe sont dans docs/architecture/COUTS_API.md. Sans clé, le portail n'offre que les
instructions de paiement manuel.
"""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

API = "https://api.stripe.com/v1"
TOLERANCE_SECONDS = 300


class PaymentError(RuntimeError):
    """Erreur du fournisseur de paiement; le message est sûr à afficher."""


def checkout_form(
    amount_cents: int, currency: str, description: str, success_url: str, cancel_url: str, metadata: Dict[str, str]
) -> Dict[str, str]:
    form = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": str(int(amount_cents)),
        "line_items[0][price_data][product_data][name]": description[:250],
        "payment_intent_data[description]": description[:250],
    }
    for key, value in metadata.items():
        form[f"metadata[{key}]"] = str(value)
        form[f"payment_intent_data[metadata][{key}]"] = str(value)
    return form


def create_checkout_session(
    secret_key: str, form: Dict[str, str], idempotency_key: str, timeout: int = 30
) -> Dict[str, Any]:
    if not secret_key:
        raise PaymentError("Le paiement en ligne n'est pas configuré.")
    request = urllib.request.Request(
        f"{API}/checkout/sessions",
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise PaymentError(
            "Le service de paiement a refusé la demande. Réessayez ou utilisez le paiement manuel."
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PaymentError("Le service de paiement ne répond pas. Réessayez dans un instant.") from exc


def verify_signature(payload: bytes, header: str, secret: str, now: Optional[float] = None) -> bool:
    """Vérifie l'en-tête `Stripe-Signature` (t=<horodatage>,v1=<HMAC-SHA256 de « t.payload »>) et la fraîcheur."""
    if not (payload and header and secret):
        return False
    parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
    stamp = parts.get("t", "")
    signatures = [v for k, v in (i.split("=", 1) for i in header.split(",") if "=" in i) if k == "v1"]
    if not stamp.isdigit() or not signatures:
        return False
    if abs((now if now is not None else time.time()) - int(stamp)) > TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode("utf-8"), f"{stamp}.".encode("utf-8") + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def sign(payload: bytes, secret: str, stamp: Optional[int] = None) -> str:
    """Produit un en-tête de signature valide (tests et développement)."""
    stamp = int(stamp if stamp is not None else time.time())
    digest = hmac.new(secret.encode("utf-8"), f"{stamp}.".encode("utf-8") + payload, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"
