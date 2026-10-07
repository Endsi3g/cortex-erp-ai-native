"""Modèles Cortex (Rapide, Équilibré, Avancé) : disponibilité, choix du niveau, fournisseur Anthropic (sans réseau)."""

import json
import unittest

from cortex_rental.services.ai import settings as ai_settings
from cortex_rental.services.ai.gateway import AIGateway, TierUnavailable, resolve_tier, tool_progress_blocks
from cortex_rental.services.ai.providers import (
    AIConfigurationError,
    AnthropicProvider,
    GeminiProvider,
    ProviderResult,
    ScriptedProvider,
    ToolCall,
    provider_for,
)


def values(**overrides):
    base = dict(ai_settings.DEFAULTS)
    base.update(api_key="", anthropic_api_key="", company_limits={})
    base.update(overrides)
    return base


class TestTierAvailability(unittest.TestCase):
    def test_nothing_configured_means_no_tier(self):
        self.assertFalse(any(t["configured"] for t in ai_settings.tiers(values())))
        self.assertEqual(ai_settings.default_tier(values()), "")
        with self.assertRaises(AIConfigurationError):
            resolve_tier(values(), None)

    def test_gemini_key_only_offers_rapide(self):
        v = values(api_key="g")
        self.assertEqual([t["key"] for t in ai_settings.tiers(v) if t["configured"]], ["rapide"])
        self.assertEqual(ai_settings.default_tier(v), "rapide")

    def test_both_keys_offer_three_levels_priced_differently(self):
        v = values(api_key="g", anthropic_api_key="a")
        rows = {t["key"]: t for t in ai_settings.tiers(v)}
        self.assertTrue(all(rows[k]["configured"] for k in ("rapide", "equilibre", "avance")))
        self.assertFalse(rows["luna"]["configured"])  # désactivé par défaut, sans clé OpenAI
        self.assertEqual(rows["rapide"]["cost_index"], 1.0)
        self.assertGreater(rows["equilibre"]["cost_index"], rows["rapide"]["cost_index"])
        self.assertGreater(rows["avance"]["cost_index"], rows["equilibre"]["cost_index"])
        self.assertEqual(rows["equilibre"]["model"], "claude-sonnet-5-5")
        self.assertEqual(rows["avance"]["model"], "claude-opus-5-5")

    def test_disabled_tier_is_not_offered(self):
        v = values(api_key="g", anthropic_api_key="a", tier_avance_enabled=0)
        self.assertFalse({t["key"]: t for t in ai_settings.tiers(v)}["avance"]["configured"])

    def test_default_falls_back_to_first_available(self):
        v = values(anthropic_api_key="a", default_tier="rapide")
        self.assertEqual(ai_settings.default_tier(v), "equilibre")

    def test_requested_tier_without_key_is_refused_not_swapped(self):
        v = values(api_key="g")
        with self.assertRaises(TierUnavailable) as raised:
            resolve_tier(v, "avance")
        self.assertIn("Cortex Avancé", str(raised.exception))

    def test_resolve_picks_requested_tier(self):
        v = values(api_key="g", anthropic_api_key="a")
        self.assertEqual(resolve_tier(v, "equilibre")["model"], "claude-sonnet-5-5")
        self.assertEqual(resolve_tier(v, None)["key"], "rapide")


class TestProviders(unittest.TestCase):
    def test_provider_is_chosen_by_prefix(self):
        self.assertIsInstance(provider_for("gemini-3.8-flash", "k"), GeminiProvider)
        self.assertIsInstance(provider_for("claude-opus-5-5", "k"), AnthropicProvider)
        with self.assertRaises(AIConfigurationError):
            provider_for("mistral-large", "k")

    def test_key_follows_provider(self):
        v = values(api_key="g", anthropic_api_key="a")
        self.assertEqual(ai_settings.provider_key_for("claude-sonnet-5-5", v), "a")
        self.assertEqual(ai_settings.provider_key_for("gemini-3.8-flash", v), "g")

    def test_anthropic_request_shape(self):
        p = AnthropicProvider("claude-sonnet-5-5", "k", max_output_tokens=500)
        body = p.request_body(
            "sys", [p.user_message("Salut")], [{"name": "t", "description": "d", "parameters": {"type": "object"}}]
        )
        self.assertEqual(body["model"], "claude-sonnet-5-5")
        self.assertEqual(body["system"], "sys")
        self.assertEqual(body["max_tokens"], 500)
        self.assertEqual(body["tools"][0]["input_schema"], {"type": "object"})
        self.assertNotIn("api_key", json.dumps(body))

    def test_anthropic_parse_text_and_tool_use(self):
        p = AnthropicProvider("claude-sonnet-5-5", "k")
        result = p.parse(
            {
                "content": [
                    {"type": "text", "text": "Je vérifie."},
                    {"type": "tool_use", "id": "tu_1", "name": "late_returns", "input": {"limit": 3}},
                ],
                "usage": {"input_tokens": 120, "output_tokens": 30},
            }
        )
        self.assertEqual(result.text, "Je vérifie.")
        self.assertEqual((result.tool_calls[0].name, result.tool_calls[0].id), ("late_returns", "tu_1"))
        self.assertEqual((result.input_tokens, result.output_tokens), (120, 30))
        echoed = p.assistant_message(result)
        self.assertEqual(echoed["role"], "assistant")
        self.assertEqual(echoed["content"][1]["id"], "tu_1")  # l'id doit revenir tel quel au tour suivant

    def test_anthropic_tool_result_links_to_call_id(self):
        p = AnthropicProvider("claude-sonnet-5-5", "k")
        message = p.tool_results_message(
            [
                {"name": "x", "id": "tu_9", "result": {"error": "refusé"}},
                {"name": "y", "id": "tu_8", "result": {"ok": 1}},
            ]
        )
        self.assertEqual(message["content"][0]["tool_use_id"], "tu_9")
        self.assertTrue(message["content"][0]["is_error"])
        self.assertNotIn("is_error", message["content"][1])

    def test_missing_key_is_a_configuration_error(self):
        with self.assertRaises(AIConfigurationError):
            AnthropicProvider("claude-sonnet-5-5", "").generate("s", [], [])


class TestGatewayUsesInjectedProvider(unittest.TestCase):
    def test_tool_progress_blocks_are_unique_and_labelled(self):
        blocks = tool_progress_blocks(["late_returns", "late_returns", "search_rental_items"])
        self.assertEqual(
            [b["tool_name"] for b in blocks], ["Recherche des retours en retard", "Recherche dans le catalogue"]
        )
        self.assertTrue(all(b["state"] == "success" for b in blocks))

    def test_injected_provider_still_works(self):
        gateway = AIGateway(provider=ScriptedProvider([ProviderResult(text="Bonjour")]), settings=values(api_key="g"))
        self.assertEqual(gateway.provider().name, "Simulation")
        self.assertEqual(ToolCall(name="a", args={}).id, "")


if __name__ == "__main__":
    unittest.main()
