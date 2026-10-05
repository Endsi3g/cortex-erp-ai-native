import json
from typing import Optional

try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None

from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event
from cortex_rental.labels import approval_label


APPROVER_ROLES = {"System Manager", "Administrator", "Rental Manager", "Cortex Account Reviewer"}


def other_approvers(company: str, requester: str) -> list:
    """Personnes actives de la société, autres que le demandeur, qui ont un rôle d'approbation."""
    if not frappe:
        return []
    members = frappe.get_all(
        "User Permission", filters={"allow": "Company", "for_value": company}, pluck="user", distinct=True
    )
    found = []
    for user in members:
        if user in (requester, "Administrator", "Guest"):
            continue
        if not frappe.db.get_value("User", user, "enabled"):
            continue
        if APPROVER_ROLES.intersection(frappe.get_roles(user)):
            found.append(user)
    return found


def sole_approver_may_self_approve(company: str, requester: str) -> bool:
    """Une seule personne autorisée (le demandeur) : sans cette règle, l'approbation resterait bloquée à jamais.

    Réglable par société (« Permettre au seul approbateur de décider de ses propres demandes », activé par défaut).
    La décision est inscrite au journal d'audit comme une auto-approbation.
    """
    if not frappe:
        return False
    flag = frappe.db.get_value("Cortex Finance Settings", {"company": company}, "allow_sole_approver_self_approval")
    if flag is not None and str(flag) in ("0", ""):
        return False
    return not other_approvers(company, requester)


