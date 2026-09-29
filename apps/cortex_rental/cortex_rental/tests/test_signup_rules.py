"""Pure rules for access requests (no Frappe needed)."""

import unittest

from cortex_rental.services import signup_rules as rules
from cortex_rental.services.signup_rules import SignupError


class TestEmail(unittest.TestCase):
    def test_normalises_case_and_whitespace(self):
        self.assertEqual(rules.normalize_email("  Jane.Doe@Studio.CA "), "jane.doe@studio.ca")

    def test_rejects_malformed(self):
        for bad in ("", None, "jane", "jane@", "@studio.ca", "jane@studio", "a b@studio.ca", "x@" + "a" * 260 + ".ca"):
            with self.assertRaises(SignupError) as ctx:
                rules.normalize_email(bad)
            self.assertEqual(ctx.exception.code, "invalid_email")


class TestDomainPolicy(unittest.TestCase):
    def test_free_mail_blocked_by_default(self):
        with self.assertRaises(SignupError) as ctx:
            rules.check_domain_policy("jane@gmail.com")
        self.assertEqual(ctx.exception.code, "free_email")

    def test_free_mail_allowed_when_policy_off(self):
        rules.check_domain_policy("jane@gmail.com", block_free=False)

    def test_allow_list_wins_over_free_mail_rule(self):
        rules.check_domain_policy("jane@gmail.com", allowed=["gmail.com"])
        with self.assertRaises(SignupError) as ctx:
            rules.check_domain_policy("jane@studio.ca", allowed=["gmail.com"])
        self.assertEqual(ctx.exception.code, "domain_not_allowed")

    def test_split_lines_accepts_commas_lines_and_at_signs(self):
        self.assertEqual(rules.split_lines("@Studio.ca, foo.com\nBar.com"), ["studio.ca", "foo.com", "bar.com"])


class TestCleanName(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(rules.clean_name("  Jane   Doe ", "Le nom"), "Jane Doe")

    def test_required_length_and_markup(self):
        for value, code in (("  ", "required"), ("x" * 141, "too_long"), ("<b>x</b>", "invalid_characters")):
            with self.assertRaises(SignupError) as ctx:
                rules.clean_name(value, "Le nom")
            self.assertEqual(ctx.exception.code, code)


class TestTokens(unittest.TestCase):
    def test_round_trip_and_hash_only_stored(self):
        token, stored = rules.new_token("ACC-REQ-2026-00001")
        request_id, secret = rules.split_token(token)
        self.assertEqual(request_id, "ACC-REQ-2026-00001")
        self.assertNotIn(secret, stored)
        self.assertTrue(rules.token_matches(secret, stored))
        self.assertFalse(rules.token_matches(secret + "x", stored))
        self.assertFalse(rules.token_matches(secret, None))

    def test_tokens_are_unique(self):
        self.assertNotEqual(rules.new_token("A")[0], rules.new_token("A")[0])

    def test_bad_shapes_are_refused(self):
        for bad in (None, "", "nodot", ".secret", "id.", "x." + "y" * 250):
            with self.assertRaises(SignupError) as ctx:
                rules.split_token(bad)
            self.assertEqual(ctx.exception.code, "invalid_token")


class TestAbbreviation(unittest.TestCase):
    def test_initials_with_accents(self):
        self.assertEqual(rules.abbreviation("Éclairage Québec Média", []), "EQM")

    def test_unique_against_taken(self):
        self.assertEqual(rules.abbreviation("Studio Lumière", ["sl"]), "SL2")
        self.assertEqual(rules.abbreviation("Studio Lumière", ["SL", "SL2"]), "SL3")

    def test_single_word_and_empty(self):
        self.assertGreaterEqual(len(rules.abbreviation("Cortex", [])), 2)
        self.assertEqual(rules.abbreviation("###", []), "CO")


if __name__ == "__main__":
    unittest.main()
