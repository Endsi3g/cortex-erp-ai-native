import unittest

from cortex_rental.services.agent_telemetry import get_agent_context, log_tool_call


class TestAgentTelemetryDegradesWithoutFrappe(unittest.TestCase):
    def test_get_agent_context_has_safe_defaults(self):
        agent_id, request_id = get_agent_context()
        self.assertEqual(agent_id, "unknown-agent")
        self.assertIsNone(request_id)

    def test_log_tool_call_decorator_preserves_return_value_and_args(self):
        @log_tool_call("dummy_tool", scope="agent:items:read")
        def handler(x, y=2):
            return x + y

        self.assertEqual(handler(3, y=4), 7)

    def test_log_tool_call_decorator_reraises_exceptions_unchanged(self):
        @log_tool_call("dummy_tool", scope="agent:items:read")
        def handler():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            handler()


if __name__ == "__main__":
    unittest.main()
