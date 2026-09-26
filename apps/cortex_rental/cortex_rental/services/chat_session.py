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
import json
from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.schemas.chat_schemas import SendMessageResponseData
from cortex_rental.services.agent_router import AgentRouter
from cortex_rental.services.tool_policy import ToolPolicyResolver
from cortex_rental.services.chat_context import (
    ChatContextResolver,
    ChatContextPermissionError,
)
from cortex_rental.services.onyx_chat_client import (
    HttpOnyxChatClient,
    OnyxChatClient,
    MockOnyxChatClient,
)
from cortex_rental.services.chat_response_transformer import ChatResponseTransformer
from cortex_rental.services.chat_telemetry import ChatAuditTelemetryService

RATE_LIMIT_MAX_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 60


class ChatRateLimitError(Exception):
    pass


class ChatSessionNotFoundError(Exception):
    pass


def _mask_sensitive_text(value: str) -> str:
    """Persist conversational text with common direct identifiers masked."""
    import re

    value = re.sub(
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        "[courriel masqué]",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"(?<!\w)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\w)",
        "[téléphone masqué]",
        value,
    )


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
    def __init__(
        self, onyx_client: Optional[OnyxChatClient] = None, engine_provider: Any = None, company: Optional[str] = None
    ):
        # Anthropic (direct, with Cortex tools) or Onyx, chosen per company.
        self.engine_provider = engine_provider
        self.model_name = getattr(engine_provider, "model", "")
        if engine_provider is None and onyx_client is None and frappe and company:
            from cortex_rental.services.ai.config import ai_settings

            settings = ai_settings(company)
            if settings["provider"] == "anthropic":
                from cortex_rental.services.ai.anthropic_provider import AnthropicProvider

                self.engine_provider = AnthropicProvider(frappe.conf.get("anthropic_api_key"), settings["model"])
                self.model_name = self.engine_provider.model
        if onyx_client is not None:
            self.onyx_client = onyx_client
        elif self.engine_provider is not None:
            self.onyx_client = None
        elif not frappe:
            # The deterministic mock remains available only to unit tests and
            # the local no-Frappe contract path.
            self.onyx_client = MockOnyxChatClient()
        else:
            conf = getattr(frappe, "conf", {})
            provider = str(conf.get("cortex_chat_provider", "onyx")).lower()
            if provider == "mock" and conf.get("developer_mode"):
                self.onyx_client = MockOnyxChatClient()
            else:
                # Created on first send: history/list endpoints must work without Onyx configured.
                self.onyx_client = None

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
            frappe.throw(
                "Unauthorized: this chat session belongs to a different user.",
                frappe.PermissionError,
            )
        data = session.as_dict()
        messages = []
        for row in frappe.get_all(
            "Cortex Chat Message",
            filters={"chat_session": name},
            fields=["name", "sender_type", "content_sanitized", "ui_blocks_json", "model_name", "created_at"],
            order_by="created_at asc",
            limit_page_length=500,
        ):
            try:
                blocks = json.loads(row.ui_blocks_json or "[]")
            except (TypeError, ValueError):
                blocks = []
            messages.append(
                {
                    "id": row.name,
                    "sender_type": row.sender_type,
                    "text": row.content_sanitized or "",
                    "blocks": blocks,
                    "model_name": row.model_name,
                    "created_at": str(row.created_at),
                }
            )
        data["messages"] = messages
        return data

    # -----------------------------------------------------------------
    def list_sessions(self, user: str, company: str) -> List[Dict[str, Any]]:
        if not frappe:
            return []

        sessions = frappe.get_all(
            "Cortex Chat Session",
            filters={"user": user, "company": company},
            fields=["name", "agent_profile", "state", "started_at", "last_message_at"],
            order_by="last_message_at desc",
            limit_page_length=50,
        )
        for session in sessions:
            first = frappe.get_all(
                "Cortex Chat Message",
                filters={"chat_session": session.name, "sender_type": "Human"},
                fields=["content_sanitized"],
                order_by="created_at asc",
                limit_page_length=1,
            )
            session["title"] = ((first[0].content_sanitized if first else "") or "")[:80]
        return sessions

    # -----------------------------------------------------------------
    def pin_context(self, session_name: str, context_snapshot_name: str, user: str) -> None:
        if not frappe:
            return
        session = frappe.get_doc("Cortex Chat Session", session_name)
        if session.user != user:
            frappe.throw(
                "Unauthorized: this chat session belongs to a different user.",
                frappe.PermissionError,
            )
        session.pinned_context = context_snapshot_name
        session.save()

    def clear_context(self, session_name: str, user: str) -> None:
        if not frappe:
            return
        session = frappe.get_doc("Cortex Chat Session", session_name)
        if session.user != user:
            frappe.throw(
                "Unauthorized: this chat session belongs to a different user.",
                frappe.PermissionError,
            )
        session.pinned_context = None
        session.save()

    # -----------------------------------------------------------------
    def send_message(
        self,
        user: str,
        company: str,
        message: str,
        context: Dict[str, Any],
        chat_session_id: Optional[str],
        client_turn_id: Optional[str] = None,
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
            chat_session_id,
            user,
            company,
            agent_profile,
            context.get("locale", "fr-CA"),
        )

        context_hash = ChatContextResolver.hash_context(resolved_context)
        self._write_context_snapshot(session_name, company, page, resolved_context, context_hash)
        self._write_message(session_name, company, "Human", user, message, [], request_id)

        if frappe and self.engine_provider is not None:
            return self._send_with_engine(
                user=user,
                company=company,
                message=message,
                page=page,
                resolved_context=resolved_context,
                session_name=session_name,
                request_id=request_id,
                client_turn_id=client_turn_id,
                start=start,
                started_at=started_at,
            )

        upstream_session_id = None
        if frappe:
            upstream_session_id = frappe.db.get_value("Cortex Chat Session", session_name, "onyx_chat_session_id")

        if self.onyx_client is None:
            self.onyx_client = HttpOnyxChatClient.from_site_config()
        try:
            result = self.onyx_client.send_message(
                message=message,
                chat_session_id=upstream_session_id,
                persona_id=agent_profile,
                allowed_tool_ids=allowed_tool_ids,
                context=resolved_context,
            )
        except Exception as exc:
            ChatAuditTelemetryService.record_chat_turn(
                company=company,
                agent_profile=agent_profile,
                request_id=request_id,
                status="Failed",
                started_at=started_at,
                duration_ms=int((time.monotonic() - start) * 1000),
                error_message=type(exc).__name__,
            )
            raise
        if frappe and result.onyx_session_id and result.onyx_session_id != upstream_session_id:
            frappe.db.set_value(
                "Cortex Chat Session",
                session_name,
                "onyx_chat_session_id",
                result.onyx_session_id,
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
        self,
        chat_session_id: Optional[str],
        user: str,
        company: str,
        agent_profile: str,
        locale: str,
    ) -> str:
        if chat_session_id:
            if not frappe:
                return chat_session_id
            if frappe.db.exists("Cortex Chat Session", chat_session_id):
                owner = frappe.db.get_value("Cortex Chat Session", chat_session_id, "user")
                if owner != user:
                    frappe.throw(
                        "Unauthorized: this chat session belongs to a different user.",
                        frappe.PermissionError,
                    )
                return chat_session_id
            # Client sent an id for a session that doesn't exist (e.g.
            # a stale id from a cleared cache) — start a fresh one
            # rather than hard-failing the whole conversation.

        created = self.create_session(user=user, company=company, page="dashboard", locale=locale)
        return created["name"]

    def _write_context_snapshot(
        self,
        session_name: str,
        company: str,
        page: str,
        resolved_context: Dict[str, Any],
        context_hash: str,
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

        safe_content = _mask_sensitive_text(content)

        doc = frappe.get_doc(
            {
                "doctype": "Cortex Chat Message",
                "chat_session": session_name,
                "company": company,
                "sender_type": sender_type,
                "sender_id": sender_id,
                "content_sanitized": safe_content,
                "content_hash": hashlib.sha256(safe_content.encode("utf-8")).hexdigest(),
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
        frappe.db.set_value(
            "Cortex Chat Session",
            session_name,
            "last_message_at",
            frappe.utils.now_datetime(),
        )

    # -----------------------------------------------------------------
    def _send_with_engine(
        self,
        user: str,
        company: str,
        message: str,
        page: str,
        resolved_context: Dict[str, Any],
        session_name: str,
        request_id: str,
        client_turn_id: Optional[str],
        start: float,
        started_at: Any,
    ) -> SendMessageResponseData:
        """Anthropic path: the model calls Cortex tools as this user; writes become proposals."""
        from cortex_rental.services.ai import engine
        from cortex_rental.services.ai.tools import ToolContext
        from cortex_rental.services.onyx_chat_client import OnyxChatResult

        roles = set(frappe.get_roles(user))
        rows = frappe.get_all(
            "Cortex Chat Message",
            filters={"chat_session": session_name},
            fields=["sender_type", "content_sanitized as text", "request_id"],
            order_by="created_at asc",
            limit_page_length=60,
        )
        history = engine.history_messages([r for r in rows if r.request_id != request_id])
        full_name = frappe.db.get_value("User", user, "full_name") or user
        system = engine.system_prompt(
            company=company,
            user_name=full_name,
            roles=[r for r in roles if r not in ("All", "Guest", "Desk User")],
            page=page,
            document=resolved_context.get("active_document_name"),
            locale=resolved_context.get("locale", "fr-CA"),
            now=frappe.utils.now_datetime(),
        )

        def publish(kind: str, payload: Dict[str, Any]) -> None:
            frappe.publish_realtime(
                "cortex_ai",
                {"session": session_name, "turn": client_turn_id, "kind": kind, **payload},
                user=user,
            )

        run = frappe.get_doc(
            {
                "doctype": "Cortex Agent Run",
                "company": company,
                "agent_id": "cortex-assistant",
                "request_id": request_id,
                "actor_id": user,
                "model_used": self.model_name,
                "status": "Running",
                "tool_call_count": 0,
                "started_at": started_at,
                "last_seen_at": started_at,
            }
        )
        run.flags.ignore_permissions = True
        run.insert()

        def record_tool_call(name: str, status: str, duration_ms: int, error: Optional[str]) -> None:
            call = frappe.get_doc(
                {
                    "doctype": "Cortex Agent Tool Call",
                    "company": company,
                    "agent_run": run.name,
                    "tool_name": name,
                    "scope": "user",
                    "status": status,
                    "started_at": frappe.utils.now_datetime(),
                    "duration_ms": duration_ms,
                    "error_message": (error or "")[:1000] or None,
                }
            )
            call.flags.ignore_permissions = True
            call.insert()

        def record_proposal(tool: Any, args: Dict[str, Any], preview: Dict[str, Any]) -> str:
            action = frappe.get_doc(
                {
                    "doctype": "Cortex AI Action",
                    "company": company,
                    "chat_session": session_name,
                    "user": user,
                    "tool": tool.name,
                    "title": (preview.get("title") or tool.name)[:140],
                    "arguments": frappe.as_json(args),
                    "preview": frappe.as_json(preview),
                    "status": "Proposed",
                }
            )
            action.flags.ignore_permissions = True
            action.insert()
            return action.name

        try:
            result = engine.run_turn(
                provider=self.engine_provider,
                system=system,
                history=history,
                message=message,
                ctx=ToolContext(user=user, company=company, roles=roles),
                publish=publish,
                record_proposal=record_proposal,
                record_tool_call=record_tool_call,
            )
        except Exception as exc:
            frappe.db.set_value(
                "Cortex Agent Run", run.name, {"status": "Failed", "last_seen_at": frappe.utils.now_datetime()}
            )
            ChatAuditTelemetryService.record_chat_turn(
                company=company,
                agent_profile="cortex-assistant",
                request_id=request_id,
                status="Failed",
                started_at=started_at,
                duration_ms=int((time.monotonic() - start) * 1000),
                error_message=type(exc).__name__,
            )
            publish("error", {"message": str(exc)[:300]})
            raise

        blocks = ChatResponseTransformer.transform(
            OnyxChatResult(onyx_message_id=request_id, text=result.text, blocks=result.blocks)
        )
        message_doc_name = self._write_message(
            session_name,
            company,
            "Agent",
            "cortex-assistant",
            result.text,
            blocks,
            request_id,
            model_provider="anthropic",
            model_name=self.model_name,
            routing_reason="Cortex assistant (Anthropic, outils Cortex)",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        self._touch_session(session_name)
        frappe.db.set_value(
            "Cortex Agent Run",
            run.name,
            {
                "status": "Completed",
                "tool_call_count": len(result.tool_calls),
                "last_seen_at": frappe.utils.now_datetime(),
            },
        )
        ChatAuditTelemetryService.record_chat_turn(
            company=company,
            agent_profile="cortex-assistant",
            request_id=request_id,
            status="Success",
            started_at=started_at,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
        publish("done", {"message_id": message_doc_name})
        return SendMessageResponseData(
            message_id=message_doc_name, chat_session_id=session_name, status="completed", blocks=blocks
        )
