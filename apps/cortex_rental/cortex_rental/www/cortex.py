"""
Serves the Cortex single-page app (built from apps/cortex_rental/frontend
into public/frontend; vite copies the built index.html to www/cortex.html).

Only authenticated sessions get the app shell. Everything the SPA shows
afterwards comes from permission-checked whitelisted APIs; the boot data
below carries no business data, only what the client needs to call them.
"""

try:
    import frappe
except ImportError:
    frappe = None

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(frappe.request.path)
        raise frappe.Redirect

    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()

    context.no_cache = 1
    context.boot = {
        "csrf_token": csrf_token,
        "cortex_user": frappe.session.user,
        "site_name": frappe.local.site,
    }
    return context
