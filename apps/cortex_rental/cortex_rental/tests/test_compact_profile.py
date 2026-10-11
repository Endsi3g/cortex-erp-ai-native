"""Profil « compact » des petits modèles (Gemma 4) : outils choisis sans modèle, consignes courtes, délais (sans banc Frappe)."""

import json
import unittest
from unittest import mock

from cortex_rental.services import tool_policy
from cortex_rental.services.ai import budget, gateway, settings as ai_settings, tool_routing, tools
from cortex_rental.services.ai.providers import (
    AIProviderError,
    LocalOpenAIProvider,
    ProviderResult,
    ScriptedProvider,
)
from cortex_rental.tests.test_ai_gateway import SETTINGS, STATUS_OK

ALLOWED = tool_policy.AGENT_TOOL_MAP["cortex-operations"]


class TestRouting(unittest.TestCase):
    def pick(self, message, previous=""):
        return tool_routing.select_tools(message, ALLOWED, previous=previous)

    def test_reading_requests_get_reading_tools_and_never_a_proposal(self):
        for message in (
            "Quelles sont mes locations en état devis ?",
            "Y a-t-il des retards de retour ?",
            "Donne-moi la situation de ma société",
            "Combien de factures sont en retard ?",
            "Quels devis sont en retenue ?",
            "bla bla ???",
        ):
            picked = self.pick(message)
            self.assertTrue(picked, message)
            self.assertFalse([n for n in picked if n.startswith("propose_")], message)

    def test_action_requests_get_the_matching_proposal_and_its_lookup_tools_only(self):
        cases = {
            "Change le tarif journalier de CAM-1 à 175 $": ("propose_update_field", {"find_records", "get_record"}),
            "Crée un client Studio Test": ("propose_create_customer", {"search_customers"}),
            "Prépare un devis pour Studio Boréal du 24 au 27 novembre": (
                "propose_create_quote",
                {"search_customers", "search_rental_items", "check_inventory_availability"},
            ),
            "Libère la retenue du devis le plus récent": ("propose_release_hold", {"list_rentals"}),
            "Renouvelle la retenue du devis CR-1": ("propose_renew_hold", {"list_rentals"}),
            "Réserve le devis CR-1": ("propose_request_reservation", {"list_rentals"}),
            "Le client a payé la facture par chèque": ("propose_record_payment", {"list_invoices"}),
            "Approuve la demande APPR-1": ("propose_decide_approval", {"list_pending_approvals"}),
            "Ajoute la catégorie Drones": ("propose_add_category", set()),
            "Applique le modèle de secteur cinéma": ("propose_apply_sector_template", set()),
        }
        for message, (proposal, reads) in cases.items():
            picked = self.pick(message)
            self.assertEqual([n for n in picked if n.startswith("propose_")], [proposal], message)
            self.assertEqual({n for n in picked if not n.startswith("propose_")}, reads, message)

    def test_smalltalk_gets_no_tools_but_a_real_question_still_does(self):
        for message in ("Bonjour", "Bonjour, tu peux m'aider ?", "Merci beaucoup !", "Salut"):
            self.assertEqual(self.pick(message), [], message)
        self.assertTrue(self.pick("Aide-moi à voir mes devis"))
        self.assertTrue(self.pick("Bonjour, combien de devis ai-je ?"))

    def test_generic_readers_only_when_a_detail_or_an_identifier_is_asked(self):
        generic = {"find_records", "get_record"}
        for message in (
            "Combien de locations sont en état devis ?",
            "Quels retours sont en retard ?",
            "Est-ce que la caméra Alexa Mini est disponible ?",
            "Que sais-tu du client Studio Boréal ?",
        ):
            self.assertFalse(generic & set(self.pick(message)), message)
        for message in ("Donne-moi le détail de CR-TRX-2026-00209", "Que contient la fiche de FAC-2026-00952 ?"):
            self.assertTrue(generic <= set(self.pick(message)), message)

    def test_late_returns_are_offered_for_a_lateness_question_only(self):
        self.assertIn("late_returns", self.pick("Quels retours sont en retard ?"))
        self.assertNotIn("late_returns", self.pick("Combien de locations sont en état devis ?"))

    def test_follow_up_without_keywords_uses_the_previous_request(self):
        picked = self.pick("oui, fais-le", previous="Change le tarif de CAM-1 à 200")
        self.assertIn("propose_update_field", picked)

    def test_never_more_than_the_policy_allows_nor_than_the_cap(self):
        restricted = ["list_rentals", "propose_create_quote"]
        self.assertEqual(
            set(tool_routing.select_tools("Prépare un devis", restricted)),
            {"list_rentals", "propose_create_quote"} & {"propose_create_quote"},
        )
        for message in (
            "devis facture client location disponibilité retard approbation",
            "crée un devis et libère la retenue",
        ):
            self.assertLessEqual(len(self.pick(message)), tool_routing.MAX_TOOLS)
        self.assertEqual(tool_routing.select_tools("n'importe quoi", []), [])

    def test_whole_words_only(self):
        # « renouvelle » ne doit pas déclencher « nouvelle » (créer).
        self.assertNotIn("propose_create_quote", self.pick("Renouvelle la retenue du devis CR-1"))

    def test_compact_offers_far_fewer_tools_than_the_full_profile(self):
        self.assertLessEqual(len(self.pick("Quelles sont mes locations ?")), 6)
        self.assertGreater(len(ALLOWED), 20)


