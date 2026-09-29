import frappe

no_cache = 1


def get_context(context):
    """Boot data for the standalone Cortex app (built by `npm run build:spa` into www/cortex.html).

    The page is served to guests too: the app shows its own sign-in when the session is anonymous.
    Nothing else is injected here; screens read their data through permission-checked `cortex_rental` APIs.
    """
    context.boot = {
        "csrf_token": frappe.sessions.get_csrf_token(),
        "user": frappe.session.user,
    }
