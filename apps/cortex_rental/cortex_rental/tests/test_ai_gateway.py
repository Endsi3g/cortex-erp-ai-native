"""Passerelle IA : fournisseur Gemini, boucle d'outils, budget, droits et réglages (sans réseau, sans banc Frappe)."""

import json
import os
import unittest
from unittest import mock

from cortex_rental.services.ai import budget, gateway, tools
from cortex_rental.services.ai.providers import (
    AIConfigurationError,
    AIProviderError,
    GeminiProvider,
    ProviderResult,
    ScriptedProvider,
    ToolCall,
    provider_for,
)
from cortex_rental.services.tool_policy import AGENT_TOOL_MAP

MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cortex_rental")

SETTINGS = {
    "enabled": 1,
    "model": "gemini-3.8-flash",
    "fallback_model": "",
    "max_tool_steps": 3,
    "warn_percent": 80,
    "price_input_per_mtok": 0.0,
    "price_output_per_mtok": 0.0,
    "default_monthly_budget": 0.0,
    "default_monthly_token_cap": 0,
    "company_limits": {},
    "api_key": "secret-key",
}

STATUS_OK = {
    "cost": 0,
    "tokens": 0,
    "calls": 0,
    "cost_cap": 0,
    "token_cap": 0,
    "percent": 0,
    "warning": False,
    "blocked": False,
}


def load(*parts):
    with open(os.path.join(MODULE_DIR, *parts), encoding="utf-8") as handle:
        return json.load(handle)


class FakeTool(tools.Tool):
    def __init__(self, name, output):
        super().__init__(name, "outil de test", {"type": "object", "properties": {}}, lambda **kw: output)


class GatewayCase(unittest.TestCase):
    def run_gateway(self, script, registry, allowed, settings=None, status=None, **kwargs):
        provider = ScriptedProvider(script)
        recorded = []
        with (
            mock.patch.object(tools, "REGISTRY", registry),
            mock.patch.object(budget, "check"),
            mock.patch.object(budget, "record", side_effect=lambda *a, **k: recorded.append(a)),
            mock.patch.object(budget, "status", return_value=status or STATUS_OK),
            mock.patch.object(gateway, "frappe", None),
        ):
            outcome = gateway.AIGateway(provider=provider, settings=settings or dict(SETTINGS)).run(
                message="Bonjour",
                history=kwargs.get("history"),
                allowed_tools=allowed,
                company="Société A",
                user="a@test.com",
            )
        return outcome, provider, recorded


