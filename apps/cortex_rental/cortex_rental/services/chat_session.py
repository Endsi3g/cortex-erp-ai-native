"""
ChatSessionService — the Cortex Chat Gateway's orchestration layer
(cortex_rental.api.v1.chat calls into this, not into Onyx directly).
Ties together ChatContextResolver, AgentRouter, ToolPolicyResolver,
OnyxChatClient, ChatResponseTransformer and ChatAuditTelemetryService
per the 14-step sequence in docs/design-system.md's chat architecture
section ("Cortex Chat Gateway").

Every public method here takes `company`/`user` as already-resolved
values (from get_company_context()/frappe.session.user in the API
layer) — this module never re-derives or trusts a client-supplied
Company or user identity.
"""

import time
from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.schemas.chat_schemas import SendMessageResponseData
from cortex_rental.services.agent_router import AgentRouter
from cortex_rental.services.tool_policy import ToolPolicyResolver
from cortex_rental.services.chat_context import ChatContextResolver, ChatContextPermissionError
from cortex_rental.services.onyx_chat_client import OnyxChatClient, MockOnyxChatClient
from cortex_rental.services.chat_response_transformer import ChatResponseTransformer
from cortex_rental.services.chat_telemetry import ChatAuditTelemetryService

RATE_LIMIT_MAX_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 60


class ChatRateLimitError(Exception):
    pass


class ChatSessionNotFoundError(Exception):
    pass


def _new_id(prefix: str) -> str:
    if frappe:
        return frappe.generate_hash(length=16)
    import uuid

    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _check_rate_limit(user: str) -> None:
    """Best-effort per-user rate limit via Frappe's own Redis-backed
    cache (frappe.cache() — a real, standard Frappe API, not a guess).
    No-ops without frappe (sandbox/unit-test mode) — there is no shared
    cache to rate-limit against there anyway."""
    if not frappe:
        return

    cache_key = f"cortex_chat_rate_limit:{user}"
    count = frappe.cache().get_value(cache_key) or 0
    if int(count) >= RATE_LIMIT_MAX_MESSAGES:
        raise ChatRateLimitError(
            f"Rate limit exceeded: max {RATE_LIMIT_MAX_MESSAGES} messages per {RATE_LIMIT_WINDOW_SECONDS}s."
        )
    frappe.cache().set_value(cache_key, int(count) + 1, expires_in_sec=RATE_LIMIT_WINDOW_SECONDS)


