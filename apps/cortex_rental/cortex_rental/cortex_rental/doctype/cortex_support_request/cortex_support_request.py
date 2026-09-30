import frappe
from frappe import _
from frappe.model.document import Document


class CortexSupportRequest(Document):
    def before_insert(self):
        self.requested_by = frappe.session.user
        if not self.company:
            try:
                from cortex_rental.permissions.agent_scopes import get_company_context

                self.company = get_company_context()
            except Exception:
                self.company = frappe.defaults.get_user_default("Company") or None

    def after_insert(self):
        """Prévient l'équipe Cortex (administrateurs du site) dans leurs notifications, en temps réel."""
        admins = frappe.get_all(
            "Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent", distinct=True
        )
        for admin in admins:
            if admin in ("Administrator", frappe.session.user) or not frappe.db.get_value("User", admin, "enabled"):
                continue
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": admin,
                    "type": "Alert",
                    "subject": _("Nouvelle demande de support : {0}").format(self.subject),
                    "document_type": self.doctype,
                    "document_name": self.name,
                    "from_user": frappe.session.user,
                }
            ).insert(ignore_permissions=True)
