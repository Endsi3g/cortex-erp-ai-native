"""
Unit tests for the Accounting P&L transform/filter logic
(`api/v1/accounting.py`). These are pure Python — no live Frappe/bench
required — unlike `get_profit_and_loss()` itself (the whitelisted
endpoint), which calls into ERPNext's real report engine and is
therefore not covered here (no bench in this sandbox; see HANDOFF.md).

`columns`/`data` below are hand-built to match ERPNext's documented
`profit_and_loss_statement.execute()` shape (see the module docstring
in accounting.py for the exact caveat on how confident that shape is).
"""

import unittest

from cortex_rental.api.v1.accounting import _build_pnl_filters, transform_pnl_report

COLUMNS = [
    {"fieldname": "account", "label": "Account", "fieldtype": "Link"},
    {"fieldname": "oct_2024_dec_2024", "label": "Oct 2024 - Dec 2024", "fieldtype": "Currency"},
    {"fieldname": "jan_2025_mar_2025", "label": "Jan 2025 - Mar 2025", "fieldtype": "Currency"},
    {"fieldname": "currency", "label": "Currency", "fieldtype": "Link"},
]

DATA = [
    {"account": "Income", "account_name": "Income", "indent": 0, "has_value": False, "oct_2024_dec_2024": 0, "jan_2025_mar_2025": 0},
    {
        "account": "Sales",
        "account_name": "Sales",
        "parent_account": "Income",
        "indent": 1,
        "has_value": True,
        "oct_2024_dec_2024": 600000,
        "jan_2025_mar_2025": 400000,
    },
    {
        "account": "Rentals",
        "account_name": "Rentals",
        "parent_account": "Income",
        "indent": 1,
        "has_value": True,
        "oct_2024_dec_2024": 400000,
        "jan_2025_mar_2025": 600000,
    },
    {
        "account_name": "Total Income",
        "indent": 0,
        "oct_2024_dec_2024": 1000000,
        "jan_2025_mar_2025": 1000000,
        "total": 2000000,
    },
    {"account": "Expense", "account_name": "Expense", "indent": 0, "has_value": False, "oct_2024_dec_2024": 0, "jan_2025_mar_2025": 0},
    {
        "account": "Payroll",
        "account_name": "Payroll",
        "parent_account": "Expense",
        "indent": 1,
        "has_value": True,
        "oct_2024_dec_2024": 620000,
        "jan_2025_mar_2025": 620000,
    },
    {
        "account_name": "Total Expense",
        "indent": 0,
        "oct_2024_dec_2024": 620000,
        "jan_2025_mar_2025": 620000,
        "total": 1240000,
    },
    {
        "account_name": "Net Profit",
        "indent": 0,
        "oct_2024_dec_2024": 380000,
        "jan_2025_mar_2025": 380000,
        "total": 760000,
    },
]


class TestTransformPnlReport(unittest.TestCase):
    def test_kpi_totals_come_from_total_rows(self):
        report = transform_pnl_report(COLUMNS, DATA)
        self.assertEqual(report["totalIncome"], 2000000)
        self.assertEqual(report["totalExpense"], 1240000)
        self.assertEqual(report["netProfit"], 760000)

    def test_periods_built_from_period_columns_in_order(self):
        report = transform_pnl_report(COLUMNS, DATA)
        self.assertEqual(len(report["periods"]), 2)
        self.assertEqual(report["periods"][0]["label"], "Oct 2024 - Dec 2024")
        self.assertEqual(report["periods"][0]["income"], 1000000)
        self.assertEqual(report["periods"][0]["expense"], 620000)
        self.assertEqual(report["periods"][0]["profitLoss"], 380000)
        self.assertEqual(report["periods"][1]["income"], 1000000)

    def test_total_and_net_profit_rows_excluded_from_account_tree(self):
        report = transform_pnl_report(COLUMNS, DATA)
        names = [a["name"] for a in report["accounts"]]
        self.assertEqual(names, ["Income", "Expense"])

    def test_account_tree_nests_children_by_indent(self):
        report = transform_pnl_report(COLUMNS, DATA)
        income = report["accounts"][0]
        self.assertEqual(income["type"], "group")
        self.assertEqual([c["name"] for c in income["children"]], ["Sales", "Rentals"])
        self.assertEqual(income["children"][0]["type"], "account")
        self.assertEqual(
            income["children"][0]["values"],
            {"oct_2024_dec_2024": 600000, "jan_2025_mar_2025": 400000},
        )

    def test_falls_back_to_last_period_when_total_row_missing_total_field(self):
        columns = COLUMNS
        data = [row for row in DATA if row.get("account_name") != "Total Income"]
        data.append({"account_name": "Total Income", "indent": 0, "oct_2024_dec_2024": 900000, "jan_2025_mar_2025": 950000})
        report = transform_pnl_report(columns, data)
        self.assertEqual(report["totalIncome"], 950000)

    def test_empty_data_returns_zeroed_report_not_an_error(self):
        report = transform_pnl_report(COLUMNS, [])
        self.assertEqual(report["totalIncome"], 0.0)
        self.assertEqual(report["totalExpense"], 0.0)
        self.assertEqual(report["netProfit"], 0.0)
        self.assertEqual(report["accounts"], [])


class TestBuildPnlFilters(unittest.TestCase):
    def test_company_always_from_server_arg_not_payload(self):
        filters = _build_pnl_filters({"company": "Someone Else Inc", "fiscal_year": "2025"}, "Cortex Test Co A")
        self.assertEqual(filters["company"], "Cortex Test Co A")

    def test_fiscal_year_filter_mode(self):
        filters = _build_pnl_filters({"fiscal_year": "2025"}, "Cortex Test Co A")
        self.assertEqual(filters["filter_based_on"], "Fiscal Year")
        self.assertEqual(filters["from_fiscal_year"], "2025")
        self.assertEqual(filters["to_fiscal_year"], "2025")

    def test_date_range_filter_mode_takes_priority_when_both_given(self):
        filters = _build_pnl_filters(
            {"fiscal_year": "2025", "from_date": "2025-01-01", "to_date": "2025-03-31"}, "Cortex Test Co A"
        )
        self.assertEqual(filters["filter_based_on"], "Date Range")
        self.assertEqual(filters["period_start_date"], "2025-01-01")
        self.assertEqual(filters["period_end_date"], "2025-03-31")

    def test_missing_period_raises(self):
        with self.assertRaises(ValueError):
            _build_pnl_filters({}, "Cortex Test Co A")

    def test_optional_filters_only_forwarded_when_present(self):
        filters = _build_pnl_filters({"fiscal_year": "2025", "cost_center": "Montreal - CTX"}, "Cortex Test Co A")
        self.assertEqual(filters["cost_center"], "Montreal - CTX")
        self.assertNotIn("project", filters)
        self.assertNotIn("finance_book", filters)

    def test_accumulated_values_and_include_default_book_entries_are_coerced_to_int(self):
        filters = _build_pnl_filters(
            {"fiscal_year": "2025", "accumulated_values": "1", "include_default_book_entries": "true"},
            "Cortex Test Co A",
        )
        self.assertEqual(filters["accumulated_values"], 1)
        self.assertEqual(filters["include_default_book_entries"], 1)


if __name__ == "__main__":
    unittest.main()
