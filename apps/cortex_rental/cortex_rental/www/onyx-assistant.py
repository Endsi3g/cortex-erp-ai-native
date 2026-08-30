"""
Controller for www/onyx-assistant.html — embeds the official Onyx
<onyx-chat-widget> web component inside a Frappe Desk-adjacent page, so
operators reach the Onyx assistant without leaving Cortex. Onyx itself
still runs as a fully separate self-hosted service (see
infra/onyx/README.md) — this page only embeds its client-side widget,
which talks to that backend directly over HTTPS.

Security notes (see infra/onyx/README.md for the full rationale):
- `onyx_backend_url` / `onyx_widget_api_key` come from site_config.json
  (frappe.conf), never from a Python env var or anything committed to
  git — standard Frappe practice for per-site secrets.
- The widget's own docs are explicit that its api-key is visible in
  client-side page source. It MUST be a limited-scope, chat-only Onyx
  API key — never a full-access one. This page cannot enforce that on
  the Onyx side; it's an operational requirement documented in
  infra/onyx/README.md.
- Human-staff only: Guest sessions get no context and the template
  renders a "not configured" message instead of the widget.
"""

try:
    import frappe
except ImportError:
    frappe = None

no_cache = 1


def get_context(context):
    context.no_cache = 1

    if not frappe or frappe.session.user == "Guest":
        context.onyx_configured = False
        return context

    backend_url = frappe.conf.get("onyx_backend_url")
    widget_api_key = frappe.conf.get("onyx_widget_api_key")
    # Not verified against a live self-hosted Onyx instance in this
    # session — the widget JS bundle's actual served path may differ
    # from this default depending on how the self-hosted deployment
    # exposes it. Override via site_config.json if needed. See
    # infra/onyx/README.md.
    widget_script_url = frappe.conf.get("onyx_widget_script_url") or (
        f"{backend_url}/widget/onyx-widget.js" if backend_url else None
    )

    context.onyx_configured = bool(backend_url and widget_api_key)
    context.onyx_backend_url = backend_url
    context.onyx_widget_api_key = widget_api_key
    context.onyx_widget_script_url = widget_script_url
    # PRD/CHANGELOG decision: Gemini is configured as the default LLM
    # provider for this Onyx deployment via its own Admin Panel
    # (Settings -> LLM Providers) — not something this page configures
    # or can verify; surfaced here only as an informational label.
    context.onyx_default_model_label = frappe.conf.get("onyx_default_model_label", "Gemini (default)")
    return context
