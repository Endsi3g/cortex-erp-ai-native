"""
Resolves which Cortex Copilot agent persona handles a chat turn, from
the page context alone — never from a client-supplied "agent" field
(SendMessageRequest/ChatContext have no such field at all, see
schemas/chat_schemas.py). This is the single source of truth for the
"Sélection d'agent" routing table from the chat architecture spec.
"""

# page -> agent persona id. Every value here MUST have a corresponding
# entry in ToolPolicyResolver.AGENT_TOOL_MAP (services/tool_policy.py)
# — enforced by a test, not just by convention.
PAGE_TO_AGENT = {
    "availability": "cortex-availability",
    "transaction": "cortex-intake",
    "inbound": "cortex-intake",
    "checkin": "cortex-returns",
    "consignment": "cortex-consignment",
    "approvals": "cortex-approval-assistant",
    "dashboard": "cortex-operations",
}

DEFAULT_AGENT = "cortex-operations"


class AgentRouter:
    @staticmethod
    def resolve_agent(page: str) -> str:
        """
        Always returns the server-determined agent for this page.
        There is deliberately no parameter here for a client-requested
        agent — if a caller wants to influence routing, it does so by
        controlling which page it's on, not by asking for a specific
        agent by name.
        """
        return PAGE_TO_AGENT.get(page, DEFAULT_AGENT)
