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

from cortex_rental.permissions.agent_scopes import (
    require_human_staff_role,
    get_company_context,
)
from cortex_rental.schemas.chat_schemas import SendMessageRequest
from cortex_rental.services.onyx_chat_client import MockOnyxChatClient
from cortex_rental.services.chat_session import (
    ChatSessionService,
    ChatContextPermissionError,
    ChatRateLimitError,
    ChatSessionNotFoundError,
)


def _raise_validation_error(exc: ValidationError) -> None:
    if frappe:
        frappe.throw(f"Invalid chat request: {exc}", frappe.ValidationError)
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

    service = ChatSessionService(company=company)
    try:
        response = service.send_message(
            user=user,
            company=company,
            message=request.message,
            context=request.context.model_dump(),
            chat_session_id=request.chat_session_id,
            client_turn_id=request.client_turn_id,
        )
    except ChatContextPermissionError as exc:
        if frappe:
            frappe.throw(str(exc), frappe.PermissionError)
        raise
    except ChatRateLimitError as exc:
        if frappe:
            frappe.throw(str(exc), frappe.ValidationError)
        raise

    return response.model_dump(mode="json")


if frappe:

    @frappe.whitelist(methods=["POST"])
    def create_session():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        page = payload.get("page") or "dashboard"
        locale = payload.get("locale") or "fr-CA"
        result = ChatSessionService().create_session(
            user=frappe.session.user, company=company, page=page, locale=locale
        )
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    def send_message():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        result = send_message_handler(payload=payload, user=frappe.session.user, company=company)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["GET"])
    def get_session():
        require_human_staff_role()
        name = frappe.local.form_dict.get("name")
        if not name:
            frappe.throw("name is required.", frappe.ValidationError)
        try:
            result = ChatSessionService().get_session(name=name, user=frappe.session.user)
        except ChatSessionNotFoundError:
            frappe.throw(f"Chat session {name} not found.", frappe.DoesNotExistError)
        return {"data": result}

    @frappe.whitelist(methods=["GET"])
    def list_sessions():
        require_human_staff_role()
        company = get_company_context()
        result = ChatSessionService().list_sessions(user=frappe.session.user, company=company)
        return {"data": result, "meta": {"company": company}}

    @frappe.whitelist(methods=["POST"])
    def pin_context():
        require_human_staff_role()
        payload = frappe.local.form_dict
        session_name = payload.get("chat_session_id")
        context_snapshot_name = payload.get("context_snapshot_id")
        if not session_name or not context_snapshot_name:
            frappe.throw(
                "chat_session_id and context_snapshot_id are required.",
                frappe.ValidationError,
            )
        ChatSessionService().pin_context(session_name, context_snapshot_name, user=frappe.session.user)
        return {"data": {"pinned": True}}

    @frappe.whitelist(methods=["POST"])
    def clear_context():
        require_human_staff_role()
        payload = frappe.local.form_dict
        session_name = payload.get("chat_session_id")
        if not session_name:
            frappe.throw("chat_session_id is required.", frappe.ValidationError)
        ChatSessionService().clear_context(session_name, user=frappe.session.user)
        return {"data": {"pinned": False}}

    @frappe.whitelist(methods=["GET"])
    def get_assistant_status():
        """Whether the assistant can answer, without exposing any URL or key."""
        from cortex_rental.services.ai.config import ai_settings

        require_human_staff_role()
        settings = ai_settings(get_company_context())
        return {
            "data": {
                "available": settings["available"],
                "provider": settings["provider"],
                "model_name": settings["model"] if settings["available"] else None,
            }
        }

    @frappe.whitelist(methods=["POST"])
    def decide_action(action_id: str, decision: str):
        """Confirm (execute as this person) or cancel a proposal made by the assistant."""
        from cortex_rental.services.ai import actions
        from cortex_rental.services.audit import AuditService

        require_human_staff_role()
        company = get_company_context()
        if decision not in ("confirm", "cancel"):
            frappe.throw("Décision inconnue.", frappe.ValidationError)
        if not frappe.db.exists("Cortex AI Action", action_id):
            frappe.throw("Action introuvable.", frappe.DoesNotExistError)
        # Row lock: two clicks or two tabs cannot execute the same proposal twice.
        frappe.db.get_value("Cortex AI Action", action_id, "status", for_update=True)
        action = frappe.get_doc("Cortex AI Action", action_id)
        try:
            actions.check_decidable(action.as_dict(), frappe.session.user, company, frappe.utils.now_datetime())
        except actions.ActionRefused as exc:
            frappe.throw(str(exc), frappe.PermissionError)

        now = frappe.utils.now_datetime()
        arguments = frappe.parse_json(action.arguments or "{}") or {}
        route = None
        if decision == "cancel":
            action.update({"status": "Cancelled", "decided_by": frappe.session.user, "decided_at": now})
            action.flags.ignore_permissions = True
            action.save()
        else:
            frappe.db.savepoint("cortex_ai_action")
            try:
                result, route = actions.execute(action.tool, arguments)
            except Exception as exc:
                frappe.db.rollback(save_point="cortex_ai_action")
                message = str(exc)[:500] or type(exc).__name__
                action.update(
                    {"status": "Failed", "error_message": message, "decided_by": frappe.session.user, "decided_at": now}
                )
                action.flags.ignore_permissions = True
                action.save()
            else:
                action.update(
                    {
                        "status": "Executed",
                        "result": frappe.as_json({**result, "route": route}),
                        "decided_by": frappe.session.user,
                        "decided_at": now,
                    }
                )
                action.flags.ignore_permissions = True
                action.save()
        AuditService.record_mutation(
            company=company,
            action=f"cortex.ai.action_{action.status.lower()}",
            entity_type="Cortex AI Action",
            entity_id=action.name,
            after_state={"tool": action.tool, "status": action.status, "error": action.error_message},
        )
        if action.chat_session:
            ChatSessionService(onyx_client=MockOnyxChatClient()).record_action_outcome(
                session_name=action.chat_session, company=company, action=action
            )
        return {
            "data": {
                "action_id": action.name,
                "status": action.status.lower(),
                "result": frappe.parse_json(action.result) if action.result else None,
                "error": action.error_message or None,
            }
        }
