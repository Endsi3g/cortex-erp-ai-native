"""An access request: a person asks for a Cortex workspace for their company.

Life cycle: Pending Verification -> (email link) Pending Approval -> Provisioned | Rejected.
Passwords are never handled here: the owner sets theirs through Frappe's own reset link once the
company exists. All logic lives in cortex_rental.services.access_requests.
"""

try:
    import frappe
    from frappe.model.document import Document
except ImportError:  # unit tests without a bench
    frappe = None

    class Document:
        pass


class CortexSignupRequest(Document):
    def validate(self):
        from cortex_rental.services.signup_rules import normalize_email

        self.email = normalize_email(self.email)
        self.full_name = (self.full_name or "").strip()
        self.company_name = (self.company_name or "").strip()

    @frappe.whitelist(methods=["POST"])
    def approve(self):
        from cortex_rental.services.access_requests import approve_request

        return approve_request(self.name)

    @frappe.whitelist(methods=["POST"])
    def resend_verification(self):
        from cortex_rental.services.access_requests import resend_verification_as_admin

        return resend_verification_as_admin(self.name)

    @frappe.whitelist(methods=["POST"])
    def reject(self, reason: str = ""):
        from cortex_rental.services.access_requests import reject_request

        return reject_request(self.name, reason)
