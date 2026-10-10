"""Cartes de statistiques de l'assistant : chiffres réels, liens sûrs, schéma valide (sans banc Frappe)."""

import unittest
from unittest import mock

from pydantic import TypeAdapter

from cortex_rental.schemas.chat_schemas import ChatBlock
from cortex_rental.services.ai import gateway, stats, tools
from cortex_rental.services.tool_policy import AGENT_TOOL_MAP


class TestStatsPure(unittest.TestCase):
    def test_href_only_allows_desk_paths(self):
        for good in (
            "/app/cortex-finance",
            "/app/cortex-rental-transaction?rental_state=Checked%20Out",
            "/app/customer/CUST-1",
        ):
            self.assertEqual(stats.safe_href(good), good)
        self.assertEqual(stats.safe_href("/app/cortex-finance"), "/app/cortex-finance")
        for bad in (
            "https://evil.example/app/x",
            "//evil.example",
            "/app/../etc/passwd",
            "javascript:alert(1)",
            "/api/method/x",
            "",
            None,
            "/app/x y",
        ):
            self.assertEqual(stats.safe_href(bad), "", bad)

    def test_money_uses_canadian_french_format(self):
        self.assertEqual(stats.money(1234.5), "1 234,50 $")
        self.assertEqual(stats.money(0), "0,00 $")
        self.assertEqual(stats.money(-12), "-12,00 $")

    def test_last_months_crosses_the_year_and_is_oldest_first(self):
        self.assertEqual(stats.last_months((2026, 2, 10), 4), [(2025, 11), (2025, 12), (2026, 1), (2026, 2)])

    def test_monthly_totals_sums_by_month_and_zero_fills(self):
        rows = [
            {"issue_date": "2026-08-03", "total": 100},
            {"issue_date": "2026-08-20", "total": 50.5},
            {"issue_date": "2026-10-01", "total": 20},
            {"issue_date": "2026-01-01", "total": 999},  # hors période : ignoré
        ]
        labels, values = stats.monthly_totals(rows, (2026, 10, 10), 3, "total", "issue_date")
        self.assertEqual(values, [150.5, 0.0, 20.0])
        self.assertEqual(len(labels), 3)

    def test_card_drops_an_unsafe_link_but_keeps_the_numbers(self):
        card = stats.card("T", "Ouvrir", "https://evil.example", kpis=[stats.kpi_block("A", "1")])
        self.assertEqual(card["source_href"], "")
        self.assertEqual(card["kpis"][0]["value"], "1")

    def test_card_validates_against_the_chat_schema(self):
        card = stats.card(
            "Locations par état",
            "Ouvrir les locations",
            "/app/cortex-rental-transaction",
            kpis=[stats.kpi_block("Total", "5", tone="good")],
            series=stats.series_block("bar", ["Devis", "Sortie"], [3, 2], "locations"),
        )
        TypeAdapter(ChatBlock).validate_python(card)


class FakeRow(dict):
    __getattr__ = dict.get


class TestStatTools(unittest.TestCase):
    def fake_frappe(self, lists):
        from datetime import datetime
        from types import SimpleNamespace

        def get_list(doctype, **kw):
            return lists[doctype]

        return SimpleNamespace(
            has_permission=lambda *a, **k: True,
            get_list=get_list,
            utils=SimpleNamespace(now_datetime=lambda: datetime(2026, 10, 10, 12, 0)),
        )

    def test_rentals_by_state_reports_real_counts_with_a_link(self):
        fake = self.fake_frappe(
            {
                "Cortex Rental Transaction": [
                    FakeRow(rental_state="Quote", n=3),
                    FakeRow(rental_state="Checked Out", n=2),
                ]
            }
        )
        with mock.patch.object(tools, "frappe", fake), mock.patch.object(tools, "_company", return_value="Société A"):
            out = tools.rentals_by_state()
        self.assertEqual(out["par_etat"], {"Devis": 3, "Sortie": 2})
        block = out["stat_block"]
        self.assertEqual(block["series"]["values"], [3.0, 2.0])
        self.assertEqual(block["source_href"], "/app/cortex-rental-transaction")
        TypeAdapter(ChatBlock).validate_python(block)

    def test_finance_trend_aggregates_invoices_and_payments(self):
        fake = self.fake_frappe(
            {
                "Cortex Rental Invoice": [
                    FakeRow(issue_date="2026-10-02", total=100),
                    FakeRow(issue_date="2026-09-15", total=40),
                ],
                "Cortex Rental Payment": [FakeRow(paid_on="2026-10-05", signed_amount=60)],
            }
        )
        with mock.patch.object(tools, "frappe", fake), mock.patch.object(tools, "_company", return_value="Société A"):
            out = tools.finance_trend(3)
        self.assertEqual(out["facture"][-2:], [40.0, 100.0])
        self.assertEqual(out["encaisse"][-1], 60.0)
        TypeAdapter(ChatBlock).validate_python(out["stat_block"])

    def test_no_access_means_an_error_not_an_empty_chart(self):
        from types import SimpleNamespace

        denied = SimpleNamespace(has_permission=lambda *a, **k: False)
        with mock.patch.object(tools, "frappe", denied):
            self.assertIn("error", tools.finance_trend())
            self.assertIn("error", tools.rentals_by_state())

    def test_stat_tools_are_granted_and_labelled(self):
        for name in ("finance_trend", "rentals_by_state"):
            self.assertIn(name, AGENT_TOOL_MAP["cortex-operations"])
            self.assertIn(name, gateway.TOOL_LABELS)

    def test_gateway_shows_the_stat_block_from_a_tool(self):
        block = stats.card("T", "Ouvrir", "/app/cortex-finance")
        # Le bloc est ajouté tel quel à la réponse (voir AIGateway.run : `output["stat_block"]`).
        self.assertIn('output.get("stat_block")', open(gateway.__file__, encoding="utf-8").read())
        self.assertEqual(block["type"], "stat_card")


if __name__ == "__main__":
    unittest.main()
