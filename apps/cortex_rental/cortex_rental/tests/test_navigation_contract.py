"""Contrat de la navigation : groupes repliables, fil d'Ariane et titres tirés d'une seule source (sans navigateur)."""

import os
import re
import unittest

BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestNavigationContract(unittest.TestCase):
    def setUp(self):
        self.nav = read("js", "cortex_nav.js")
        self.pages = read("js", "cortex_pages.js")

    def group_titles(self):
        return re.findall(r'title: "([^"]+)",\n(?:\s*(?:pinned|bottom): true,\n)*\s*items', self.nav)

    def test_operations_and_assistant_are_always_open_the_rest_on_demand(self):
        self.assertRegex(self.nav, r'title: "Opérations",\n\s*pinned: true')
        self.assertRegex(self.nav, r'title: "Assistant",\n\s*pinned: true')
        self.assertIn("group.pinned ||", self.nav)

    def test_every_group_is_collapsible_and_remembers_its_state(self):
        self.assertIn("cx-group-title", self.nav)
        self.assertIn("aria-expanded", self.nav)
        self.assertIn("GROUP_STORE", self.nav)

    def test_without_a_saved_choice_only_the_current_group_is_open(self):
        self.assertIn("stored === undefined", self.nav)

    def test_nav_is_the_single_source_for_breadcrumbs_and_titles(self):
        self.assertIn("cortex.NAV", self.nav)
        self.assertIn("cortex.NAV.locate", self.pages)
        self.assertIn("frappe.breadcrumbs.update", self.pages)

    def test_breadcrumbs_have_no_leading_arrow(self):
        css = read("css", "cortex-nav.css")
        self.assertRegex(css, r"#navbar-breadcrumbs li::before\s*\{\s*content:\s*none")

    def test_group_labels_are_unique_and_french(self):
        titles = self.group_titles()
        self.assertEqual(len(titles), len(set(titles)))
        self.assertTrue({"Opérations", "Assistant", "Parc", "Clients et finance", "Administration"} <= set(titles))

    def test_the_assistant_group_is_second(self):
        order = self.group_titles()
        self.assertEqual(order[1], "Assistant")

    def test_administration_sits_at_the_bottom(self):
        self.assertIn("cx-group-bottom", self.nav)

    def test_list_dates_do_not_depend_on_the_moment_locale(self):
        views = read("js", "cortex_views.js")
        self.assertIn("Intl.DateTimeFormat", views)


if __name__ == "__main__":
    unittest.main()
