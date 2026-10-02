"""Onboarding contract that does not need a bench: steps, error envelope and DocType flags."""

import json
import os
import unittest

from cortex_rental.api.v1.onboarding import guarded
from cortex_rental.services import onboarding
from cortex_rental.services.signup_rules import SignupError

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestSteps(unittest.TestCase):
    def test_profile_is_required_and_others_optional(self):
        optional = {key: is_optional for key, _title, _flag, is_optional in onboarding.STEPS}
        self.assertFalse(optional["profile"])
        self.assertTrue(all(optional[k] for k in ("team", "catalog", "policies")))

    def test_every_step_flag_is_a_field_of_the_doctype(self):
        path = os.path.join(APP_DIR, "cortex_rental", "doctype", "cortex_onboarding", "cortex_onboarding.json")
        with open(path, encoding="utf-8") as handle:
            fields = {f["fieldname"] for f in json.load(handle)["fields"]}
        for _key, _title, flag, _optional in onboarding.STEPS:
            self.assertIn(flag, fields)

    def test_step_titles_are_french(self):
        self.assertEqual(onboarding.STEPS[0][1], "Profil de l'entreprise")


class TestGuard(unittest.TestCase):
    def test_success_is_wrapped_with_ok(self):
        result = guarded(lambda: {"value": 1})
        self.assertTrue(result["data"]["ok"])
        self.assertEqual(result["data"]["value"], 1)

    def test_rule_failure_becomes_a_stable_code_not_an_exception(self):
        def fail():
            raise SignupError("invalid_email", "Adresse invalide.")

        result = guarded(fail)
        self.assertFalse(result["data"]["ok"])
        self.assertEqual(result["data"]["code"], "invalid_email")

    def test_unexpected_errors_are_not_swallowed(self):
        def boom():
            raise RuntimeError("db down")

        with self.assertRaises(RuntimeError):
            guarded(boom)


if __name__ == "__main__":
    unittest.main()
