"""Mon compte : toutes les actions s'appliquent à la personne connectée (voir services/account.py)."""

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.services import account

if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_account():
        return account.get_account()

    @frappe.whitelist(methods=["POST"])
    def update_profile(first_name: str = "", last_name: str = "", mobile_no: str = ""):
        return account.update_profile(first_name, last_name, mobile_no)

    @frappe.whitelist(methods=["POST"])
    def update_photo(file_url: str = ""):
        return account.update_photo(file_url)

    @frappe.whitelist(methods=["POST"])
    @rate_limit(limit=10, seconds=60 * 60)
    def change_password(old_password: str = "", new_password: str = ""):
        return account.change_password(old_password, new_password)

    @frappe.whitelist(methods=["GET"])
    def list_sessions():
        return account.list_sessions()

    @frappe.whitelist(methods=["POST"])
    def sign_out_other_sessions():
        return account.sign_out_other_sessions()

    @frappe.whitelist(methods=["POST"])
    def update_notifications(values: str = "{}"):
        return account.update_notifications(frappe.parse_json(values) or {})

    @frappe.whitelist(methods=["GET"])
    def my_activity(limit: int = 15):
        return account.my_activity(limit)

    @frappe.whitelist(methods=["GET"])
    def ai_usage():
        return account.ai_usage()
