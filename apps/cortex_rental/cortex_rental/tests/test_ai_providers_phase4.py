"""Phase 4 : prix vérifiés, niveau Luna (OpenAI), « à venir » honnête, règles de la société dans le prompt."""

import json
import unittest

from cortex_rental.services.ai import gateway
from cortex_rental.services.ai import settings as ai_settings
from cortex_rental.services.ai.providers import AIProviderError, OpenAIProvider, ProviderResult, ToolCall, provider_for


def values(**extra):
    base = dict(ai_settings.DEFAULTS)
    base.update({"api_key": "", "anthropic_api_key": "", "openai_api_key": ""})
    base.update(extra)
    return base


class TestVerifiedPrices(unittest.TestCase):
    def test_defaults_match_the_verified_provider_prices(self):
        d = ai_settings.DEFAULTS
        self.assertEqual((d["tier_equilibre_price_input"], d["tier_equilibre_price_output"]), (2.0, 10.0))
        self.assertEqual((d["tier_avance_price_input"], d["tier_avance_price_output"]), (4.0, 20.0))
        self.assertEqual((d["tier_luna_price_input"], d["tier_luna_price_output"]), (0.1, 0.5))
        for key, tier in (("claude-sonnet-5-5", "equilibre"), ("claude-opus-5-5", "avance"), ("gpt-6-luna", "luna")):
            verified = ai_settings.VERIFIED_MODELS[key]
            self.assertEqual(d[f"tier_{tier}_model"], key)
            self.assertEqual(
                (d[f"tier_{tier}_price_input"], d[f"tier_{tier}_price_output"]), (verified["input"], verified["output"])
            )
        self.assertEqual(d["model"], "gemini-3.8-flash")

    def test_doctype_defaults_follow_the_code_defaults(self):
        import pathlib

        path = (
            pathlib.Path(ai_settings.__file__).resolve().parents[2]
            / "cortex_rental"
            / "doctype"
            / "cortex_ai_settings"
            / "cortex_ai_settings.json"
        )
        fields = {f["fieldname"]: f for f in json.loads(path.read_text(encoding="utf-8"))["fields"]}
        for key in ("equilibre", "avance", "luna"):
            for side in ("input", "output"):
                name = f"tier_{key}_price_{side}"
                self.assertEqual(float(fields[name]["default"]), float(ai_settings.DEFAULTS[name]), name)
        self.assertEqual(fields["tier_luna_enabled"]["default"], "0")
        self.assertEqual(fields["openai_api_key"]["fieldtype"], "Password")

    def test_the_price_patch_is_registered_and_only_replaces_old_defaults(self):
        import pathlib

        root = pathlib.Path(ai_settings.__file__).resolve().parents[2]
        self.assertIn("cortex_rental.patches.correct_ai_tier_prices", (root / "patches.txt").read_text())
        source = (root / "patches" / "correct_ai_tier_prices.py").read_text()
        self.assertIn("float(current or 0) == old", source)  # une saisie manuelle n'est jamais écrasée


class TestLunaTier(unittest.TestCase):
    def test_luna_is_off_until_a_key_and_activation_exist(self):
        luna = {t["key"]: t for t in ai_settings.tiers(values())}["luna"]
        self.assertFalse(luna["enabled"])
        self.assertFalse(luna["configured"])

    def test_luna_needs_the_openai_key_not_the_gemini_one(self):
        rows = {t["key"]: t for t in ai_settings.tiers(values(tier_luna_enabled=1, api_key="gemini-key"))}
        self.assertTrue(rows["luna"]["enabled"])
        self.assertFalse(rows["luna"]["configured"])
        rows = {t["key"]: t for t in ai_settings.tiers(values(tier_luna_enabled=1, openai_api_key="sk-x"))}
        self.assertTrue(rows["luna"]["configured"])

    def test_requesting_an_unconfigured_tier_is_refused_not_replaced(self):
        with self.assertRaises(gateway.TierUnavailable):
            gateway.resolve_tier(values(api_key="g", tier_luna_enabled=1), "luna")

    def test_upcoming_models_are_never_selectable(self):
        self.assertTrue(any(m["label"] == "Gemini 4" for m in ai_settings.UPCOMING_MODELS))
        self.assertNotIn("gemini-4", {t["model"] for t in ai_settings.tiers(values())})


