"""
Cortex Chat Gateway tests. Most of this suite runs in this sandbox
without a live Frappe site — ChatSessionService.send_message()'s
no-frappe branch is a real, deterministic code path (same convention
as AvailabilityService.check()'s mock branch elsewhere in this repo),
not a stub. What genuinely needs a live bench (row-level permission
isolation, actual DB persistence) is marked skipUnless(frappe, ...).
"""

import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1.chat import send_message_handler
from cortex_rental.services.agent_router import AgentRouter, PAGE_TO_AGENT
from cortex_rental.services.tool_policy import ToolPolicyResolver, AGENT_TOOL_MAP
from cortex_rental.services.onyx_chat_client import MockOnyxChatClient
from cortex_rental.services.chat_response_transformer import ChatResponseTransformer
from cortex_rental.services.chat_session import ChatSessionService


class TestClientCannotEscalate(unittest.TestCase):
    """The core security property from the chat architecture spec:
    a client cannot choose its own company/agent/model/allowed_tool_ids
    — not because a check rejects the value, but because there is no
    field to put it in (schemas/chat_schemas.py sets extra="forbid")."""

    def _payload(self, **extra):
        base = {
            "message": "Bonjour",
            "context": {"page": "availability", "locale": "fr-CA"},
        }
        base.update(extra)
        return base

    def test_rejects_client_supplied_company(self):
        with self.assertRaises(ValueError):
            send_message_handler(self._payload(company="Someone Else's Company"), user="u@test.com", company="C1")

    def test_rejects_client_supplied_model(self):
        with self.assertRaises(ValueError):
            send_message_handler(self._payload(model="claude-sonnet-5"), user="u@test.com", company="C1")

    def test_rejects_client_supplied_allowed_tool_ids(self):
        with self.assertRaises(ValueError):
            send_message_handler(self._payload(allowed_tool_ids=["activate_contract"]), user="u@test.com", company="C1")

    def test_rejects_client_supplied_agent_inside_context(self):
        payload = self._payload()
        payload["context"]["agent"] = "admin_agent"
        with self.assertRaises(ValueError):
            send_message_handler(payload, user="u@test.com", company="C1")

    def test_rejects_message_over_length_limit(self):
        payload = self._payload(message="x" * 5000)
        with self.assertRaises(ValueError):
            send_message_handler(payload, user="u@test.com", company="C1")

    def test_rejects_too_many_selected_items(self):
        payload = self._payload()
        payload["context"]["selected_item_codes"] = [f"ITEM-{i}" for i in range(51)]
        with self.assertRaises(ValueError):
            send_message_handler(payload, user="u@test.com", company="C1")


class TestAgentRoutingAndToolPolicy(unittest.TestCase):
    def test_every_routed_agent_has_a_tool_policy_entry(self):
        """Catches drift between AgentRouter's routing table and
        ToolPolicyResolver's allowlist — a page that routes to an agent
        with no tool-policy entry would silently fall back to an empty
        list today, but this test makes that an explicit, visible fact
        rather than a surprise."""
        for page, agent in PAGE_TO_AGENT.items():
            self.assertIn(agent, AGENT_TOOL_MAP, f"page={page} routes to {agent}, which has no tool policy entry")

    def test_availability_agent_has_no_write_tools(self):
        tools = ToolPolicyResolver.resolve_tools("cortex-availability")
        write_tools = {"create_quote_draft", "create_customer_draft", "submit_approval_request"}
        self.assertFalse(set(tools) & write_tools)

    def test_intake_agent_only_drafts_never_confirms(self):
        tools = ToolPolicyResolver.resolve_tools("cortex-intake")
        self.assertNotIn("activate_contract", tools)  # not a real tool at all — must never appear
        self.assertIn("create_quote_draft", tools)

    def test_unknown_agent_returns_empty_not_all_tools(self):
        self.assertEqual(ToolPolicyResolver.resolve_tools("some-agent-that-does-not-exist"), [])

    def test_agent_router_ignores_no_client_override_parameter(self):
        # resolve_agent takes only `page` — there is no second parameter
        # for a client-requested agent to override it with.
        import inspect

        sig = inspect.signature(AgentRouter.resolve_agent)
        self.assertEqual(list(sig.parameters.keys()), ["page"])


