"""
Per-agent allowlist of MCP tool ids — the server-side answer to the
chat spec's explicit rule: "Ne laisse jamais allowed_tool_ids = null en
production." Every call to Onyx must carry an explicit, non-empty-or-
deliberately-empty list; never `None` (which would let the agent use
every tool configured on the Onyx persona, defeating the whole point).

Tool ids here are real, currently-registered FastMCP tools (see
apps/cortex-mcp/cortex_mcp/server.py's @mcp.tool() functions) — not
guessed. Several agents this spec calls for need a read-only
capability (transaction read, check-in read, approval read) that has
no corresponding MCP tool today; those agents get an empty list rather
than a fabricated tool name. Tracked in HANDOFF.md as a real gap, not
silently worked around.
"""

from typing import List

# Real tool names, cross-checked against apps/cortex-mcp/cortex_mcp/server.py.
AGENT_TOOL_MAP = {
    "cortex-availability": ["search_rental_items", "check_inventory_availability", "list_rentals"],
    "cortex-intake": [
        "search_rental_items",
        "search_customers",
        "check_inventory_availability",
        "create_quote_draft",
        "create_customer_draft",
        "submit_approval_request",
    ],
    "cortex-consignment": ["prepare_owner_statement"],
    # No read-only "transaction"/"check-in"/"approval" MCP tool exists
    # yet — these three agents are read-only by design (the spec's own
    # table has no write tool for them either) but literally have no
    # tool to call until one is built. Empty on purpose, not an oversight.
    # Les outils de lecture de la passerelle IA (services/ai/tools.py) comblent une partie de ce manque :
    # lire les locations et les approbations en attente. Aucun n'écrit ni n'approuve.
    "cortex-returns": ["list_rentals", "late_returns"],
    "cortex-approval-assistant": ["list_pending_approvals", "list_rentals"],
    "cortex-operations": [
        "search_rental_items",
        "check_inventory_availability",
        "list_rentals",
        "list_pending_approvals",
        "finance_summary",
        "customer_summary",
        "late_returns",
        # Proposent une écriture; la personne approuve (services/ai/actions.py). Offerts seulement si `cortex_ai_actions` est actif.
        "propose_create_customer",
        "propose_create_quote",
    ],
}


class ToolPolicyResolver:
    @staticmethod
    def resolve_tools(agent_profile: str) -> List[str]:
        """Always returns a concrete list (possibly empty), never None —
        an unknown agent_profile also resolves to an empty list rather
        than falling back to "all tools", which would be the one
        failure mode this whole module exists to prevent."""
        return list(AGENT_TOOL_MAP.get(agent_profile, []))
