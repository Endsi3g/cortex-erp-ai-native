import unittest
import asyncio
import inspect
from cortex_mcp.server import (
    search_rental_items,
    search_customers,
    create_customer_draft,
    check_inventory_availability,
    create_quote_draft,
    submit_approval_request,
    prepare_owner_statement,
)


class TestCortexMCPTools(unittest.TestCase):
    def setUp(self):
        self.company = "CineRental Montreal"

    def test_search_rental_items(self):
        result = asyncio.run(search_rental_items(query="Alexa"))
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("Alexa", result[0]["name"])

    def test_search_customers(self):
        result = asyncio.run(search_customers(query="Dune"))
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("Dune", result[0]["name"])

    def test_create_quote_draft_tool(self):
        result = asyncio.run(
            create_quote_draft(
                customer_id="cust-dune3-01",
                starts_at="2026-09-01T09:00:00Z",
                ends_at="2026-09-08T09:00:00Z",
                lines=[{"item_id": "itm-alexa-35-pkg", "quantity": 3, "unit_rate": 1500.00}],
                evidence_ids=["ev-email-001"],
            )
        )
        self.assertEqual(result["state"], "quote")
        self.assertEqual(result["billable_days"], 3.0)
        self.assertEqual(result["calendar_days"], 7)
        self.assertEqual(result["total"], "13500.00")

    def test_check_availability_tool(self):
        result = asyncio.run(
            check_inventory_availability(
                starts_at="2026-09-01T09:00:00Z",
                ends_at="2026-09-08T09:00:00Z",
                items=[{"item_id": "itm-alexa-35-pkg", "quantity": 3}],
            )
        )
        self.assertIsInstance(result, list)
        self.assertTrue(result[0]["is_available"])

    def test_prepare_owner_statement_tool(self):
        result = asyncio.run(
            prepare_owner_statement(
                owner_id="Roger Deakins Productions Inc.",
                gross_amount=9000.00,
                consignment_percentage=70.0,
                serial_no="SN-ALX35-001",
                days=3.0,
                rate=1500.0,
            )
        )
        self.assertEqual(result["owner_payout_amount"], 6300.00)
        self.assertNotIn("customer_name", result["calculation_snapshot"])

    def test_tools_do_not_accept_a_company_argument(self):
        """
        Regression guard: no MCP tool may expose a `company` parameter.
        The tenant is fixed to this MCP deployment's configured Company —
        an LLM tool call (or an instruction hidden in an ingested
        document) must never be able to redirect a request to another
        tenant by passing `company=...`.
        """
        for tool in (
            search_rental_items,
            search_customers,
            create_customer_draft,
            check_inventory_availability,
            create_quote_draft,
            submit_approval_request,
            prepare_owner_statement,
        ):
            params = inspect.signature(tool).parameters
            self.assertNotIn(
                "company",
                params,
                f"{tool.__name__} must not accept a caller-supplied 'company' argument",
            )


if __name__ == "__main__":
    unittest.main()
