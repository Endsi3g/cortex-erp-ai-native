"""Assistant : mode démonstration honnête et résumé de disponibilité (logique pure, sans site)."""

import os
import re
import unittest
from datetime import date, datetime

from cortex_rental.services import availability_summary
from cortex_rental.services.ai import demo

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TODAY = date(2026, 10, 6)


class TestDemoUnderstanding(unittest.TestCase):
    def test_intents(self):
        self.assertEqual(demo.detect("Y a-t-il des retards de retour ?"), "late")
        self.assertEqual(demo.detect("Quelles approbations sont en attente ?"), "approvals")
        self.assertEqual(demo.detect("Qu'est-ce qui est dispo cette semaine ?"), "availability")
        self.assertEqual(demo.detect("Montre-moi le catalogue"), "catalog")
        self.assertEqual(demo.detect("Raconte-moi une blague"), "help")

    def test_late_wins_over_other_words(self):
        # « retard » contient le mot « location » dans la phrase : le retard doit gagner, pas le catalogue.
        self.assertEqual(demo.detect("Quelle location est en retard ?"), "late")

    def test_period_is_parsed_not_guessed(self):
        self.assertEqual(
            demo.parse_period("libres du 20 au 22 octobre ?", TODAY), (date(2026, 10, 20), date(2026, 10, 22))
        )
        self.assertEqual(demo.parse_period("libre le 5 novembre", TODAY), (date(2026, 11, 5), date(2026, 11, 5)))
        self.assertEqual(demo.parse_period("dispo le 3 janvier", TODAY), (date(2027, 1, 3), date(2027, 1, 3)))
        self.assertEqual(demo.parse_period("sur 30 jours", TODAY), (TODAY, date(2026, 11, 4)))

    def test_unclear_period_is_none(self):
        self.assertIsNone(demo.parse_period("libre le 30 février", TODAY))
        self.assertIsNone(demo.parse_period("du 31 au 2 octobre", TODAY))
        self.assertIsNone(demo.parse_period("dispo bientôt", TODAY))

    def test_money_is_french(self):
        self.assertEqual(demo.money(1234.5), "1 234,50 $")

    def test_help_does_not_pretend(self):
        self.assertIn("démonstration", demo.HELP)
        self.assertIn("aucun modèle d'IA", demo.HELP)


class TestAvailabilitySummary(unittest.TestCase):
    def _item(self, blocks, fleet=4):
        return {
            "item_code": "X",
            "item_name": "Caméra",
            "category": "Caméras",
            "fleet_quantity": fleet,
            "blocks": blocks,
        }

    def test_free_when_no_block(self):
        row = availability_summary.summarize([self._item([])], "2026-10-20", "2026-10-22", datetime(2026, 10, 6))[0]
        self.assertEqual((row["status"], row["free"]), ("ok", 4))

    def test_partial_and_worst_day(self):
        blocks = [
            {
                "starts_at": "2026-10-21 00:00:00",
                "ends_at": "2026-10-22 00:00:00",
                "qty": 3,
                "rental_state": "Reservation",
            }
        ]
        row = availability_summary.summarize([self._item(blocks)], "2026-10-20", "2026-10-22", datetime(2026, 10, 6))[0]
        self.assertEqual((row["status"], row["free"], row["booked"]), ("partial", 1, 3))

    def test_full(self):
        blocks = [
            {"starts_at": "2026-10-20 00:00:00", "ends_at": "2026-10-21 00:00:00", "qty": 4, "rental_state": "Contract"}
        ]
        row = availability_summary.summarize([self._item(blocks)], "2026-10-20", "2026-10-20", datetime(2026, 10, 6))[0]
        self.assertEqual((row["status"], row["free"]), ("full", 0))

    def test_quote_holds_only_while_valid(self):
        quote = {
            "starts_at": "2026-10-20 00:00:00",
            "ends_at": "2026-10-21 00:00:00",
            "qty": 2,
            "rental_state": "Quote",
            "hold_until": "2026-10-10 00:00:00",
        }
        live = availability_summary.summarize([self._item([quote])], "2026-10-20", "2026-10-20", datetime(2026, 10, 6))[
            0
        ]
        expired = availability_summary.summarize(
            [self._item([quote])], "2026-10-20", "2026-10-20", datetime(2026, 10, 11)
        )[0]
        self.assertEqual((live["free"], live["held"]), (2, 2))
        self.assertEqual((expired["free"], expired["held"]), (4, 0))

    def test_no_fleet(self):
        row = availability_summary.summarize(
            [self._item([], fleet=0)], "2026-10-20", "2026-10-20", datetime(2026, 10, 6)
        )[0]
        self.assertEqual(row["status"], "none")

    def test_period_limits(self):
        with self.assertRaises(ValueError):
            availability_summary.summarize([], "2026-10-22", "2026-10-20", datetime(2026, 10, 6))
        with self.assertRaises(ValueError):
            availability_summary.summarize([], "2026-01-01", "2026-12-31", datetime(2026, 10, 6))


