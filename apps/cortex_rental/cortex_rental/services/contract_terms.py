"""Conditions du contrat de location : modèle de départ modifiable par chaque société, consentement et preuves.

Décision de Kael (2026-10-07) : pas d'avis juridique préalable. Avant d'accepter un devis, le client doit **cocher qu'il a
lu et compris les conditions du contrat**; la société peut changer ces conditions à tout moment. Le devis envoyé garde
les conditions telles qu'au moment de l'envoi (instantané) : modifier le modèle ensuite ne change pas un devis déjà
parti. Preuves conservées : version, empreinte SHA-256 du texte, date, nom saisi, empreinte de l'adresse IP et du navigateur.
Le modèle de départ est un point de départ à adapter, pas un avis juridique.
"""

import hashlib
from typing import Any, Dict, Optional

DEFAULT_TERMS = """1. Objet. Le présent contrat encadre la location du matériel indiqué au devis par l'entreprise (le « Locateur ») au client (le « Locataire »), pour la période et au prix indiqués.

2. Réservation et acompte. Le matériel est réservé à la confirmation du Locateur. Un acompte peut être exigé; il est déduit de la facture finale. Un devis accepté ne garantit pas le matériel tant que le Locateur ne l'a pas réservé.

3. Utilisation. Le Locataire utilise le matériel avec soin, conformément aux instructions du fabricant, aux fins prévues et dans le respect des lois. Il ne le prête, ne le sous-loue ni ne le modifie sans l'accord écrit du Locateur.

4. Garde et risques. Dès la sortie du matériel, le Locataire en a la garde et en assume les risques (perte, vol, dommages) jusqu'à son retour et sa vérification par le Locateur. Le Locataire est responsable de l'assurance du matériel loué pendant cette période, sauf entente contraire écrite.

5. Retour. Le matériel est retourné complet, propre et en bon état, à la date et à l'heure prévues. Un retour tardif peut entraîner des frais de location supplémentaires selon le tarif du Locateur.

6. Dommages et pertes. Le matériel abîmé est facturé au coût de réparation estimé; le matériel perdu ou non retourné est facturé à sa valeur de remplacement, taxes en sus.

7. Annulation. Une annulation ou une modification doit être demandée au Locateur. Les frais d'annulation, s'il y en a, sont ceux indiqués par le Locateur au moment de la réservation.

8. Paiement. Le prix est payable selon les modalités indiquées au devis; les taxes applicables (TPS, TVQ) s'ajoutent. Tout solde impayé à l'échéance peut porter intérêt selon la loi.

9. Acceptation. En cochant la case de confirmation et en inscrivant son nom, le Locataire déclare avoir lu et compris les présentes conditions et les accepter. Cette acceptation vaut signature électronique du contrat.

10. Droit applicable. Le contrat est régi par les lois du Québec; les tribunaux du district du Locateur sont compétents.
"""

MAX_TERMS = 20000


def terms_text(configured: Optional[str]) -> str:
    """Le texte des conditions de la société, sinon le modèle de départ de Cortex."""
    text = (configured or "").replace("\r\n", "\n").strip()
    return text[:MAX_TERMS] if text else DEFAULT_TERMS.strip()


def terms_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def snapshot_terms(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pur : ce qui est figé dans le devis envoyé (texte, version, empreinte, exigence de consentement)."""
    row = row or {}
    text = terms_text(row.get("contract_terms"))
    required = row.get("contract_require_consent")
    return {
        "terms_text": text,
        "terms_version": int(row.get("contract_terms_version") or 1),
        "terms_hash": terms_hash(text),
        # Sans réglage enregistré, le consentement est exigé (défaut de la société).
        "terms_required": True if required is None else bool(int(required)),
    }


def technical_proof(ip: str, user_agent: str, token_hash: str) -> str:
    """Empreinte de l'adresse IP et du navigateur (jamais en clair), liée au jeton du devis."""
    raw = f"{ip or ''}|{(user_agent or '')[:200]}|{token_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_acceptance(snapshot: Dict[str, Any], accepted: Any) -> Optional[str]:
    """Message d'erreur si le consentement manque, sinon `None`. Les devis envoyés avant cette fonction n'en exigent pas."""
    if not snapshot.get("terms_required"):
        return None
    if str(accepted).lower() in ("1", "true", "on", "yes"):
        return None
    return "Confirmez que vous avez lu et compris les conditions du contrat avant d'accepter."
