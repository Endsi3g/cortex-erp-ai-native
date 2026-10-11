"""Niveau Cortex Gemma (Gemma 4 par l'API Gemini) : choix du fournisseur, clé, prix honnêtes (sans banc Frappe)."""

import unittest

from cortex_rental.services import subscriptions
from cortex_rental.services.ai import settings as ai_settings
from cortex_rental.services.ai.gateway import TierUnavailable, resolve_tier
from cortex_rental.services.ai.providers import AIConfigurationError, GeminiProvider, provider_for


def values(**over):
    base = dict(ai_settings.DEFAULTS)
    base.update(api_key="", anthropic_api_key="", openai_api_key="", company_limits={})
    base.update(over)
    return base


class TestGemmaTier(unittest.TestCase):
    def test_gemma_model_ids_use_the_gemini_provider_and_the_gemini_key(self):
        for model in ("gemma-4-26b-a4b-it", "gemma-4-31b-it"):
            self.assertIsInstance(provider_for(model, "k"), GeminiProvider)
            self.assertEqual(ai_settings.provider_key_for(model, values(api_key="g-key")), "g-key")
        with self.assertRaises(AIConfigurationError):
            provider_for("llama-9", "k")

    def test_request_goes_to_the_gemma_model_with_tools_and_system_instruction(self):
        provider = provider_for("gemma-4-26b-a4b-it", "k")
        self.assertEqual(provider.model, "gemma-4-26b-a4b-it")  # l'URL generateContent est construite avec ce modèle

    def test_tier_needs_the_gemini_key_and_is_never_the_default(self):
        self.assertFalse({t["key"]: t for t in ai_settings.tiers(values())}["gemma"]["configured"])
        rows = {t["key"]: t for t in ai_settings.tiers(values(api_key="g"))}
        self.assertTrue(rows["gemma"]["configured"])
        self.assertEqual(rows["gemma"]["model"], "gemma-4-26b-a4b-it")
        self.assertEqual(
            ai_settings.default_tier(values(api_key="g", default_tier="gemma")), "gemma"
        )  # choix explicite permis
        self.assertEqual(ai_settings.default_tier(values(api_key="g")), "rapide")

    def test_price_is_unconfirmed_and_says_so(self):
        row = {t["key"]: t for t in ai_settings.tiers(values(api_key="g"))}["gemma"]
        self.assertEqual((row["price_input_per_mtok"], row["price_output_per_mtok"]), (0.0, 0.0))
        self.assertEqual(row["cost_index"], 0)  # pas d'indice de coût inventé
        self.assertIn("non confirmé", ai_settings.VERIFIED_MODELS["gemma-4-26b-a4b-it"]["note"].lower())

    def test_disabled_or_modelless_gemma_is_not_offered_and_resolves_to_a_refusal(self):
        for over in ({"tier_gemma_enabled": 0}, {"tier_gemma_model": ""}):
            with self.assertRaises(
                TierUnavailable
            ):  # refusé clairement, jamais remplacé en silence par un autre modèle
                resolve_tier(values(api_key="g", **over), "gemma")

    def test_resolve_picks_the_gemma_model(self):
        tier = resolve_tier(values(api_key="g"), "gemma")
        self.assertEqual(tier["model"], "gemma-4-26b-a4b-it")

    def test_gemma_is_a_known_subscription_tier_but_has_no_price_in_the_catalog(self):
        self.assertIn("gemma", subscriptions.ALL_TIERS)
        self.assertFalse(
            [r for r in subscriptions.DEFAULT_OPTIONS if r[1] == "gemma"]
        )  # le prix de vente est une décision de consensus

    def test_the_chat_request_accepts_every_tier_key_the_settings_define(self):
        """Une clé de niveau ajoutée aux réglages mais oubliée dans la requête de conversation était refusée (Luna l'était)."""
        from cortex_rental.schemas.chat_schemas import SendMessageRequest

        for key in ai_settings.TIER_KEYS:
            self.assertIn(key, SendMessageRequest.model_fields["model_tier"].annotation.__args__[0].__args__)

    def test_validation_errors_name_the_field_not_pydantic_internals(self):
        from pydantic import BaseModel, ValidationError

        from cortex_rental.api.v1.chat import validation_summary

        class Probe(BaseModel):
            model_tier: int

        try:
            Probe(model_tier="x")
        except ValidationError as exc:
            self.assertEqual(validation_summary(exc), "model_tier")
            self.assertNotIn("pydantic", validation_summary(exc))


if __name__ == "__main__":
    unittest.main()