class TestMockOnyxChatClient(unittest.TestCase):
    def test_availability_response_is_labeled_as_mock_not_a_real_lookup(self):
        result = MockOnyxChatClient().send_message(
            message="Avez-vous de la disponibilité ?",
            chat_session_id=None,
            persona_id="cortex-availability",
            allowed_tool_ids=["search_rental_items", "check_inventory_availability"],
            context={},
        )
        fact_blocks = [b for b in result.blocks if b["type"] == "verified_fact"]
        self.assertTrue(fact_blocks)
        self.assertIn("simulé", fact_blocks[0]["title"].lower())

    def test_no_allowed_tools_returns_missing_information_not_a_fabricated_answer(self):
        result = MockOnyxChatClient().send_message(
            message="Explique-moi ce dossier",
            chat_session_id=None,
            persona_id="cortex-returns",
            allowed_tool_ids=[],  # cortex-returns has no MCP tool yet
            context={},
        )
        self.assertEqual(result.blocks[0]["type"], "missing_information")


class TestChatResponseTransformer(unittest.TestCase):
    def test_malformed_block_becomes_an_error_block_not_a_crash(self):
        from cortex_rental.services.onyx_chat_client import OnyxChatResult

        result = OnyxChatResult(
            onyx_message_id="x",
            text="...",
            blocks=[{"type": "verified_fact"}],  # missing required fields
        )
        blocks = ChatResponseTransformer.transform(result)
        self.assertEqual(blocks[0]["type"], "error")

    def test_empty_block_list_still_returns_a_visible_error_not_a_blank_message(self):
        from cortex_rental.services.onyx_chat_client import OnyxChatResult

        result = OnyxChatResult(onyx_message_id="x", text="", blocks=[])
        blocks = ChatResponseTransformer.transform(result)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "error")


class TestSendMessageEndToEndNoFrappe(unittest.TestCase):
    """frappe is unimportable in this sandbox, so ChatSessionService
    takes its documented no-DB branch — this still exercises real
    validation, routing, tool-policy, mock-client and transformer code,
    just without persistence."""

    def test_returns_typed_blocks_for_an_availability_question(self):
        response = send_message_handler(
            {
                "message": "Avez-vous 12 tubes Astera du 8 au 18 septembre ?",
                "context": {"page": "availability", "locale": "fr-CA"},
            },
            user="camille@cinerental.test",
            company="CineRental Montreal",
        )
        self.assertIn("blocks", response)
        self.assertTrue(response["blocks"])
        self.assertEqual(response["status"], "completed")

    def test_unknown_page_falls_back_to_operations_agent_not_an_error(self):
        response = send_message_handler(
            {
                "message": "Résumé du jour",
                "context": {"page": "some-future-page-not-yet-routed", "locale": "fr-CA"},
            },
            user="camille@cinerental.test",
            company="CineRental Montreal",
        )
        self.assertIn("blocks", response)


@unittest.skipUnless(frappe, "requires a live Frappe site (bench) — not available in this sandbox")
class TestChatIsolationLive(unittest.TestCase):
    """Written so the first real `bench run-tests` proves session/message
    privacy holds, not just Company scoping — see
    permissions/__init__.py's _own_chat_session_condition."""

    def test_user_cannot_read_another_users_session(self):
        service = ChatSessionService()
        created = service.create_session(user="user-a@test.com", company="Cortex Test Co A", page="availability")
        with self.assertRaises(frappe.PermissionError):
            service.get_session(created["name"], user="user-b@test.com")
