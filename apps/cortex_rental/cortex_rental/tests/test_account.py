"""Page « Mon compte » : l'API ne vise que la personne connectée (contrat statique, sans banc Frappe)."""

import inspect
import os
import re
import unittest

from cortex_rental.services import account

BASE = os.path.dirname(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestAccountContract(unittest.TestCase):
    def test_no_function_takes_a_user_or_email_parameter(self):
        for name in ("update_profile", "update_photo", "change_password", "update_notifications", "my_activity"):
            params = inspect.signature(getattr(account, name)).parameters
            self.assertFalse({"user", "email", "name", "owner"} & set(params), name)

    def test_every_public_function_starts_from_the_session_user(self):
        source = read("services", "account.py")
        for name in (
            "get_account",
            "update_profile",
            "update_photo",
            "change_password",
            "list_sessions",
            "sign_out_other_sessions",
            "update_notifications",
            "my_activity",
        ):
            body = source.split(f"def {name}(")[1].split("\ndef ")[0]
            self.assertIn("_user()", body, name)

    def test_guests_and_administrator_are_refused(self):
        body = read("services", "account.py").split("def _user")[1].split("\ndef ")[0]
        self.assertIn('("Guest", "Administrator")', body)

    def test_profile_update_writes_only_name_and_phone_fields(self):
        body = read("services", "account.py").split("def update_profile")[1].split("\ndef ")[0]
        body = body.split("frappe.db.set_value(")[1]  # seul l'appel d'écriture compte (pas la vérification d'unicité)
        written = re.findall(r'"(\w+)":', body)
        self.assertEqual(set(written), {"first_name", "last_name", "full_name", "mobile_no"})

    def test_photo_must_be_an_image_uploaded_by_the_person(self):
        body = read("services", "account.py").split("def update_photo")[1].split("\ndef ")[0]
        self.assertIn("IMAGE_EXT", body)
        self.assertIn('"owner"', body)

    def test_password_change_checks_the_old_one_enforces_strength_and_closes_other_sessions(self):
        body = read("services", "account.py").split("def change_password")[1].split("\ndef ")[0]
        for needle in ("check_password", "MIN_PASSWORD", "test_password_strength", "sign_out_other_sessions"):
            self.assertIn(needle, body)

    def test_password_endpoint_is_rate_limited(self):
        source = read("api", "v1", "account.py")
        self.assertRegex(source, r"@rate_limit\([^)]*\)\n\s*def change_password")

    def test_no_account_endpoint_is_open_to_guests(self):
        self.assertNotIn("allow_guest", read("api", "v1", "account.py"))

    def test_session_ids_are_never_returned_in_full(self):
        # Seule une empreinte tronquée (16 caractères du SHA-256) est renvoyée, jamais l'identifiant de session.
        body = read("services", "devices.py").split("def list_for")[1].split("\ndef ")[0]
        self.assertIn("key[:16]", body)
        self.assertNotIn('"sid"', body)

    def test_page_is_registered_and_reachable_from_the_profile_menu(self):
        self.assertIn(
            '"name": "cortex-account"', read("cortex_rental", "page", "cortex_account", "cortex_account.json")
        )
        self.assertIn('frappe.set_route("cortex-account", "profil")', read("public", "js", "cortex_nav.js"))

    def test_page_escapes_what_it_prints(self):
        js = read("cortex_rental", "page", "cortex_account", "cortex_account.js")
        self.assertIn("escape_html", js)
        self.assertNotIn("eval(", js)


if __name__ == "__main__":
    unittest.main()