class ChatSessionService:
    def __init__(self, onyx_client: Optional[OnyxChatClient] = None):
        # Defaults to the mock — see HANDOFF.md for why no real Onyx
        # client is wired in this pass. Tests inject their own fake.
        self.onyx_client = onyx_client or MockOnyxChatClient()

    # -----------------------------------------------------------------
    def create_session(self, user: str, company: str, page: str, locale: str = "fr-CA") -> Dict[str, Any]:
        agent_profile = AgentRouter.resolve_agent(page)
        now = frappe.utils.now_datetime() if frappe else None

        if not frappe:
            return {
                "name": _new_id("CCHAT"),
                "company": company,
                "user": user,
                "agent_profile": agent_profile,
                "locale": locale,
                "state": "Active",
            }

        doc = frappe.get_doc(
            {
                "doctype": "Cortex Chat Session",
                "company": company,
                "user": user,
                "agent_profile": agent_profile,
                "locale": locale,
                "state": "Active",
                "started_at": now,
                "last_message_at": now,
            }
        )
        doc.insert()
        return doc.as_dict()

    # -----------------------------------------------------------------
    def get_session(self, name: str, user: str) -> Dict[str, Any]:
        if not frappe:
            raise ChatSessionNotFoundError(name)

        session = frappe.get_doc("Cortex Chat Session", name)
        if session.user != user and "System Manager" not in frappe.get_roles(user):
            frappe.throw("Unauthorized: this chat session belongs to a different user.", frappe.PermissionError)
        return session.as_dict()

    # -----------------------------------------------------------------
    def list_sessions(self, user: str, company: str) -> List[Dict[str, Any]]:
        if not frappe:
            return []

        return frappe.get_all(
            "Cortex Chat Session",
            filters={"user": user, "company": company},
            fields=["name", "agent_profile", "state", "started_at", "last_message_at"],
            order_by="last_message_at desc",
            limit_page_length=50,
        )

    # -----------------------------------------------------------------
    def pin_context(self, session_name: str, context_snapshot_name: str, user: str) -> None:
        if not frappe:
            return
        session = frappe.get_doc("Cortex Chat Session", session_name)
        if session.user != user:
            frappe.throw("Unauthorized: this chat session belongs to a different user.", frappe.PermissionError)
        session.pinned_context = context_snapshot_name
        session.save()

    def clear_context(self, session_name: str, user: str) -> None:
        if not frappe:
            return
        session = frappe.get_doc("Cortex Chat Session", session_name)
        if session.user != user:
            frappe.throw("Unauthorized: this chat session belongs to a different user.", frappe.PermissionError)
        session.pinned_context = None
        session.save()

    # -----------------------------------------------------------------
    def send_message(
        self, user: str, company: str, message: str, context: Dict[str, Any], chat_session_id: Optional[str]
    ) -> SendMessageResponseData:
        _check_rate_limit(user)

        start = time.monotonic()
        started_at = frappe.utils.now_datetime() if frappe else None
        request_id = _new_id("REQ")

        page = context.get("page", "dashboard")
        agent_profile = AgentRouter.resolve_agent(page)
        allowed_tool_ids = ToolPolicyResolver.resolve_tools(agent_profile)

        try:
            resolved_context = ChatContextResolver.resolve(context, user=user, company=company)
        except ChatContextPermissionError as exc:
            ChatAuditTelemetryService.record_chat_turn(
                company=company,
                agent_profile=agent_profile,
                request_id=request_id,
                status="Denied",
                started_at=started_at,
                duration_ms=int((time.monotonic() - start) * 1000),
                error_message=str(exc),
            )
            raise

        session_name = self._resolve_session(
            chat_session_id, user, company, agent_profile, context.get("locale", "fr-CA")
        )

        context_hash = ChatContextResolver.hash_context(resolved_context)
        self._write_context_snapshot(session_name, company, page, resolved_context, context_hash)
        self._write_message(session_name, company, "Human", user, message, [], request_id)

        result = self.onyx_client.send_message(
            message=message,
            chat_session_id=session_name,
            persona_id=agent_profile,
            allowed_tool_ids=allowed_tool_ids,
            context=resolved_context,
        )
        blocks = ChatResponseTransformer.transform(result)

        message_doc_name = self._write_message(
            session_name,
            company,
            "Agent",
            agent_profile,
            result.text,
            blocks,
            request_id,
            model_provider=result.model_provider,
            model_name=result.model_name,
            routing_reason=result.routing_reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

        self._touch_session(session_name)

        ChatAuditTelemetryService.record_chat_turn(
            company=company,
            agent_profile=agent_profile,
            request_id=request_id,
            status="Success",
            started_at=started_at,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

        return SendMessageResponseData(
            message_id=message_doc_name,
            chat_session_id=session_name,
            status="completed",
            blocks=blocks,
        )

    # -----------------------------------------------------------------
    def _resolve_session(
        self, chat_session_id: Optional[str], user: str, company: str, agent_profile: str, locale: str
    ) -> str:
        if chat_session_id:
            if not frappe:
                return chat_session_id
            if frappe.db.exists("Cortex Chat Session", chat_session_id):
                owner = frappe.db.get_value("Cortex Chat Session", chat_session_id, "user")
                if owner != user:
                    frappe.throw("Unauthorized: this chat session belongs to a different user.", frappe.PermissionError)
                return chat_session_id
            # Client sent an id for a session that doesn't exist (e.g.
            # a stale id from a cleared cache) — start a fresh one
            # rather than hard-failing the whole conversation.

        created = self.create_session(user=user, company=company, page="dashboard", locale=locale)
        return created["name"]

    def _write_context_snapshot(
        self, session_name: str, company: str, page: str, resolved_context: Dict[str, Any], context_hash: str
    ) -> None:
        if not frappe:
            return
        doc = frappe.get_doc(
            {
                "doctype": "Cortex Chat Context Snapshot",
                "chat_session": session_name,
                "company": company,
                "page": page,
                "reference_doctype": resolved_context.get("active_doctype"),
                "reference_name": resolved_context.get("active_document_name"),
                "selected_item_codes_json": frappe.as_json(resolved_context.get("selected_item_codes", [])),
                "selected_serial_nos_json": frappe.as_json(resolved_context.get("selected_serial_nos", [])),
                "visible_dates_json": frappe.as_json(resolved_context.get("visible_date_range")),
                "filters_json": frappe.as_json(resolved_context.get("active_filters", {})),
                "permissions_snapshot_json": frappe.as_json({"roles": frappe.get_roles(frappe.session.user)}),
                "context_hash": context_hash,
                "created_at": frappe.utils.now_datetime(),
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.set_value("Cortex Chat Session", session_name, "last_context_hash", context_hash)

    def _write_message(
        self,
        session_name: str,
        company: str,
        sender_type: str,
        sender_id: str,
        content: str,
        blocks: List[Dict[str, Any]],
        request_id: str,
        model_provider: str = "",
        model_name: str = "",
        routing_reason: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> str:
        if not frappe:
            return _new_id("CMSG")

        import hashlib

        doc = frappe.get_doc(
            {
                "doctype": "Cortex Chat Message",
                "chat_session": session_name,
                "company": company,
                "sender_type": sender_type,
                "sender_id": sender_id,
                "content_sanitized": content,
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "ui_blocks_json": frappe.as_json(blocks),
                "model_provider": model_provider,
                "model_name": model_name,
                "routing_reason": routing_reason,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "request_id": request_id,
                "created_at": frappe.utils.now_datetime(),
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()
        return doc.name

    def _touch_session(self, session_name: str) -> None:
        if not frappe:
            return
        frappe.db.set_value("Cortex Chat Session", session_name, "last_message_at", frappe.utils.now_datetime())