class ApprovalRequest(Document):
    """
    Supervision queue entity for sensitive AI agent actions.
    Enforces that agents can never approve their own or any approval requests.
    """

    def validate(self):
        """A decision is only valid through approve() / reject(): a plain form save can never change it."""
        if not frappe:
            return
        if self.is_new():
            if self.status != "Pending":
                frappe.throw("Une demande d'approbation est toujours créée « En attente ».", frappe.ValidationError)
            return
        if getattr(self.flags, "decision_in_progress", False):
            return
        before = frappe.db.get_value(
            self.doctype, self.name, ["status", "decided_by", "decided_at", "decision_reason"], as_dict=True
        )
        if before and (
            before.status != self.status
            or (before.decided_by or None) != (self.decided_by or None)
            or (before.decision_reason or None) != (self.decision_reason or None)
        ):
            frappe.throw(
                "Une décision se prend seulement avec « Approuver » ou « Refuser ».",
                frappe.PermissionError,
            )

    @staticmethod
    def _assert_human_decider(doc) -> None:
        if not frappe:
            return
        user_roles = frappe.get_roles(frappe.session.user)
        if "Agent Service Account" in user_roles or getattr(frappe.flags, "in_agent_context", False):
            frappe.throw("Un agent ne peut jamais décider d'une demande.", frappe.PermissionError)
        if doc.status != "Pending":
            frappe.throw(
                f"Impossible de décider d'une demande au statut « {approval_label(doc.status)} ».",
                frappe.ValidationError,
            )

    def approve(self, reason: Optional[str] = None):
        if frappe:
            current_user = frappe.session.user
            user_roles = frappe.get_roles(current_user)

            # Strict Agent Gate: Agents can never approve
            if "Agent Service Account" in user_roles or getattr(frappe.flags, "in_agent_context", False):
                frappe.throw(
                    "Un agent ne peut jamais approuver une demande.",
                    frappe.PermissionError,
                )

            self_approved = False
            if self.requested_by_type == "Human" and self.requested_by_id == current_user:
                if not sole_approver_may_self_approve(self.company, current_user):
                    frappe.throw(
                        "La personne qui soumet une demande ne peut pas l’approuver elle-même : une autre personne "
                        "autorisée de votre société doit la décider.",
                        frappe.PermissionError,
                    )
                self_approved = True

            if self.status != "Pending":
                frappe.throw(
                    f"Impossible d'approuver une demande au statut « {approval_label(self.status)} ».",
                    frappe.ValidationError,
                )

            self.flags.decision_in_progress = True
            self.status = "Approved"
            self.decided_by = current_user
            self.decision_reason = reason
            self.decided_at = frappe.utils.now_datetime()
            self.save()

            # Execute the approved mutation now, as the authenticated human
            # approver — never deferred to a later, unaudited step.
            self._execute_approved_action()

            log_audit_event(
                company=self.company,
                actor_type="Human",
                actor_id=current_user,
                action="rental.approval.approved",
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                after_state={
                    "status": "Approved",
                    "decision_reason": reason,
                    **(
                        {"self_approved": True, "note": "Seule personne autorisée de la société"}
                        if self_approved
                        else {}
                    ),
                },
            )
        else:
            self.status = "Approved"

    def _execute_approved_action(self):
        """
        Perform the actual business mutation this request was approved
        for. Re-derives the target state from the structured
        `proposed_payload` (preferred) or the `action` identifier, then
        calls `transition_to()` so the same state-machine preconditions
        (customer account, insurance, payment) and audit trail apply as
        any other transition — approval never bypasses them.
        """
        if not frappe:
            return

        if self.entity_type == "Cortex Rental Transaction":
            target_state = self._resolve_target_rental_state()
            if not target_state:
                return
            txn = frappe.get_doc("Cortex Rental Transaction", self.entity_id)
            txn.transition_to(target_state, reason=f"Approved via {self.name}")

        elif self.entity_type == "Sales Order" and self.action == "rental.quote.transition_to_reservation":
            so = frappe.get_doc("Sales Order", self.entity_id)
            so.custom_rental_state = "Reservation"
            so.save()

    def _resolve_target_rental_state(self) -> Optional[str]:
        proposed = self.proposed_payload
        if proposed:
            try:
                proposed = json.loads(proposed) if isinstance(proposed, str) else proposed
            except (ValueError, TypeError):
                proposed = None
            if isinstance(proposed, dict) and proposed.get("rental_state"):
                return proposed["rental_state"]

        if self.action and "transition_to_" in self.action:
            suffix = self.action.rsplit("transition_to_", 1)[-1]
            return suffix.replace("_", " ").title()

        return None

    def withdraw(self, reason: Optional[str] = None):
        """La personne qui a fait la demande la retire (rien n'est exécuté)."""
        if not frappe:
            self.status = "Rejected"
            return
        current_user = frappe.session.user
        self._assert_human_decider(self)
        if not (self.requested_by_type == "Human" and self.requested_by_id == current_user):
            frappe.throw("Seule la personne qui a fait la demande peut la retirer.", frappe.PermissionError)
        text = (reason or "").strip() or "Demande retirée par son auteur"
        self.flags.ignore_permissions = True  # l'auteur est vérifié ci-dessus ; son rôle peut ne pas avoir « écrire »
        self.flags.decision_in_progress = True
        self.status = "Rejected"
        self.decided_by = current_user
        self.decision_reason = f"Retirée : {text}"
        self.decided_at = frappe.utils.now_datetime()
        self.save()
        log_audit_event(
            company=self.company,
            actor_type="Human",
            actor_id=current_user,
            action="rental.approval.withdrawn",
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            after_state={"status": "Rejected", "decision_reason": self.decision_reason},
        )

    def reject(self, reason: str):
        if not reason or not reason.strip():
            if frappe:
                frappe.throw("Un motif de refus est obligatoire.", frappe.ValidationError)
            else:
                raise ValueError("Un motif de refus est obligatoire.")

        if frappe:
            self._assert_human_decider(self)
            current_user = frappe.session.user
            if self.requested_by_type == "Human" and self.requested_by_id == current_user:
                frappe.throw(
                    "Vous avez fait cette demande : utilisez « Retirer ma demande » pour l'annuler.",
                    frappe.PermissionError,
                )
            self.flags.decision_in_progress = True
            self.status = "Rejected"
            self.decided_by = current_user
            self.decision_reason = reason
            self.decided_at = frappe.utils.now_datetime()
            self.save()

            log_audit_event(
                company=self.company,
                actor_type="Human",
                actor_id=current_user,
                action="rental.approval.rejected",
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                after_state={"status": "Rejected", "decision_reason": reason},
            )
        else:
            self.status = "Rejected"
