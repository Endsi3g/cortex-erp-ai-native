"""Cortex is built on native ERPNext constructions (workspaces, number cards, charts, reports, onboarding).

These tests read the JSON/Python files shipped in the module, so they run without a bench. They guard the layout
the product owner asked for (an Accounting-style workspace) and the removal of Vite/Frappe UI.
"""

import glob
import json
import os
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_DIR = os.path.join(APP_DIR, "cortex_rental")
REPO = os.path.abspath(os.path.join(APP_DIR, "..", "..", ".."))
FROM_ERPNEXT = {"Profit and Loss"}  # standard ERPNext chart reused by the Finance workspace


def _docs(kind):
    out = {}
    for path in sorted(glob.glob(os.path.join(MODULE_DIR, kind, "*", "*.json"))):
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
        out[doc["name"]] = doc
    return out


def _fields(doctype):
    folder = doctype.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(MODULE_DIR, "doctype", folder, f"{folder}.json")
    if not os.path.exists(path):
        return None  # a core Frappe/ERPNext DocType
    with open(path, encoding="utf-8") as handle:
        return {f["fieldname"] for f in json.load(handle)["fields"]} | {
            "name",
            "creation",
            "modified",
            "owner",
            "docstatus",
        }


class TestNoViteLeftovers(unittest.TestCase):
    def test_the_vite_project_and_standalone_app_are_gone(self):
        self.assertFalse(os.path.exists(os.path.join(APP_DIR, "public", "frontend")))
        self.assertFalse(os.path.exists(os.path.join(APP_DIR, "www", "cortex.py")))
        self.assertFalse(os.path.exists(os.path.join(APP_DIR, "public", "js", "cortex_host")))

    def test_no_build_tooling_references_remain(self):
        for parts in (
            ("hooks.py",),
            ("..", "..", "..", "Makefile"),
            ("..", "..", "..", "infra", "docker", "entrypoint-bench.sh"),
        ):
            with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
                text = handle.read()
            for word in ("vite", "npm run", "frappe-ui", "dist-desk", "dist-spa", "cortex_host"):
                self.assertNotIn(word, text.lower(), f"{parts}: {word}")

    def test_no_shell_pages_that_mount_a_bundle(self):
        for path in glob.glob(os.path.join(MODULE_DIR, "page", "*", "*.js")):
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("host.mount", handle.read(), path)


class TestNumberCardsAndCharts(unittest.TestCase):
    def test_number_cards_are_standard_public_and_use_real_fields(self):
        cards = _docs("number_card")
        self.assertGreaterEqual(len(cards), 20)
        for name, card in cards.items():
            self.assertEqual((card["is_standard"], card["is_public"], card["module"]), (1, 1, "Cortex Rental"), name)
            fields = _fields(card["document_type"])
            for row in json.loads(card["filters_json"]) + (
                json.loads(card["dynamic_filters_json"]) if card["dynamic_filters_json"] else []
            ):
                self.assertEqual(row[0], card["document_type"], name)
                if fields is not None:
                    self.assertIn(row[1], fields, f"{name}: {row[1]}")
            if card["function"] != "Count":
                self.assertTrue(card["aggregate_function_based_on"], name)
                if fields is not None:
                    self.assertIn(card["aggregate_function_based_on"], fields, name)

    def test_charts_are_standard_and_use_real_fields(self):
        charts = _docs("dashboard_chart")
        self.assertGreaterEqual(len(charts), 8)
        for name, chart in charts.items():
            self.assertEqual((chart["is_standard"], chart["is_public"]), (1, 1), name)
            fields = _fields(chart["document_type"])
            used = [chart.get("group_by_based_on"), chart.get("based_on"), chart.get("value_based_on")]
            for field in filter(None, used):
                if fields is not None:
                    self.assertIn(field, fields, f"{name}: {field}")

    def test_status_filters_use_declared_select_options(self):
        selects = {}
        for name in (
            "cortex_rental_transaction",
            "approval_request",
            "cortex_inbound_request",
            "consignment_payout",
            "cortex_signup_request",
        ):
            with open(os.path.join(MODULE_DIR, "doctype", name, f"{name}.json"), encoding="utf-8") as handle:
                doc = json.load(handle)
            selects[doc["name"]] = {
                f["fieldname"]: set(f.get("options", "").split("\n"))
                for f in doc["fields"]
                if f["fieldtype"] == "Select"
            }
        for name, card in _docs("number_card").items():
            options = selects.get(card["document_type"])
            if not options:
                continue
            for _dt, field, operator, value in json.loads(card["filters_json"]):
                if field in options:
                    values = value if isinstance(value, list) else [value]
                    self.assertTrue(set(values) <= options[field], f"{name}: {field}={values}")


