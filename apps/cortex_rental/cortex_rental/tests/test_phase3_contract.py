"""Phase 3 : consultation des profils ouverte à la société, gestion des comptes réservée au propriétaire."""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def function_body(source, name):
    return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


class TestPhase3Contract(unittest.TestCase):
    def test_account_management_functions_require_the_owner(self):
        source = read("services", "administration.py")
        for name in ("set_member_preset", "set_member_enabled", "set_company_logo", "team_devices", "sign_out_member"):
            self.assertIn("_require_team_admin", function_body(source, name), name)
        self.assertIn("can_manage_team", function_body(source, "get_team"))

    def test_profile_reading_is_a_get_limited_to_the_company(self):
        api = read("api", "v1", "account.py")
        head = api.split("def colleague_profile", 1)[0].rsplit("@frappe.whitelist", 1)[1]
        self.assertTrue(head.startswith('(methods=["GET"])'))
        service = function_body(read("services", "account_insights.py"), "colleague_profile")
        self.assertIn("company_members", service)
        self.assertIn("PermissionError", service)
        self.assertIn('"usage_time": None', service)  # jamais estimé

    def test_configuration_entry_only_shows_while_setup_is_pending(self):
        nav = read("public", "js", "cortex_nav.js")
        entry = nav.split('id: "setup"', 1)[1].split("},", 1)[0]
        self.assertIn("setup_pending", entry)

    def test_company_page_links_to_setup_and_profiles(self):
        page = read("cortex_rental", "page", "cortex_account", "cortex_account.js")
        self.assertIn("/app/cortex-setup", page)
        self.assertIn("showColleague", page)


if __name__ == "__main__":
    unittest.main()
