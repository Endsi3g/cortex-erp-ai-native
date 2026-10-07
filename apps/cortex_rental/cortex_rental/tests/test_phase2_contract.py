"""Contrat statique de la phase 2 (locations, disponibilité, navigation, saisie vocale).

Ces vérifications lisent le code : elles ne remplacent pas un essai sur un Desk Frappe actif, qui reste à faire.
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class TestPhase2Contract(unittest.TestCase):
    def test_loading_indicator_is_registered_and_respects_reduced_motion(self):
        self.assertIn("/assets/cortex_rental/js/cortex_loading.js", read("hooks.py"))
        css = read("public", "css", "cortex-motion.css")
        block = css.split(".cx-route-bar", 1)[1]
        self.assertIn("prefers-reduced-motion: reduce", block)
        self.assertIn("animation: none", block.split("prefers-reduced-motion: reduce", 1)[1])

    def test_sidebar_collapse_is_at_the_bottom_and_auto_collapses_on_the_assistant(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertIn('class: "cx-nav-foot"', js)
        self.assertNotIn("head.append(brand, toggle)", js)
        self.assertIn('=== "cortex-home"', js)
        # Une préférence explicite de la personne gagne toujours.
        self.assertRegex(js, r"autoCollapse\(\) \{\s+if \(store\(STORE\) !== null\) return;")

    def test_collapsed_rail_hides_sub_groups(self):
        css = read("public", "css", "cortex-nav.css")
        self.assertRegex(css, r"body\.cx-nav-collapsed \.cx-sub \{\s+display: none;")

    def test_project_label_is_french_with_a_capital_n(self):
        doctype = json.loads(
            read("cortex_rental", "doctype", "cortex_rental_transaction", "cortex_rental_transaction.json")
        )
        field = next(f for f in doctype["fields"] if f["fieldname"] == "project_name")
        self.assertEqual(field["label"], "Nom du projet")

    def test_voice_input_uses_the_shared_module_and_never_fails_silently(self):
        vue = read("public", "js", "cortex_home", "CortexHome.vue")
        self.assertIn("cortexVoice.js", vue)
        self.assertNotIn("speechRec.onerror = () => {\n\t\t\tisListening.value = false;\n\t\t};", vue)
        self.assertIn('role="status"', vue)

    def test_company_page_offers_statistics_with_a_dedicated_endpoint(self):
        self.assertIn("def company_stats", read("api", "v1", "account.py"))
        self.assertIn('call("company_stats")', read("cortex_rental", "page", "cortex_account", "cortex_account.js"))

    def test_new_endpoints_are_read_only_gets(self):
        source = read("api", "v1", "account.py")
        decorator = source.split("def company_stats", 1)[0].rsplit("@frappe.whitelist", 1)[1]
        self.assertTrue(decorator.startswith('(methods=["GET"])'))
        self.assertTrue(re.search(r"@defense\.safe_input", source.split("def company_stats", 1)[0][-200:]))


if __name__ == "__main__":
    unittest.main()
