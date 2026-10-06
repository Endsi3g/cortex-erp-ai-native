"""Cortex is built on native ERPNext constructions (workspaces, number cards, charts, reports, onboarding).

These tests read the JSON/Python files shipped in the module, so they run without a bench. They guard the layout
the product owner asked for (an Accounting-style workspace) and the removal of Vite/Frappe UI.
"""

import glob
import json
import os
import unicodedata
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

    def test_workspaces_no_longer_embed_the_native_onboarding_block(self):
        # L'assistant plein écran (page cortex-setup) et la carte d'accueil remplacent le guide natif.
        for name, ws in self._workspaces().items():
            types = [b["type"] for b in json.loads(ws["content"])]
            self.assertNotIn("onboarding", types, name)

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


class TestAccessibilityAndAvailabilityGrid(unittest.TestCase):
    def test_accessibility_shim_and_styles_are_loaded_in_the_desk(self):
        with open(os.path.join(APP_DIR, "hooks.py"), encoding="utf-8") as handle:
            hooks = handle.read()
        for asset in ("cortex_a11y.js", "cortex-a11y.css", "cortex_views.js", "cortex_desk.js"):
            self.assertIn(asset, hooks)
            folder = "css" if asset.endswith(".css") else "js"
            self.assertTrue(os.path.exists(os.path.join(APP_DIR, "public", folder, asset)), asset)

    def test_availability_grid_page_ships_its_bundle_and_reads_the_server_matrix(self):
        page = os.path.join(MODULE_DIR, "page", "cortex_availability")
        for name in ("__init__.py", "cortex_availability.json", "cortex_availability.js"):
            self.assertTrue(os.path.exists(os.path.join(page, name)), name)
        bundle = os.path.join(APP_DIR, "public", "js", "cortex_availability")
        with open(os.path.join(bundle, "CortexAvailability.vue"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("cortex_rental.api.v1.availability.get_matrix", source)
        self.assertIn("revérifie", source, "the grid must say the server re-checks availability")
        self.assertTrue(os.path.exists(os.path.join(bundle, "cortex_availability.bundle.js")))

    def test_workspaces_link_the_grid_page(self):
        linked = [
            name
            for name, doc in _docs("workspace").items()
            if any(s["link_to"] == "cortex-availability" for s in doc.get("shortcuts", []))
        ]
        self.assertTrue(linked)


class TestMultiTenantNaming(unittest.TestCase):
    def test_pricing_rule_names_do_not_depend_on_the_rule_label(self):
        # Found by the 3-month simulation: two companies with the same default rule label collided on the record name.
        path = os.path.join(MODULE_DIR, "doctype", "rental_pricing_rule", "rental_pricing_rule.json")
        with open(path, encoding="utf-8") as handle:
            autoname = json.load(handle)["autoname"]
        self.assertNotIn("rule_name", autoname)


class TestSerialAllocationIsDateAware(unittest.TestCase):
    def test_serial_allocation_only_excludes_overlapping_reservations(self):
        # Found by the simulation: a unit reserved for one date blocked it for every other date.
        path = os.path.join(MODULE_DIR, "doctype", "cortex_rental_transaction", "cortex_rental_transaction.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("tx.starts_at < %(ends_at)s", source)
        self.assertIn("tx.ends_at > %(starts_at)s", source)


class TestDoctypePermissions(unittest.TestCase):
    """Found by the 3-month simulation: real approvers could not decide, and operators could edit decisions."""

    def _perms(self, name):
        path = os.path.join(MODULE_DIR, "doctype", name, f"{name}.json")
        with open(path, encoding="utf-8") as handle:
            return {p["role"]: p for p in json.load(handle)["permissions"]}

    def test_approvers_can_write_approval_requests_and_operators_cannot(self):
        perms = self._perms("approval_request")
        for role in ("Rental Manager", "Cortex Account Reviewer"):
            self.assertEqual(perms[role].get("write"), 1, role)
        for role in ("Rental Operator", "Cortex Counter Staff", "Agent Service Account"):
            self.assertFalse(perms[role].get("write"), role)

    def test_domain_roles_have_access_to_their_own_records(self):
        self.assertEqual(self._perms("consignment_payout")["Cortex Finance Manager"].get("write"), 1)
        self.assertEqual(self._perms("consignment_owner")["Cortex Consignment Manager"].get("write"), 1)
        self.assertEqual(self._perms("rental_pricing_rule")["Rental Manager"].get("write"), 1)
        self.assertEqual(self._perms("audit_event")["Rental Manager"].get("read"), 1)


class TestReportAndPrintRights(unittest.TestCase):
    """Found by the stress test: managers could not run reports, export or print contracts."""

    def test_managers_can_report_export_and_print_rentals(self):
        path = os.path.join(MODULE_DIR, "doctype", "cortex_rental_transaction", "cortex_rental_transaction.json")
        with open(path, encoding="utf-8") as handle:
            perms = {p["role"]: p for p in json.load(handle)["permissions"]}
        for role in ("Rental Manager", "Cortex Operations Manager"):
            for right in ("report", "export", "print"):
                self.assertEqual(perms[role].get(right), 1, f"{role}:{right}")
        self.assertEqual(perms["Cortex Counter Staff"].get("print"), 1)

    def test_customer_permissions_are_granted_to_cortex_roles(self):
        from cortex_rental import setup

        self.assertIn("Rental Manager", setup.CUSTOMER_EDITORS)
        self.assertIn("Cortex Counter Staff", setup.CUSTOMER_EDITORS)
        self.assertTrue(set(setup.CUSTOMER_EDITORS).isdisjoint(setup.CUSTOMER_READERS))

    def test_customer_activity_report_does_not_require_customer_rights(self):
        path = os.path.join(MODULE_DIR, "report", "activité_des_clients", "activité_des_clients.json")
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["ref_doctype"], "Cortex Rental Transaction")


class TestLandingAndWorkspaceDesign(unittest.TestCase):
    def test_people_land_on_the_cortex_rental_workspace(self):
        from cortex_rental import auth_hooks

        self.assertEqual(auth_hooks.HOME_ROUTE, "cortex-rental")

    def test_number_cards_are_black_except_the_ones_that_need_attention(self):
        cards = {}
        for path in glob.glob(os.path.join(MODULE_DIR, "number_card", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                card = json.load(handle)
            cards[card["name"]] = card.get("color") or ""
        self.assertEqual(cards["Locations en cours"], "")
        self.assertEqual(cards["Départs du jour"], "")
        self.assertNotEqual(cards["Approbations en attente"], "")


class TestFrenchTranslations(unittest.TestCase):
    def test_translation_file_is_well_formed_and_names_doctypes(self):
        import csv

        with open(os.path.join(APP_DIR, "translations", "fr.csv"), encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        # source, traduction et, facultatif, le contexte (« msgctxt » de Frappe)
        self.assertTrue(all(len(row) in (2, 3) and row[0] and row[1] for row in rows))
        keys = [(row[0], row[2] if len(row) == 3 else "") for row in rows]
        self.assertEqual(len(keys), len(set(keys)), "duplicate translation keys")
        for doctype in ("Cortex Rental Transaction", "Approval Request", "Consignment Payout", "Rental Pricing Rule"):
            self.assertIn((doctype, ""), keys)


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
                "Créances par client",
                "Taxes perçues",
                "Journal comptable",
                "Balance de vérification",
                "Utilisation IA",
                "Utilisation du parc",
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
            # Frappe imports `report.<scrub(name)>.<scrub(name)>`: the folder must match exactly (accents included).
            self.assertEqual(base, unicodedata.normalize("NFC", name.replace(" ", "_").replace("-", "_").lower()))
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
