"""Mon compte : toutes les actions s'appliquent à la personne connectée (voir services/account.py)."""

try:
    import frappe
    from frappe.rate_limiter import rate_limit
except ImportError:
    frappe = None

from cortex_rental.services import account, account_insights, defense


def _me():
    from cortex_rental.permissions.agent_scopes import get_company_context

    return account._user(), get_company_context()


if frappe:

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_account():
        return account.get_account()

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("profile", 60)
    def update_profile(first_name: str = "", last_name: str = "", mobile_no: str = ""):
        return account.update_profile(first_name, last_name, mobile_no)

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("photo", 30)
    def update_photo(file_url: str = ""):
        return account.update_photo(file_url)

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @rate_limit(limit=10, seconds=60 * 60)
    def change_password(old_password: str = "", new_password: str = ""):
        return account.change_password(old_password, new_password)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def list_sessions():
        return account.list_sessions()

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("sign_out", 60)
    def sign_out_session(device_id: str = ""):
        return account.sign_out_session(device_id)

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("sign_out_all", 30)
    def sign_out_other_sessions():
        return account.sign_out_other_sessions()

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    @defense.limit_user("notif", 120)
    def update_notifications(values: str = "{}"):
        return account.update_notifications(defense.json_object(values))

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def my_activity(limit: int = 15):
        return account.my_activity(limit)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def ai_usage():
        return account.ai_usage()

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def stats(period: str = "30"):
        user, company = _me()
        return account_insights.stats(user, company, period)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def history(
        category: str = "", period: str = "90", limit: int = 30, offset: int = 0, scope: str = "me", kind: str = ""
    ):
        user, company = _me()
        return account_insights.history(user, company, category, period, limit, offset, scope, kind)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def todo():
        user, company = _me()
        return {"items": account_insights.todo(user, company)}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def my_approvals():
        user, company = _me()
        return account_insights.my_approvals(user, company)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def login_history(limit: int = 25):
        return account_insights.login_history(account._user(), limit)

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def inbox(limit: int = 30):
        return account_insights.inbox(account._user(), limit)

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def mark_all_read():
        return {"marked": account_insights.mark_all_read(account._user())}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def preferences():
        return account_insights.preferences(account._user())

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def update_preferences(values: str = "{}"):
        return account_insights.update_preferences(account._user(), defense.json_object(values))

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def company_overview():
        from cortex_rental.services import administration

        user, company = _me()
        return {
            "role": account_insights.role_summary(user),
            "rights": account_insights.rights(user),
            "team": account_insights.team_roster(company, user, administration.can_manage_team(user)),
            "can_manage_team": bool(administration.can_manage_team(user)),
        }
