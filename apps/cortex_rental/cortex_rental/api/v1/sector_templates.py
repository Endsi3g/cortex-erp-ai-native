"""Modèles de secteur — page « Modèles de secteur » (Administration).

Propriétaire seulement. Rien n'est écrit ici : `propose` valide et garde une proposition (aperçu); l'application et
l'annulation passent par `chat.decide_action` et `chat.undo_action`, le même moteur d'actions que l'assistant
(approbation, audit, annulation). Voir services/sector_templates.py et ADR-011.
"""

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services import defense, sector_templates

if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def list_templates():
        """Les modèles disponibles et l'état du site (catégories actuelles), pour la page."""
        require_human_staff_role()
        sector_templates.require_owner_or_throw()
        return {"data": {"templates": sector_templates.catalog(), "categories": sector_templates.categories()}}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("ai_action_decide", 60)
    def propose(template: str = ""):
        """Calcule l'aperçu de l'application d'un modèle et le garde comme proposition (carte d'action)."""
        require_human_staff_role()
        company = get_company_context()
        from cortex_rental.services.ai import actions

        try:
            block = actions.propose("apply_sector_template", {"template": template}, company, frappe.session.user)
        except actions.ActionError as exc:
            frappe.throw(str(exc), frappe.ValidationError)
        return {"data": block, "meta": {"company": company}}
