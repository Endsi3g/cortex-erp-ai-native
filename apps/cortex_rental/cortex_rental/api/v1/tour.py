"""Visite guidée — état « déjà vue » gardé côté serveur, par personne (Cortex User Preference.tour_seen_at).

La visite elle-même est entièrement dans le navigateur (public/js/cortex_tour.js) : aucun modèle d'IA. Ce point d'accès
n'écrit que la ligne de préférences de la personne connectée.
"""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services import defense


def tour_seen(user: str) -> bool:
    """Vrai si cette personne a déjà vu (ou passé) la visite guidée."""
    if not frappe or not user or user == "Guest":
        return True  # jamais de visite pour un visiteur
    try:
        return bool(frappe.db.get_value("Cortex User Preference", user, "tour_seen_at"))
    except Exception:
        return True  # en cas de doute, ne pas imposer la visite


def mark_seen_for(user: str) -> None:
    now = frappe.utils.now_datetime()
    if frappe.db.exists("Cortex User Preference", user):
        frappe.db.set_value("Cortex User Preference", user, "tour_seen_at", now)
    else:
        frappe.get_doc({"doctype": "Cortex User Preference", "user": user, "tour_seen_at": now}).insert(
            ignore_permissions=True
        )
    # Frappe garde le « boot » de chaque personne en cache : on le retire pour que le prochain chargement relise l'état.
    # (La visite confirme aussi auprès du serveur avant de se lancer : voir get_state.)
    frappe.cache.hdel("bootinfo", user)


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_state():
        """État lu à chaud (le « boot » de Frappe est mis en cache et peut garder une valeur périmée)."""
        return {"data": {"seen": tour_seen(frappe.session.user)}}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("tour_mark_seen", 30)
    def mark_seen():
        """Note que la personne connectée a vu la visite guidée (terminée ou passée)."""
        if frappe.session.user == "Guest":
            frappe.throw("Connexion requise.", frappe.PermissionError)
        mark_seen_for(frappe.session.user)
        return {"data": {"seen": True}}
