"""Onboarding contract that does not need a bench: steps, error envelope and DocType flags."""

import json
import os
import unittest

from cortex_rental.api.v1.onboarding import guarded
from cortex_rental.services import onboarding
from cortex_rental.services.signup_rules import SignupError

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestSteps(unittest.TestCase):
    def test_company_and_owner_information_are_required_and_the_rest_optional(self):
        optional = {key: is_optional for key, _title, _flag, is_optional in onboarding.STEPS}
        self.assertFalse(optional["company"])
        self.assertFalse(optional["owner"])
        self.assertTrue(all(optional[k] for k in ("team", "catalog", "pricing", "first")))
        self.assertEqual(onboarding.REQUIRED_KEYS, ["company", "owner"])

    def test_every_step_flag_is_a_field_of_the_doctype(self):
        path = os.path.join(APP_DIR, "cortex_rental", "doctype", "cortex_onboarding", "cortex_onboarding.json")
        with open(path, encoding="utf-8") as handle:
            fields = {f["fieldname"] for f in json.load(handle)["fields"]}
        for _key, _title, flag, _optional in onboarding.STEPS:
            self.assertIn(flag, fields)
        self.assertIn("skipped_steps", fields)

    def test_step_titles_are_french(self):
        self.assertEqual(onboarding.STEPS[0][1], "Votre entreprise")

    def test_the_first_unfinished_step_is_current_and_optional_steps_can_be_skipped(self):
        steps = onboarding.build_steps({"profile_done": True, "owner_done": True}, skipped=["team"])
        by_key = {s["key"]: s for s in steps}
        self.assertTrue(by_key["team"]["skipped"])
        self.assertFalse(by_key["team"]["current"])
        self.assertTrue(by_key["catalog"]["current"])

    def test_going_forward_is_locked_until_required_steps_are_done_but_back_never_is(self):
        steps = onboarding.build_steps({})
        by_key = {s["key"]: s for s in steps}
        self.assertFalse(by_key["company"]["locked"])
        self.assertTrue(by_key["owner"]["locked"])
        self.assertTrue(by_key["team"]["locked"])
        done = {s["key"]: s for s in onboarding.build_steps({"profile_done": True, "owner_done": True})}
        self.assertTrue(all(not s["locked"] for s in done.values()))

    def test_a_required_step_is_never_reported_as_skipped(self):
        steps = onboarding.build_steps({}, skipped=["company", "owner"])
        self.assertTrue(all(not s["skipped"] for s in steps if s["required"]))

    def test_required_missing_lists_only_unfinished_required_steps(self):
        self.assertEqual(onboarding.required_missing({}), ["company", "owner"])
        self.assertEqual(onboarding.required_missing({"profile_done": True}), ["owner"])
        self.assertEqual(onboarding.required_missing({"profile_done": True, "owner_done": True}), [])

    def test_the_server_refuses_to_skip_or_complete_a_required_step_and_to_finish_early(self):
        src = open(os.path.join(APP_DIR, "services", "onboarding.py"), encoding="utf-8").read()
        self.assertIn('"not_skippable"', src.split("def skip_step")[1].split("def invite_team_member")[0])
        self.assertIn('"required_step"', src.split("def complete_step")[1].split("def finish")[0])
        self.assertIn('"required_missing"', src.split("def finish")[1])

    def test_the_company_step_requires_logo_address_phone_and_email(self):
        src = open(os.path.join(APP_DIR, "services", "onboarding.py"), encoding="utf-8").read()
        body = src.split("def save_company_profile")[1].split("def save_owner_profile")[0]
        for needle in ("address_line1", "city", "pincode", "phone_no", "email", "logo_required"):
            self.assertIn(needle, body)

    def test_phone_numbers_are_validated(self):
        self.assertTrue(onboarding.PHONE_RE.match("514 555-0123"))
        self.assertTrue(onboarding.PHONE_RE.match("+1 (438) 555-0100"))
        self.assertFalse(onboarding.PHONE_RE.match("abc"))


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
