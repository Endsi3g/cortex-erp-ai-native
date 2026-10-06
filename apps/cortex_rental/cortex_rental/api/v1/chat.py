"""
Cortex Chat Gateway — POST /api/method/cortex_rental.api.v1.chat.*

Human-staff-only (require_human_staff_role, same gate as checkin.py) —
this is not part of the agent-facing MCP surface and has no MCP tool.
Every field a client could use to escalate privilege (company, agent,
model, allowed_tool_ids) simply has no place to go: SendMessageRequest
doesn't define those fields and rejects extras (schemas/chat_schemas.py).
"""

from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None

from pydantic import ValidationError

from cortex_rental.services import defense
from cortex_rental.permissions.agent_scopes import (
    require_human_staff_role,
    get_company_context,
)
from cortex_rental.schemas.chat_schemas import SendMessageRequest
from cortex_rental.services.onyx_chat_client import OnyxConfigurationError
from cortex_rental.services.chat_session import (
    ChatSessionService,
    ChatContextPermissionError,
    ChatRateLimitError,
    ChatSessionNotFoundError,
)


class _ModelNotNeeded:
    """Stand-in client for calls that never reach the model (history, sessions): no Onyx configuration required."""

    def send_message(self, *args, **kwargs):  # pragma: no cover - guarded by _service(model=True)
        raise OnyxConfigurationError("Onyx is not configured.")


def _service(model: bool = False) -> ChatSessionService:
    """The chat service. Only sending a message needs the model; reading history never does.

    When the engine is missing its configuration, sending answers with a clear message instead of a server error.
    """
    if not model:
        return ChatSessionService(onyx_client=_ModelNotNeeded())
    try:
        return ChatSessionService()
    except OnyxConfigurationError as exc:
        if frappe:
            frappe.throw(
                "L'assistant IA n'est pas encore configuré sur ce site : un administrateur doit saisir la clé API "
                f"dans les réglages de l'IA. ({exc})",
                frappe.ValidationError,
            )
        raise


def _raise_validation_error(exc: ValidationError) -> None:
    if frappe:
        frappe.throw(f"Demande de conversation invalide : {exc}", frappe.ValidationError)
    raise ValueError(str(exc))


def send_message_handler(payload: Dict[str, Any], user: str, company: str) -> Dict[str, Any]:
    cleaned = {k: v for k, v in payload.items() if k not in ("cmd", "csrf_token", "_")}
    if isinstance(cleaned.get("context"), str):
        if frappe:
            cleaned["context"] = frappe.parse_json(cleaned["context"])
        else:
            import json

            cleaned["context"] = json.loads(cleaned["context"])
    try:
        request = SendMessageRequest.model_validate(cleaned)
    except ValidationError as exc:
        _raise_validation_error(exc)
        return {}  # unreachable when frappe is available; keeps type-checkers happy

    service = _service(model=True)
    try:
        response = service.send_message(
            user=user,
            company=company,
            message=request.message,
            context=request.context.model_dump(),
            chat_session_id=request.chat_session_id,
        )
    except ChatContextPermissionError as exc:
        if frappe:
            frappe.throw(str(exc), frappe.PermissionError)
        raise
    except ChatRateLimitError as exc:
        if frappe:
            frappe.throw(str(exc), frappe.ValidationError)
        raise
    except OnyxConfigurationError as exc:
        if frappe:
            frappe.throw(str(exc), frappe.ValidationError)
        raise

    return response.model_dump(mode="json")


if frappe:

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def create_session():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        page = payload.get("page") or "dashboard"
        locale = payload.get("locale") or "fr-CA"
        result = _service().create_session(user=frappe.session.user, company=company, page=page, locale=locale)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def send_message():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = send_message_handler(payload=payload, user=frappe.session.user, company=company)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_session():
        require_human_staff_role()
        name = frappe.local.form_dict.get("name")
        if not name:
            frappe.throw("Le nom est obligatoire.", frappe.ValidationError)
        try:
            result = _service().get_session(name=name, user=frappe.session.user)
        except ChatSessionNotFoundError:
            frappe.throw(f"Conversation {name} introuvable.", frappe.DoesNotExistError)
        return {"data": result}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def get_messages():
        require_human_staff_role()
        name = frappe.local.form_dict.get("name")
        if not name:
            frappe.throw("Le nom est obligatoire.", frappe.ValidationError)
        try:
            result = _service().get_messages(name=name, user=frappe.session.user)
        except ChatSessionNotFoundError:
            frappe.throw(f"Conversation {name} introuvable.", frappe.DoesNotExistError)
        return {"data": result}

    @frappe.whitelist(methods=["GET"])
    @defense.safe_input
    def list_sessions():
        require_human_staff_role()
        company = get_company_context()
        result = _service().list_sessions(user=frappe.session.user, company=company)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def pin_context():
        require_human_staff_role()
        payload = frappe.local.form_dict
        session_name = payload.get("chat_session_id")
        context_snapshot_name = payload.get("context_snapshot_id")
        if not session_name or not context_snapshot_name:
            frappe.throw(
                "La conversation et le contexte à épingler sont obligatoires.",
                frappe.ValidationError,
            )
        _service().pin_context(session_name, context_snapshot_name, user=frappe.session.user)
        return {"data": {"pinned": True}}

    @frappe.whitelist(methods=["POST"])
    @defense.safe_input
    def clear_context():
        require_human_staff_role()
        payload = frappe.local.form_dict
        session_name = payload.get("chat_session_id")
        if not session_name:
            frappe.throw("La conversation est obligatoire.", frappe.ValidationError)
        _service().clear_context(session_name, user=frappe.session.user)
        return {"data": {"pinned": False}}