class TestCompactGateway(unittest.TestCase):
    def run_gateway(self, message, tier):
        provider = ScriptedProvider([ProviderResult(text="Voici.", tool_calls=[], input_tokens=1, output_tokens=1)])
        settings = {**SETTINGS, **{k: v for k, v in ai_settings.DEFAULTS.items() if k.startswith("tier_")}}
        gw = gateway.AIGateway(provider=provider, settings=settings)
        gw.tier = tier
        registry = {n: tools.REGISTRY[n] for n in ALLOWED if n in tools.REGISTRY}
        with (
            mock.patch.object(tools, "REGISTRY", registry),
            mock.patch.object(tools, "actions_enabled", return_value=True),
            mock.patch.object(budget, "check"),
            mock.patch.object(budget, "record"),
            mock.patch.object(budget, "status", return_value=STATUS_OK),
            mock.patch.object(gateway, "frappe", None),
        ):
            gw.run(message=message, history=[], allowed_tools=ALLOWED, company="Société A", user="a@test.com")
        return provider.calls[0]

    def test_compact_tier_sends_few_tools_and_the_short_prompt(self):
        compact = self.run_gateway("Change le tarif de CAM-1 à 175 $", {"key": "local", "compact": True})
        full = self.run_gateway("Change le tarif de CAM-1 à 175 $", {"key": "rapide", "compact": False})
        self.assertEqual(sorted(compact["tools"]), ["find_records", "get_record", "propose_update_field"])
        self.assertGreater(len(full["tools"]), 15)
        self.assertLess(len(compact["system"]), len(full["system"]) / 2)
        self.assertIn("propose_", compact["system"])
        self.assertIn("jamais « c'est fait »".replace("jamais « c'est fait »", "Ne dis jamais"), compact["system"])

    def test_compact_declarations_have_short_descriptions(self):
        for name in ("find_records", "propose_update_field", "list_rentals"):
            full = tools.REGISTRY[name].declaration()
            short = tools.REGISTRY[name].declaration(compact=True)
            self.assertLessEqual(len(short["description"]), 200, name)
            self.assertLessEqual(len(short["description"]), len(full["description"]), name)
            self.assertEqual(short["parameters"], full["parameters"])  # les paramètres restent entiers

    def test_a_tool_outside_the_routed_subset_is_refused(self):
        provider = ScriptedProvider(
            [
                ProviderResult(
                    text="", tool_calls=[gateway_tool_call("propose_record_payment")], input_tokens=1, output_tokens=1
                ),
                ProviderResult(text="Ok.", tool_calls=[], input_tokens=1, output_tokens=1),
            ]
        )
        gw = gateway.AIGateway(provider=provider, settings=dict(SETTINGS))
        gw.tier = {"key": "local", "compact": True}
        registry = {n: tools.REGISTRY[n] for n in ALLOWED if n in tools.REGISTRY}
        executed = []
        with (
            mock.patch.object(tools, "REGISTRY", registry),
            mock.patch.object(tools, "actions_enabled", return_value=True),
            mock.patch.object(tools, "execute", side_effect=lambda n, a: executed.append(n) or {}),
            mock.patch.object(budget, "check"),
            mock.patch.object(budget, "record"),
            mock.patch.object(budget, "status", return_value=STATUS_OK),
            mock.patch.object(gateway, "frappe", None),
        ):
            gw.run(
                message="Quelles sont mes locations ?",
                history=[],
                allowed_tools=ALLOWED,
                company="S",
                user="a@test.com",
            )
        self.assertEqual(executed, [])  # un outil de paiement, jamais offert pour une simple lecture, n'est pas exécuté