class TestWorkspacesFollowTheAccountingLayout(unittest.TestCase):
    def _workspaces(self):
        return _docs("workspace")

    def test_every_workspace_has_cards_a_chart_shortcuts_and_link_cards(self):
        for name, ws in self._workspaces().items():
            types = [b["type"] for b in json.loads(ws["content"])]
            for needed in ("chart", "number_card", "shortcut", "card"):
                self.assertIn(needed, types, f"{name} lacks a {needed} block")
            self.assertGreaterEqual(types.count("number_card"), 4, name)

    def test_hub_starts_with_onboarding(self):
        hub = self._workspaces()["Cortex Rental"]
        self.assertEqual(json.loads(hub["content"])[0]["type"], "onboarding")

    def test_referenced_cards_and_charts_exist(self):
        cards, charts = set(_docs("number_card")), set(_docs("dashboard_chart")) | FROM_ERPNEXT
        for name, ws in self._workspaces().items():
            for row in ws["number_cards"]:
                self.assertIn(row["number_card_name"], cards, name)
            for row in ws["charts"]:
                self.assertIn(row["chart_name"], charts, name)

    def test_titles_are_french(self):
        titles = {ws["label"]: ws["title"] for ws in self._workspaces().values()}
        self.assertEqual(titles["Cortex Operations"], "Opérations")
        self.assertEqual(titles["Cortex Warehouse"], "Entrepôt")
        self.assertEqual(titles["Cortex Admin"], "Administration")

    def test_onboarding_steps_exist_and_are_ordered(self):
        onboarding = _docs("module_onboarding")["Cortex Rental"]
        steps = _docs("onboarding_step")
        names = [row["step"] for row in onboarding["steps"]]
        self.assertGreaterEqual(len(names), 5)
        for name in names:
            self.assertIn(name, steps)


class TestScriptReports(unittest.TestCase):
    def test_each_report_ships_python_javascript_and_roles(self):
        reports = _docs("report")
        self.assertEqual(
            set(reports),
            {
                "Disponibilité du parc",
                "Prochains départs et retours",
                "Activité des clients",
                "Versements de consignation",
                "Relevé propriétaire",
            },
        )
        for name, report in reports.items():
            folder = os.path.join(
                MODULE_DIR,
                "report",
                os.path.basename(
                    os.path.dirname(
                        next(
                            p
                            for p in glob.glob(os.path.join(MODULE_DIR, "report", "*", "*.json"))
                            if json.load(open(p, encoding="utf-8"))["name"] == name
                        )
                    )
                ),
            )
            base = os.path.basename(folder)
            self.assertEqual((report["report_type"], report["is_standard"]), ("Script Report", "Yes"), name)
            self.assertTrue(report["roles"], name)
            for ext in ("py", "js"):
                self.assertTrue(os.path.exists(os.path.join(folder, f"{base}.{ext}")), f"{name}.{ext}")
            with open(os.path.join(folder, f"{base}.js"), encoding="utf-8") as handle:
                self.assertIn(f'frappe.query_reports["{name}"]', handle.read())

    def test_reports_read_through_permission_checked_queries_only(self):
        for path in glob.glob(os.path.join(MODULE_DIR, "report", "*", "*.py")):
            if os.path.basename(path) == "__init__.py":
                continue
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            self.assertNotIn("frappe.db.sql", source, path)
            self.assertRegex(source, r"frappe\.get_list|AvailabilityService", path)


if __name__ == "__main__":
    unittest.main()