class TestGeminiProvider(unittest.TestCase):
    def setUp(self):
        self.provider = GeminiProvider("gemini-3.8-flash", "k", temperature=0.1, max_output_tokens=256)

    def test_request_carries_system_tools_and_generation_config(self):
        body = self.provider.request_body(
            "système",
            [self.provider.user_message("allo")],
            [{"name": "t", "description": "d", "parameters": {"type": "object"}}],
        )
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "système")
        self.assertEqual(body["generationConfig"], {"temperature": 0.1, "maxOutputTokens": 256})
        self.assertEqual(body["tools"][0]["functionDeclarations"][0]["name"], "t")

    def test_no_tools_key_when_no_tool_is_exposed(self):
        self.assertNotIn("tools", self.provider.request_body("s", [], []))

    def test_parse_reads_text_calls_and_tokens_and_hides_thoughts(self):
        payload = {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "réflexion", "thought": True},
                            {"text": "Voici."},
                            {"functionCall": {"name": "finance_summary", "args": {}}, "thoughtSignature": "abc"},
                        ],
                    }
                }
            ],
            "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 30, "thoughtsTokenCount": 10},
        }
        result = self.provider.parse(payload)
        self.assertEqual(result.text, "Voici.")
        self.assertEqual([c.name for c in result.tool_calls], ["finance_summary"])
        self.assertEqual((result.input_tokens, result.output_tokens), (120, 40))
        # le message natif (avec sa signature) est renvoyé tel quel au tour suivant
        self.assertEqual(self.provider.assistant_message(result)["parts"][2]["thoughtSignature"], "abc")

    def test_blocked_prompt_is_a_clear_error(self):
        with self.assertRaises(AIProviderError):
            self.provider.parse({"promptFeedback": {"blockReason": "SAFETY"}})

    def test_api_key_goes_in_a_header_never_in_the_url(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"], captured["headers"] = request.full_url, dict(request.header_items())
            raise AIProviderError("stop")

        with mock.patch("urllib.request.urlopen", fake_urlopen), self.assertRaises(AIProviderError):
            self.provider.generate("s", [], [])
        self.assertNotIn("k", captured["url"].split("?")[-1] if "?" in captured["url"] else "")
        self.assertIn("gemini-3.8-flash:generateContent", captured["url"])
        self.assertEqual(captured["headers"].get("X-goog-api-key"), "k")

    def test_missing_key_is_a_configuration_error(self):
        with self.assertRaises(AIConfigurationError):
            GeminiProvider("gemini-3.8-flash", "").generate("s", [], [])

    def test_upgrading_the_model_is_only_a_setting(self):
        self.assertEqual(provider_for("gemini-4-pro", "k").model, "gemini-4-pro")
        self.assertEqual(provider_for("gemini-3.8-flash", "k").BASE_URL, provider_for("gemini-4-pro", "k").BASE_URL)

    def test_unknown_provider_is_refused_clearly(self):
        with self.assertRaises(AIConfigurationError):
            provider_for("mistral-large", "k")


class TestToolLoop(GatewayCase):
    FINANCE = {
        "mois": "2026-09",
        "facture": 1000.0,
        "encaisse": 400.0,
        "solde_a_recevoir": 600.0,
        "factures_ouvertes": 2,
        "factures_en_retard": 1,
    }

    def test_tool_result_reaches_the_model_and_becomes_a_verified_fact(self):
        script = [
            ProviderResult(tool_calls=[ToolCall("finance_summary", {})], input_tokens=100, output_tokens=10),
            ProviderResult(text="Vous avez 600 $ à recevoir.", input_tokens=150, output_tokens=20),
        ]
        outcome, provider, recorded = self.run_gateway(
            script, {"finance_summary": FakeTool("finance_summary", self.FINANCE)}, ["finance_summary"]
        )
        self.assertEqual(outcome.text, "Vous avez 600 $ à recevoir.")
        self.assertEqual((outcome.input_tokens, outcome.output_tokens), (250, 30))
        self.assertEqual(outcome.tool_calls, ["finance_summary"])
        self.assertTrue(any(b["type"] == "verified_fact" for b in outcome.blocks))
        self.assertEqual(len(recorded), 2)  # chaque appel au modèle est compté
        self.assertEqual(provider.calls[1]["messages"][-1]["role"], "tool")

    def test_a_tool_outside_the_allowlist_is_never_run(self):
        ran = []
        sneaky = tools.Tool(
            "approve_everything", "x", {"type": "object", "properties": {}}, lambda **k: ran.append(1) or {}
        )
        script = [
            ProviderResult(tool_calls=[ToolCall("approve_everything", {})]),
            ProviderResult(text="Je ne peux pas."),
        ]
        outcome, provider, _ = self.run_gateway(script, {"approve_everything": sneaky}, [])
        self.assertEqual(ran, [])
        self.assertEqual(provider.calls[0]["tools"], [])
        self.assertIn("pas autorisé", provider.calls[1]["messages"][-1]["results"][0]["result"]["error"])
        self.assertEqual(outcome.tool_calls, [])

    def test_a_tool_error_is_given_back_to_the_model_not_hidden(self):
        boom = tools.Tool(
            "list_rentals",
            "x",
            {"type": "object", "properties": {}},
            lambda **k: (_ for _ in ()).throw(PermissionError("Accès refusé")),
        )
        with mock.patch.object(tools, "REGISTRY", {"list_rentals": boom}):
            self.assertEqual(tools.execute("list_rentals", {}), {"error": "Accès refusé"})
            self.assertIn("error", tools.execute("inconnu", {}))

    def test_endless_tool_calls_stop_after_the_step_limit(self):
        loop = [ProviderResult(tool_calls=[ToolCall("finance_summary", {})]) for _ in range(6)]
        outcome, _, _ = self.run_gateway(
            loop, {"finance_summary": FakeTool("finance_summary", self.FINANCE)}, ["finance_summary"]
        )
        self.assertEqual(outcome.text, gateway.STEPS_EXHAUSTED)

    def test_an_empty_answer_is_replaced_by_an_honest_message(self):
        outcome, _, _ = self.run_gateway([ProviderResult(text="")], {}, [])
        self.assertEqual(outcome.text, gateway.EMPTY_ANSWER)

    def test_a_quote_proposal_creates_nothing_and_needs_the_person(self):
        proposal = {
            "proposal": {
                "customer": "Client",
                "starts_at": "2026-10-10 09:00:00",
                "ends_at": "2026-10-12 09:00:00",
                "lines": [{"item": "Console", "quantity": 1, "amount": 300.0}],
                "subtotal": 300.0,
                "tps": 15.0,
                "tvq": 29.93,
                "total": 344.93,
            }
        }
        script = [
            ProviderResult(tool_calls=[ToolCall("create_quote_draft", {})]),
            ProviderResult(text="Voici une proposition."),
        ]
        outcome, _, _ = self.run_gateway(
            script, {"create_quote_draft": FakeTool("create_quote_draft", proposal)}, ["create_quote_draft"]
        )
        block = next(b for b in outcome.blocks if b["type"] == "proposal")
        self.assertFalse(block["requires_approval"])
        self.assertIn("Rien n'est créé", " ".join(block["impact"]))

    def test_history_is_passed_to_the_model_in_order(self):
        history = [{"role": "user", "text": "Question 1"}, {"role": "assistant", "text": "Réponse 1"}]
        _, provider, _ = self.run_gateway([ProviderResult(text="ok")], {}, [], history=history)
        texts = [m["text"] for m in provider.calls[0]["messages"]]
        self.assertEqual(texts, ["Question 1", "Réponse 1", "Bonjour"])

    def test_system_prompt_forbids_guessing_and_approving(self):
        self.assertIn("ne devines jamais", gateway.SYSTEM_PROMPT)
        self.assertIn("ni approuver", gateway.SYSTEM_PROMPT)

    def test_a_warning_block_appears_near_the_budget(self):
        warning = {**STATUS_OK, "warning": True, "percent": 85.0}
        outcome, _, _ = self.run_gateway([ProviderResult(text="ok")], {}, [], status=warning)
        self.assertTrue(any(b["type"] == "risk" for b in outcome.blocks))

    def test_fallback_model_is_used_only_when_the_main_one_is_missing(self):
        class Missing(ScriptedProvider):
            def generate(self, *a, **k):
                raise AIProviderError("introuvable", status=404)

        fallback = ScriptedProvider([ProviderResult(text="Réponse du repli")], model="gemini-3.5-flash")
        settings = {**SETTINGS, "fallback_model": "gemini-3.5-flash"}
        with (
            mock.patch.object(tools, "REGISTRY", {}),
            mock.patch.object(budget, "check"),
            mock.patch.object(budget, "record"),
            mock.patch.object(budget, "status", return_value=STATUS_OK),
            mock.patch.object(gateway, "frappe", None),
            mock.patch.object(gateway, "build_provider", return_value=fallback),
        ):
            outcome = gateway.AIGateway(provider=Missing([]), settings=settings).run(
                "Bonjour", None, [], "Société A", "a@test.com"
            )
        self.assertEqual(outcome.text, "Réponse du repli")
        self.assertEqual(outcome.model, "gemini-3.5-flash")

    def test_no_key_means_a_clear_configuration_error(self):
        with self.assertRaises(AIConfigurationError):
            gateway.build_provider({**SETTINGS, "api_key": ""})
        with self.assertRaises(AIConfigurationError):
            gateway.build_provider({**SETTINGS, "enabled": 0})


class TestBudget(unittest.TestCase):
    def test_cost_uses_the_prices_from_settings(self):
        prices = {"price_input_per_mtok": 0.30, "price_output_per_mtok": 2.50}
        self.assertEqual(budget.cost_of(1_000_000, 100_000, prices), 0.55)
        self.assertEqual(budget.cost_of(1_000_000, 100_000, {}), 0)  # sans prix : jetons comptés, coût à zéro

    def test_a_company_limit_overrides_the_default(self):
        settings = {
            "default_monthly_budget": 100.0,
            "default_monthly_token_cap": 0,
            "company_limits": {"Gros client": {"budget": 400.0, "tokens": 0}},
        }
        self.assertEqual(budget.limits_for("Société A", settings), (100.0, 0))
        self.assertEqual(budget.limits_for("Gros client", settings), (400.0, 0))

    def test_zero_means_no_cap(self):
        with mock.patch.object(budget, "month_to_date", return_value={"cost": 9999.0, "tokens": 10**9, "calls": 5}):
            current = budget.status("Société A", {"warn_percent": 80})
        self.assertFalse(current["blocked"])
        self.assertEqual(current["percent"], 0.0)

    def test_reaching_the_cap_blocks_and_warns_before(self):
        settings = {"default_monthly_budget": 100.0, "warn_percent": 80, "company_limits": {}}
        with mock.patch.object(budget, "month_to_date", return_value={"cost": 85.0, "tokens": 0, "calls": 1}):
            self.assertTrue(budget.status("A", settings)["warning"])
            budget.check("A", settings)  # 85 % : encore permis
        with mock.patch.object(budget, "month_to_date", return_value={"cost": 100.0, "tokens": 0, "calls": 1}):
            with self.assertRaises(budget.BudgetExceeded):
                budget.check("A", settings)

    def test_token_cap_works_without_prices(self):
        settings = {"default_monthly_token_cap": 1000, "warn_percent": 80, "company_limits": {}}
        with mock.patch.object(budget, "month_to_date", return_value={"cost": 0.0, "tokens": 1200, "calls": 3}):
            with self.assertRaises(budget.BudgetExceeded):
                budget.check("A", settings)


ECON = {
    **SETTINGS,
    "default_monthly_budget": 60.0,
    "economy_model": "gemini-3.1-flash-lite",
    "economy_cap_percent": 150,
    "economy_price_input_per_mtok": 0.25,
    "economy_price_output_per_mtok": 1.5,
    "price_input_per_mtok": 0.75,
    "price_output_per_mtok": 3.75,
}


class TestEconomyMode(unittest.TestCase):
    def usage(self, cost):
        return mock.patch.object(budget, "month_to_date", return_value={"cost": cost, "tokens": 0, "calls": 1})

    def test_below_the_cap_the_main_model_is_used(self):
        with self.usage(30.0):
            current = budget.status("A", ECON)
        self.assertFalse(current["economy"])
        self.assertFalse(current["blocked"])

    def test_at_the_cap_we_switch_to_the_economy_model_instead_of_refusing(self):
        with self.usage(60.0):
            current = budget.status("A", ECON)
            budget.check("A", ECON)  # ne refuse pas
        self.assertTrue(current["economy"])
        self.assertFalse(current["blocked"])

    def test_far_above_the_cap_we_finally_refuse(self):
        with self.usage(90.0):
            self.assertTrue(budget.status("A", ECON)["blocked"])
            with self.assertRaises(budget.BudgetExceeded):
                budget.check("A", ECON)

    def test_without_an_economy_model_the_cap_refuses_as_before(self):
        with self.usage(60.0):
            current = budget.status("A", {**ECON, "economy_model": ""})
        self.assertTrue(current["blocked"])
        self.assertFalse(current["economy"])

    def test_gateway_answers_with_the_economy_model_tells_the_person_and_prices_it_cheaper(self):
        economy_provider = ScriptedProvider(
            [ProviderResult(text="Réponse économique", input_tokens=1000, output_tokens=100)],
            model="gemini-3.1-flash-lite",
        )
        recorded = []
        with (
            mock.patch.object(tools, "REGISTRY", {}),
            mock.patch.object(budget, "check"),
            mock.patch.object(budget, "record", side_effect=lambda *a, **k: recorded.append(k)),
            mock.patch.object(budget, "status", return_value={**STATUS_OK, "economy": True, "percent": 104.0}),
            mock.patch.object(gateway, "frappe", None),
            mock.patch.object(gateway, "build_provider", return_value=economy_provider) as build,
        ):
            outcome = gateway.AIGateway(provider=ScriptedProvider([]), settings=dict(ECON)).run(
                "Bonjour", None, [], "A", "a@test.com"
            )
        build.assert_called_once()
        self.assertEqual(build.call_args.kwargs["model"], "gemini-3.1-flash-lite")
        self.assertEqual(outcome.model, "gemini-3.1-flash-lite")
        self.assertEqual(recorded[0]["prices"]["price_input_per_mtok"], 0.25)
        risk = next(b for b in outcome.blocks if b["type"] == "risk")
        self.assertIn("plafond", risk["title"].lower())
        self.assertIn("économique", risk["explanation"])

    def test_the_economy_model_is_cheaper_in_the_shipped_defaults(self):
        from cortex_rental.services.ai import settings as ai_settings

        d = ai_settings.DEFAULTS
        self.assertLess(d["economy_price_output_per_mtok"], d["price_output_per_mtok"])
        self.assertLess(d["economy_price_input_per_mtok"], d["price_input_per_mtok"])


class TestPolicyAndDoctypes(unittest.TestCase):
    WRITE_WORDS = ("approve", "confirm", "activate", "delete", "pay", "cancel", "submit", "update")

    def test_no_tool_in_the_registry_can_write_or_approve(self):
        for name in tools.REGISTRY:
            self.assertFalse(any(w in name for w in self.WRITE_WORDS), name)

    def test_quote_tool_only_proposes(self):
        self.assertIn("Ne crée rien", tools.REGISTRY["create_quote_draft"].description)

    def test_every_registered_tool_is_granted_to_at_least_one_agent(self):
        granted = {t for names in AGENT_TOOL_MAP.values() for t in names}
        self.assertTrue(set(tools.REGISTRY) <= granted, set(tools.REGISTRY) - granted)

    def test_finance_tool_is_not_given_to_the_returns_or_availability_agents(self):
        self.assertNotIn("finance_summary", AGENT_TOOL_MAP["cortex-returns"])
        self.assertNotIn("finance_summary", AGENT_TOOL_MAP["cortex-availability"])

    def test_settings_hold_the_key_as_an_encrypted_password_field(self):
        spec = load("doctype", "cortex_ai_settings", "cortex_ai_settings.json")
        fields = {f["fieldname"]: f for f in spec["fields"]}
        self.assertEqual(fields["api_key"]["fieldtype"], "Password")
        self.assertEqual(fields["model"]["default"], "gemini-3.8-flash")
        self.assertEqual({p["role"] for p in spec["permissions"]}, {"System Manager"})
        self.assertEqual(spec["issingle"], 1)

    def test_usage_is_append_only_for_everyone_but_the_gateway(self):
        spec = load("doctype", "cortex_ai_usage", "cortex_ai_usage.json")
        for perm in spec["permissions"]:
            self.assertFalse(perm.get("write") or perm.get("create") or perm.get("delete"), perm)

    def test_the_api_key_is_never_exposed_to_the_browser_code(self):
        root = os.path.join(MODULE_DIR, "public")
        for folder, _, files in os.walk(root):
            for name in files:
                if name.endswith((".js", ".vue", ".css")):
                    with open(os.path.join(folder, name), encoding="utf-8", errors="ignore") as handle:
                        text = handle.read()
                    self.assertNotIn("gemini_api_key", text, name)
                    self.assertNotIn("generativelanguage.googleapis.com", text, name)


if __name__ == "__main__":
    unittest.main()
