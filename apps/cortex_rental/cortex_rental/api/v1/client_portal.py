"""Portail client (sans compte) : calendrier du matériel et dépôt d'une demande. Règles : services/client_portal.py.

Chaque appel est limité par adresse IP (`rate_limit`) et par société (plafond quotidien); les erreurs de règle sont
des messages en français affichables tels quels."""

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.services import client_portal, defense

if frappe:

    @frappe.whitelist(allow_guest=True, methods=["GET"])
    @defense.safe_input
    @rate_limit(limit=240, seconds=60 * 60)
    def portal_calendar(slug: str = "", starts: str = "", ends: str = "", search: str = ""):
        """Statuts par jour du matériel (libre, en partie réservé, complet) : aucune quantité, aucun client."""
        return client_portal.public_calendar(slug, starts, ends, search)

    @frappe.whitelist(allow_guest=True, methods=["POST"])
    @defense.safe_input
    @rate_limit(limit=10, seconds=60 * 60)
    def submit_portal_request(
        slug: str = "",
        name: str = "",
        email: str = "",
        phone: str = "",
        organisation: str = "",
        project: str = "",
        starts: str = "",
        ends: str = "",
        items: str = "",
        message: str = "",
        consent: str = "",
        website: str = "",
    ):
        """Dépose une demande de location : elle arrive à l'équipe comme demande entrante, sans rien réserver."""
        return client_portal.submit_request(
            slug,
            {
                "name": name,
                "email": email,
                "phone": phone,
                "organisation": organisation,
                "project": project,
                "starts": starts,
                "ends": ends,
                "items": items,
                "message": message,
                "consent": consent,
                "website": website,
            },
        )
