"""Navigation, aide, support et activité d'équipe (sans banc Frappe)."""

import json
import os
import re
import unittest

from cortex_rental import hooks
from cortex_rental.services import team_activity

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestNavigationAssets(unittest.TestCase):
    def test_nav_assets_are_loaded_on_every_desk_page(self):
        self.assertIn("/assets/cortex_rental/js/cortex_nav.js", hooks.app_include_js)
        self.assertIn("/assets/cortex_rental/css/cortex-nav.css", hooks.app_include_css)

    def test_nav_never_links_to_accounting_modules_the_owner_cannot_open(self):
        js = read("public", "js", "cortex_nav.js")
        for forbidden in (
            "/app/accounting",
            "/app/selling",
            "/app/stock",
            "/app/quality",
            "/app/support",
            "/app/sales-invoice",
        ):
            self.assertNotIn(forbidden, js)

    def test_admin_items_are_role_gated(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertRegex(js, r'id: "settings".*hasRole\("System Manager"\)')
        self.assertIn('workspace("Cortex Admin")', js)

    def test_nav_is_a_drawer_on_phones_and_respects_reduced_motion(self):
        css = read("public", "css", "cortex-nav.css")
        self.assertIn("max-width: 768px", css)
        self.assertIn("translateX(-100%)", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_search_placeholder_is_short_enough_not_to_be_cut(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertRegex(js, r'setAttribute\("placeholder", __\("Rechercher…"\)\)')


class TestHelpMenuAndSupport(unittest.TestCase):
    def test_help_menu_offers_the_assistant_and_support_not_frappe_links(self):
        patch = read("patches", "set_cortex_help_menu.py")
        self.assertIn("cortex.openAssistant()", patch)
        self.assertIn("/app/cortex-support-request/new", patch)
        for forbidden in ("frappe.io", "github.com", "discuss.frappe"):
            self.assertNotIn(forbidden, patch)

    def test_support_requests_are_company_scoped_and_not_deletable(self):
        doc = json.loads(read("cortex_rental", "doctype", "cortex_support_request", "cortex_support_request.json"))
        self.assertTrue(all(not p.get("delete") for p in doc["permissions"]))
        self.assertIn("Cortex Support Request", hooks.permission_query_conditions)


class TestTeamActivity(unittest.TestCase):
    def test_every_billing_and_rental_action_has_a_french_sentence(self):
        for action in (
            "cortex.invoice.issued",
            "cortex.payment.recorded",
            "rental.approval.approved",
            "cortex.rental_transaction.transition_to_closed",
            "cortex.check_in.completed",
        ):
            self.assertTrue(team_activity.action_text(action).startswith("a "), action)

    def test_read_only_actions_are_never_shown_as_work(self):
        for action in (
            "cortex.availability.checked",
            "cortex.items.searched",
            "cortex.accounting.profit_and_loss_viewed",
        ):
            self.assertEqual(team_activity.action_text(action), "")

    def test_online_window_is_short(self):
        self.assertLessEqual(team_activity.ONLINE_WINDOW_MINUTES, 5)

    def test_presence_api_is_scoped_to_the_callers_company(self):
        source = read("api", "v1", "presence.py")
        self.assertIn("get_company_context()", source)
        self.assertIn("require_human_staff_role()", source)


class TestEnglishLeftoversInNav(unittest.TestCase):
    def test_nav_labels_are_french(self):
        js = read("public", "js", "cortex_nav.js")
        labels = re.findall(r'label: "([^"]+)"', js)
        self.assertGreater(len(labels), 10)
        for label in labels:
            self.assertFalse(re.search(r"\b(Dashboard|Customers|Settings|Payments|Invoices)\b", label), label)


if __name__ == "__main__":
    unittest.main()