def gateway_tool_call(name):
    from cortex_rental.services.ai.providers import ToolCall

    return ToolCall(name=name, args={}, id="x")


class TestTierTimeouts(unittest.TestCase):
    def test_compact_flag_and_timeouts_per_tier(self):
        values = dict(ai_settings.DEFAULTS)
        values.update(
            api_key="g", local_base_url="http://x", anthropic_api_key="", openai_api_key="", company_limits={}
        )
        rows = {t["key"]: t for t in ai_settings.tiers(values)}
        self.assertTrue(rows["gemma"]["compact"] and rows["local"]["compact"])
        self.assertFalse(rows["rapide"]["compact"] or rows["equilibre"]["compact"] or rows["avance"]["compact"])
        self.assertEqual(rows["local"]["timeout"], 600)
        self.assertEqual(rows["gemma"]["timeout"], 90)
        self.assertEqual(rows["rapide"]["timeout"], int(values["timeout_seconds"]))

    def test_local_provider_never_retries_a_slow_model_and_says_why(self):
        provider = LocalOpenAIProvider("ai/gemma4", "", timeout=300)
        self.assertEqual(provider.attempts, 1)
        self.assertIn("carte graphique", provider.timeout_message())
        self.assertIn(str(provider.timeout), provider.timeout_message())

    def test_local_timeout_stays_under_the_web_server_limit(self):
        fake = mock.Mock()
        fake.conf = {"http_timeout": 120}
        with mock.patch.dict("sys.modules", {"frappe": fake}):
            self.assertEqual(LocalOpenAIProvider("ai/gemma4", "", timeout=600).timeout, 110)
            fake.conf = {"http_timeout": 900}
            self.assertEqual(LocalOpenAIProvider("ai/gemma4", "", timeout=600).timeout, 600)
        self.assertIsInstance(AIProviderError("x"), RuntimeError)


class TestModelView(unittest.TestCase):
    """Les cartes d'interface ne sont pas renvoyées au modèle (jetons), mais les chiffres de l'outil le sont."""

    def test_ui_blocks_are_replaced_by_a_marker_and_data_stays(self):
        from cortex_rental.services.ai.gateway import model_view

        output = {
            "par_etat": {"Devis": 36},
            "stat_block": {"type": "stat_card", "title": "Locations par état", "series": {"values": [36.0] * 200}},
        }
        view = model_view(output)
        self.assertNotIn("stat_block", view)
        self.assertEqual(view["par_etat"], {"Devis": 36})
        self.assertEqual(view["carte_affichee_a_la_personne"], "Locations par état")
        self.assertIn("stat_block", output)  # l'original (envoyé à l'écran) n'est pas touché
        self.assertLess(len(json.dumps(view)), len(json.dumps(output)) / 3)

    def test_action_card_is_summarised_and_plain_outputs_are_untouched(self):
        from cortex_rental.services.ai.gateway import model_view

        view = model_view({"status": "proposed", "action_block": {"title": "Créer un client", "rows": [1] * 50}})
        self.assertEqual(view["carte_affichee_a_la_personne"], "Créer un client")
        self.assertEqual(view["status"], "proposed")
        plain = {"rentals": [{"name": "A"}], "total": 1}
        self.assertIs(model_view(plain), plain)
        self.assertEqual(model_view({"error": "x"}), {"error": "x"})


if __name__ == "__main__":
    unittest.main()
