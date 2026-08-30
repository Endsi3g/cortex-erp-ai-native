"""
ChatAuditTelemetryService — records every chat gateway call to the same
Cortex Agent Run / Cortex Agent Tool Call trail every other agent-facing
endpoint uses (services/agent_telemetry.py), rather than inventing a
parallel telemetry system just for chat. "tool_name" here is the chat
turn itself (`chat.send_message`), not the individual MCP tools Onyx
may have called — those still get their own Cortex Agent Tool Call rows
from the MCP-side telemetry once a real Onyx/MCP round-trip exists.
"""

import time
from typing import Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.agent_telemetry import record_tool_call


class ChatAuditTelemetryService:
    @staticmethod
    def record_chat_turn(
        company: str,
        agent_profile: str,
        request_id: str,
        status: str,
        started_at,
        duration_ms: int,
        error_message: Optional[str] = None,
    ) -> None:
        record_tool_call(
            company=company,
            tool_name="chat.send_message",
            scope=f"chat:{agent_profile}",
            status=status,
            started_at=started_at,
            duration_ms=duration_ms,
            error_message=error_message,
            agent_id=agent_profile,
            request_id=request_id,
        )


def now_monotonic_ms() -> float:
    return time.monotonic() * 1000
