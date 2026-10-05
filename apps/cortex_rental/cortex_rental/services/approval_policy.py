"""Règle d'approbation « le seul approbateur décide de ses propres demandes » : désactivée par défaut, activée
par la société elle-même après avoir lu ce que cela change (bénéfices et dangers).

Le texte affiché vient d'ici (une seule source) : la fenêtre d'explication, la page Société et rôles et le message de
la liste des approbations disent la même chose.
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

FIELD = "allow_sole_approver_self_approval"

WHAT = (
    "Par défaut, la personne qui fait une demande d'approbation ne peut pas la décider : une deuxième personne autorisée "
    "doit la confirmer. Cette règle protège la société contre les erreurs et les abus."
)
BENEFITS = [
    "Une société d'une seule personne peut confirmer ses contrats sans attendre quelqu'un d'autre.",
    "Chaque décision reste inscrite au journal d'audit, marquée « auto-approbation », et se retrouve dans « Mes approbations ».",
    "La règle des deux personnes revient d'elle-même dès qu'une autre personne autorisée s'ajoute à l'équipe.",
]
DANGERS = [
    "Plus de second regard : une erreur (client sans assurance, acompte oublié, mauvais prix) passe sans être vue par quelqu'un d'autre.",
    "Si votre compte est utilisé par une autre personne (mot de passe volé, ordinateur laissé ouvert), elle peut confirmer des contrats à votre place.",
    "Un assureur, un comptable ou un auditeur peut exiger la séparation des tâches : vérifiez avant d'activer.",
    "Les contrats confirmés ainsi engagent du matériel de valeur : la responsabilité repose entièrement sur vous.",
]
ADVICE = (
    "Activez-la seulement si vous êtes vraiment seul à pouvoir approuver. Si vous avez un associé ou un employé de confiance, "
    "ajoutez-le dans « Équipe et rôles » avec le profil Gestionnaire : c'est plus sûr, et gratuit."
)


def _flag(company: str) -> bool:
    value = frappe.db.get_value("Cortex Finance Settings", {"company": company}, FIELD)
    return bool(value) and str(value) not in ("0", "")


def get_policy(company: str, user: str) -> Dict[str, Any]:
    from cortex_rental.cortex_rental.doctype.approval_request.approval_request import other_approvers
    from cortex_rental.services import administration

    sole = not other_approvers(company, user)
    can_manage = bool(administration.can_manage_team(user))
    enabled = _flag(company)
    return {
        "enabled": enabled,
        "sole_approver": sole,
        "can_manage": can_manage,
        "applies_now": enabled and sole,
        "what": WHAT,
        "benefits": BENEFITS,
        "dangers": DANGERS,
        "advice": ADVICE,
    }


def set_self_approval(company: str, user: str, enabled: bool, acknowledged: bool) -> Dict[str, Any]:
    from cortex_rental.services import administration
    from cortex_rental.services.audit import AuditService

    if not administration.can_manage_team(user):
        frappe.throw("Seul le propriétaire de la société peut changer cette règle.", frappe.PermissionError)
    if enabled and not acknowledged:
        frappe.throw("Confirmez que vous avez compris les risques avant d'activer cette règle.", frappe.ValidationError)
    if not frappe.db.exists("Cortex Finance Settings", {"company": company}):
        from cortex_rental.services import billing

        billing.ensure_settings(company)
    before = _flag(company)
    frappe.db.set_value("Cortex Finance Settings", {"company": company}, FIELD, 1 if enabled else 0)
    AuditService.record_mutation(
        company=company,
        action="cortex.approvals.self_approval_changed",
        entity_type="Cortex Finance Settings",
        entity_id=company,
        before_state={"enabled": before},
        after_state={"enabled": bool(enabled), "acknowledged": bool(acknowledged)},
    )
    return get_policy(company, user)
