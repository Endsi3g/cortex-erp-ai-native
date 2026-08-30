try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexChatSession(Document):
    """
    One (user, company, agent_profile) conversation with the Cortex
    Copilot. Only services/chat_session.py should create/update these —
    see docs/design-system.md's chat architecture ("Cortex Chat
    Gateway") for why the browser never gets to choose company, agent,
    or model directly.
    """

    def validate(self):
        if not frappe:
            return
        # Defense in depth: even if some future code path bypasses
        # ChatSessionService, a session can never be created for a
        # Company the current user isn't authorized for — the same
        # invariant every other Company-scoped doctype in this app
        # enforces in its own validate()/permission_query_conditions.
        from cortex_rental.permissions.agent_scopes import get_allowed_companies

        if self.company not in get_allowed_companies(self.user):
            frappe.throw(
                "Multi-Tenant Error: this session's Company is not authorized for this user.",
                frappe.PermissionError,
            )