class TestOpenAIProvider(unittest.TestCase):
    def provider(self):
        return provider_for("gpt-6-luna", "sk-test", max_output_tokens=500)

    def test_prefix_selects_the_openai_provider(self):
        self.assertIsInstance(self.provider(), OpenAIProvider)

    def test_request_body_disables_reasoning_for_function_calling_and_keeps_the_key_out(self):
        tools = [{"name": "list_rentals", "description": "d", "parameters": {"type": "object", "properties": {}}}]
        body = self.provider().request_body("SYS", [{"role": "user", "content": "Bonjour"}], tools)
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "SYS"})
        self.assertEqual(body["max_completion_tokens"], 500)
        self.assertEqual(body["tools"][0]["function"]["name"], "list_rentals")
        self.assertNotIn("sk-test", json.dumps(body))

    def test_tool_calls_round_trip_with_one_tool_message_per_result(self):
        p = self.provider()
        payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "list_rentals", "arguments": '{"limit": 3}'},
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {"name": "late_returns", "arguments": "pas du json"},
                            },
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }
        result = p.parse(payload)
        self.assertEqual([c.id for c in result.tool_calls], ["call_1", "call_2"])
        self.assertEqual(result.tool_calls[0].args, {"limit": 3})
        self.assertEqual(result.tool_calls[1].args, {})  # arguments illisibles : jamais inventés
        self.assertEqual((result.input_tokens, result.output_tokens), (11, 7))
        self.assertEqual(p.assistant_message(result)["tool_calls"][0]["id"], "call_1")
        messages = p.tool_results_message(
            [{"id": "call_1", "result": {"ok": 1}}, {"id": "call_2", "result": {"error": "x"}}]
        )
        self.assertEqual([m["tool_call_id"] for m in messages], ["call_1", "call_2"])
        self.assertTrue(all(m["role"] == "tool" for m in messages))

    def test_plain_answer_and_refusal(self):
        p = self.provider()
        ok = p.parse({"choices": [{"message": {"role": "assistant", "content": " Bonjour "}}], "usage": {}})
        self.assertEqual(ok.text, "Bonjour")
        with self.assertRaises(AIProviderError):
            p.parse({"choices": [{"message": {"role": "assistant", "content": None, "refusal": "non"}}]})

    def test_assistant_message_without_raw_rebuilds_tool_calls(self):
        p = self.provider()
        msg = p.assistant_message(ProviderResult(text="", tool_calls=[ToolCall("f", {"a": 1}, "id1")]))
        self.assertEqual(json.loads(msg["tool_calls"][0]["function"]["arguments"]), {"a": 1})


class TestCompanyRules(unittest.TestCase):
    def test_rules_are_read_from_settings_and_never_invented(self):
        from types import SimpleNamespace

        row = {
            "apply_taxes": 1,
            "tps_rate": 5.0,
            "tvq_rate": 9.975,
            "deposit_percent": 30.0,
            "quote_hold_enabled": 1,
            "quote_hold_hours": 72,
            "allow_sole_approver_self_approval": 0,
        }
        original = gateway.frappe
        try:
            gateway.frappe = SimpleNamespace(db=SimpleNamespace(get_value=lambda *a, **k: row))
            text = gateway.company_rules("Cortex Test")
            self.assertIn("TPS 5.0 %", text)
            self.assertIn("TVQ 9.975 %", text)
            self.assertIn("72 h", text)
            self.assertIn("personne ne décide de sa propre demande", text)
            gateway.frappe = SimpleNamespace(db=SimpleNamespace(get_value=lambda *a, **k: None))
            self.assertEqual(gateway.company_rules("Cortex Test"), "")
            self.assertEqual(gateway.company_rules(""), "")
        finally:
            gateway.frappe = original

    def test_system_prompt_has_a_rules_slot(self):
        self.assertIn("{rules}", gateway.SYSTEM_PROMPT)
        gateway.SYSTEM_PROMPT.format(company="A", today="2026-10-07", page="x", rules="")


if __name__ == "__main__":
    unittest.main()