class TestAssistantContracts(unittest.TestCase):
    def _read(self, *parts):
        with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
            return handle.read()

    def test_demo_seeder_refuses_production(self):
        source = self._read("dev_tools", "jeu_de_demo.py")
        self.assertIn("developer_mode", source)
        self.assertIn("cortex_allow_demo_seed", source)

    def test_proposal_action_matches_schema(self):
        schema = self._read("schemas", "chat_schemas.py")
        actions = set(re.findall(r'"action": "([a-z_]+)"', self._read("services", "ai", "demo.py")))
        for action in actions:
            self.assertIn(f'"{action}"', schema)

    def test_catalogue_search_never_crosses_companies(self):
        source = self._read("services", "ai", "tools.py")
        body = source[source.index("def search_rental_items") :]
        body = body[: body.index("\ndef ", 10)] if "\ndef " in body[10:] else body
        self.assertIn('"company": company', body)

    def test_quote_flow_reads_hold_without_guessing(self):
        flow = self._read("public", "js", "cortex_copilot", "CopilotFlowQuote.vue")
        self.assertIn("hold_status", flow)
        self.assertNotIn("Créer automatiquement", flow)

    def test_proposal_card_creates_nothing_by_itself(self):
        card = self._read("public", "js", "cortex_copilot", "CopilotProposalCard.vue")
        self.assertNotIn("rentals.create_quote_draft", card)
        self.assertNotIn("frappe.call", card)
        self.assertNotIn("customers[0]", card)

    def test_attachments_are_not_offered(self):
        home = self._read("public", "js", "cortex_home", "CortexHome.vue")
        self.assertNotIn('type="file"', home)
        self.assertNotIn("triggerFileInput", home)

    def test_flows_use_explicit_methods(self):
        for name in ("CopilotFlowQuote.vue", "CopilotFlowAvailability.vue", "CopilotFlowApprovals.vue"):
            source = self._read("public", "js", "cortex_copilot", name)
            self.assertNotIn("frappe.call(", source, name)  # tout passe par apiCall, qui fixe GET/POST


class TestChatPresentation(unittest.TestCase):
    def _read(self, *parts):
        with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
            return handle.read()

    def test_unknown_block_type_is_never_shown_as_an_error(self):
        conversation = self._read("public", "js", "cortex_copilot", "CopilotConversation.vue")
        self.assertNotIn("Type de contenu non reconnu", conversation)
        self.assertIn("assistant_text", conversation)

    def test_answers_are_plain_text_not_green_cards(self):
        for name in ("CopilotVerifiedFact.vue", "CopilotProposalCard.vue", "CopilotRiskCard.vue"):
            source = self._read("public", "js", "cortex_copilot", name)
            self.assertNotIn("success-50", source, name)
            self.assertNotIn("primary-50", source, name)
            self.assertNotIn("#f6fbf8", source, name)

    def test_composer_has_no_shadow_and_is_docked(self):
        home = self._read("public", "js", "cortex_home", "CortexHome.vue")
        composer = home[
            home.index(".ch-composer {") : home.index(".ch-attachments") if ".ch-attachments" in home else None
        ]
        self.assertIn("box-shadow: none", composer)
        self.assertIn("overflow-y: auto", home[home.index(".ch-thread {") :][:300])
        self.assertNotIn("position: sticky", home[home.index(".is-chat .ch-composer") :][:200])

    def test_reveal_respects_reduced_motion(self):
        text = self._read("public", "js", "cortex_copilot", "CopilotAssistantText.vue")
        self.assertIn("prefers-reduced-motion", text)

    def test_tier_is_sent_as_a_key_never_a_model_id(self):
        schema = self._read("schemas", "chat_schemas.py")
        self.assertIn('Literal["rapide", "equilibre", "avance"]', schema)


if __name__ == "__main__":
    unittest.main()
