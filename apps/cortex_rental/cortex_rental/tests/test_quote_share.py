"""Portail de devis : jeton, instantané, droits du client et contrat des fichiers (sans banc Frappe)."""

import json
import os
import re
import unittest

from cortex_rental.services import quote_share

MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)))


def read(*parts):
    with open(os.path.join(MODULE_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestToken(unittest.TestCase):
    def test_tokens_are_long_random_and_unique(self):
        tokens = {quote_share.new_token() for _ in range(200)}
        self.assertEqual(len(tokens), 200)
        self.assertTrue(all(len(t) >= 40 for t in tokens))

    def test_only_the_hash_is_kept_and_it_is_not_the_token(self):
        token = quote_share.new_token()
        digest = quote_share.hash_token(token)
        self.assertNotEqual(digest, token)
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, quote_share.hash_token(token))

    def test_the_share_doctype_never_stores_the_raw_token(self):
        spec = json.loads(read("cortex_rental", "doctype", "cortex_quote_share", "cortex_quote_share.json"))
        names = {f["fieldname"] for f in spec["fields"]}
        self.assertIn("token_hash", names)
        self.assertNotIn("token", names)
        fields = {f["fieldname"]: f for f in spec["fields"]}
        self.assertTrue(fields["token_hash"].get("hidden"))
        for perm in spec["permissions"]:
            self.assertFalse(perm.get("write") or perm.get("create") or perm.get("delete"), perm)


class TestClientCanOnlyAnswer(unittest.TestCase):
    def test_three_actions_only(self):
        self.assertEqual(set(quote_share.ACTIONS), {"accept", "decline", "changes"})

    def test_guest_endpoints_are_only_respond(self):
        source = read("api", "v1", "quote_share.py")
        guest = re.findall(r"allow_guest=True[^\n]*\n(?:\s*@[^\n]*\n)*\s*def (\w+)", source)
        self.assertEqual(guest, ["respond"])

    def test_guest_respond_is_rate_limited(self):
        source = read("api", "v1", "quote_share.py")
        self.assertRegex(source, r"allow_guest=True.*\n\s*@rate_limit")

    def test_staff_endpoints_require_a_human_staff_role(self):
        source = read("api", "v1", "quote_share.py")
        for name in ("create_share", "list_shares", "revoke_share"):
            body = source.split(f"def {name}")[1].split("@frappe.whitelist")[0]
            self.assertIn("require_human_staff_role()", body, name)

    def test_accepting_does_not_reserve_or_write_the_rental(self):
        source = read("services", "quote_share.py")
        self.assertNotIn("request_reservation", source)
        self.assertNotIn('"Cortex Rental Transaction", tx', source.split("def respond")[1].split("_STATE_MESSAGES")[0])

    def test_public_page_is_noindex_and_escapes_values(self):
        html = read("www", "devis.html")
        self.assertIn("noindex", html)
        self.assertNotIn("|safe", html)
        self.assertNotIn("| safe", html)

    def test_route_rule_maps_the_token(self):
        self.assertIn('"/devis/<token>"', read("hooks.py"))

    def test_email_is_french_and_has_the_link(self):
        html = read("templates", "emails", "cortex_quote_share.html")
        self.assertIn("{{ link }}", html)
        self.assertIn("Consulter le devis", html)


class TestText(unittest.TestCase):
    def test_clean_text_has_a_limit(self):
        self.assertLessEqual(len(quote_share.clean_text("a" * 5000)), quote_share.MAX_MESSAGE)


if __name__ == "__main__":
    unittest.main()
