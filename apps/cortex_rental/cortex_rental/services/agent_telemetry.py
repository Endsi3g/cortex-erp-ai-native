"""
Structured agent tool-call telemetry (PRD §7: "Tout appel outil est
journalisé dans Cortex Agent Tool Call + Cortex Audit Event").

This is deliberately separate from Cortex Audit Event: Audit Event
records business mutations (what changed, before/after state). Cortex
Agent Run / Cortex Agent Tool Call record the *agent-facing API
surface* itself — every call, whether it mutated anything or not,
succeeded, was denied by a scope/tenant check, or errored. Together
they answer "what did every agent invocation actually do" without
requiring an operator to reconstruct that from Audit Event's
narrower, mutation-only trail.

Never logs raw request/response payloads, documents, or PII — only the
tool name, scope, outcome and (for Denied/Error) the exception message.
"""

from functools import wraps
from typing import Any, Callable, Optional
import time

try:
    import frappe
except ImportError:
    frappe = None


def get_agent_context() -> tuple:
    """Read the caller-supplied (never trust-bearing) agent/run labels."""
    if not frappe:
        return "unknown-agent", None

    request = getattr(frappe.local, "request", None)
    agent_id = (request.headers.get("X-Cortex-Agent-Id") if request else None) or "unknown-agent"
    request_id = request.headers.get("X-Request-ID") if request else None
    return agent_id, request_id


def _get_or_create_run(company: str, agent_id: str, request_id: Optional[str], actor_id: str):
    now = frappe.utils.now_datetime()

    if not request_id:
        # No correlation ID supplied by the caller: every call is its
        # own single-call run rather than silently grouping unrelated
        # calls together under a shared/empty key.
        request_id = frappe.generate_hash(length=20)

    existing = frappe.db.exists("Cortex Agent Run", {"request_id": request_id, "company": company})
    if existing:
        frappe.db.set_value("Cortex Agent Run", existing, "last_seen_at", now)
        frappe.db.set_value(
            "Cortex Agent Run",
            existing,
            "tool_call_count",
            frappe.db.get_value("Cortex Agent Run", existing, "tool_call_count") + 1,
        )
        return existing

    run = frappe.get_doc(
        {
            "doctype": "Cortex Agent Run",
            "company": company,
            "agent_id": agent_id,
            "request_id": request_id,
            "actor_id": actor_id,
            "status": "Running",
            "tool_call_count": 1,
            "started_at": now,
            "last_seen_at": now,
        }
    )
    run.flags.ignore_permissions = True
    run.insert()
    return run.name


def record_tool_call(
    company: str,
    tool_name: str,
    scope: Optional[str],
    status: str,
    started_at,
    duration_ms: int,
    error_message: Optional[str] = None,
    agent_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """
    `agent_id`/`request_id` default to get_agent_context() (the
    X-Cortex-Agent-Id/X-Request-ID headers an MCP-originated call
    sends) but can be passed explicitly — used by
    services/chat_telemetry.py, where the caller is a human Desk
    session with no such headers, and "agent_id" instead means which
    Copilot persona (cortex-availability, etc.) is answering.
    """
    if not frappe:
        return

    default_agent_id, default_request_id = get_agent_context()
    agent_id = agent_id or default_agent_id
    request_id = request_id or default_request_id
    actor_id = frappe.session.user

    try:
        run_name = _get_or_create_run(company, agent_id, request_id, actor_id)

        call = frappe.get_doc(
            {
                "doctype": "Cortex Agent Tool Call",
                "company": company,
                "agent_run": run_name,
                "tool_name": tool_name,
                "scope": scope,
                "status": status,
                "started_at": started_at,
                "duration_ms": duration_ms,
                "error_message": (error_message or "")[:500] or None,
            }
        )
        call.flags.ignore_permissions = True
        call.insert()

        if status in ("Denied", "Error"):
            frappe.db.set_value("Cortex Agent Run", run_name, "status", "Failed")
    except Exception:
        # Telemetry must never break the actual business call it wraps.
        frappe.log_error(title="cortex_rental.agent_telemetry.record_tool_call failed")


def log_tool_call(tool_name: str, scope: Optional[str] = None) -> Callable:
    """
    Decorator for whitelisted agent-facing API entrypoints. Wraps the
    call, timing it and recording Success/Denied/Error to Cortex Agent
    Tool Call, then re-raises any exception unchanged — this is pure
    observability and must never alter the wrapped function's actual
    security behavior or return value.

    Resolves `company` for the log entry from get_company_context()
    itself (best-effort — if that call is what raised the exception,
    e.g. an unauthorized Company, the entry is logged against
    "unresolved" rather than dropped, since a denied cross-tenant
    attempt is exactly the kind of event this exists to capture).
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not frappe:
                return func(*args, **kwargs)

            start = time.monotonic()
            started_at = frappe.utils.now_datetime()
            company = "unresolved"
            try:
                from cortex_rental.permissions.agent_scopes import get_company_context

                company = get_company_context()
            except Exception:
                pass

            try:
                result = func(*args, **kwargs)
                record_tool_call(
                    company=company,
                    tool_name=tool_name,
                    scope=scope,
                    status="Success",
                    started_at=started_at,
                    duration_ms=int((time.monotonic() - start) * 1000),
                )
                return result
            except frappe.PermissionError as e:
                record_tool_call(
                    company=company,
                    tool_name=tool_name,
                    scope=scope,
                    status="Denied",
                    started_at=started_at,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error_message=str(e),
                )
                raise
            except Exception as e:
                record_tool_call(
                    company=company,
                    tool_name=tool_name,
                    scope=scope,
                    status="Error",
                    started_at=started_at,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error_message=str(e),
                )
                raise

        return wrapper

    return decorator
