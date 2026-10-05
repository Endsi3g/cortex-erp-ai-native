"""Présence et activité de l'équipe (lecture seule, limitée à la société de la personne connectée)."""

try:
    import frappe
    from frappe.utils import now_datetime
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import team_activity

if frappe:

    @frappe.whitelist(methods=["POST"])
    def ping(where: str = ""):
        """Battement de cœur : indique que la personne est à l'écran (une écriture sur sa propre fiche seulement).

        `where` est le nom de l'écran affiché (« Disponibilité », « Location CR-TRX-… »). Il n'est gardé que 3 minutes en
        mémoire, pour l'infobulle « en ligne » de l'équipe de la même société ; il n'est jamais écrit dans un dossier."""
        require_human_staff_role()
        frappe.db.set_value("User", frappe.session.user, "last_active", now_datetime(), update_modified=False)
        team_activity.remember_where(frappe.session.user, where)
        return {"ok": True}

    @frappe.whitelist(methods=["GET"])
    def team_activity_snapshot():
        require_human_staff_role()
        company = get_company_context()
        return team_activity.team_snapshot(company, frappe.session.user)
