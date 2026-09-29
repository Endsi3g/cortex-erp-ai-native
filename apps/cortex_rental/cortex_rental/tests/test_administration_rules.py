"""Administration rules that need no bench: pricing-rule validation and role-preset arithmetic."""

import json
import os
import unittest

from cortex_rental.api.v1.administration import guarded
from cortex_rental.services import administration
from cortex_rental.services.signup_rules import SignupError
from cortex_rental.services.tenant_provisioning import ROLE_PRESETS

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def rule(**over):
    base = {"rule_name": "7 jours = 3 jours facturés", "calendar_days": 7, "billable_days": 3, "description": ""}
    base.update(over)
    return base


class TestPricingRuleValidation(unittest.TestCase):
    def test_accepts_the_house_rule(self):
        clean = administration.validate_pricing_rule(rule())
        self.assertEqual((clean["calendar_days"], clean["billable_days"]), (7, 3.0))

    def test_accepts_half_days(self):
        self.assertEqual(
            administration.validate_pricing_rule(rule(calendar_days="2", billable_days="1.5"))["billable_days"], 1.5
        )

    def test_rejects_each_invalid_field_with_a_stable_code(self):
        cases = (
            (rule(calendar_days=0), "invalid_days"),
            (rule(calendar_days=366), "invalid_days"),
            (rule(calendar_days="abc"), "invalid_days"),
            (rule(billable_days=0), "invalid_billable"),
            (rule(billable_days="x"), "invalid_billable"),
            (rule(billable_days=8), "billable_exceeds_calendar"),
            (rule(rule_name="  "), "required"),
            (rule(rule_name="<script>"), "invalid_characters"),
        )
        for payload, code in cases:
            with self.assertRaises(SignupError, msg=str(payload)) as ctx:
                administration.validate_pricing_rule(payload)
            self.assertEqual(ctx.exception.code, code)

    def test_description_is_trimmed_and_capped(self):
        self.assertEqual(len(administration.validate_pricing_rule(rule(description="a " * 600))["description"]), 500)


class TestRolePresets(unittest.TestCase):
    def test_detects_the_largest_matching_preset(self):
        self.assertEqual(
            administration.detect_preset(ROLE_PRESETS["manager"]["roles"] + ["Desk User"], ROLE_PRESETS), "manager"
        )
        self.assertEqual(
            administration.detect_preset(["Rental Operator", "Cortex Counter Staff"], ROLE_PRESETS), "counter"
        )

    def test_a_custom_mix_matches_nothing(self):
        self.assertIsNone(administration.detect_preset(["Rental Operator"], ROLE_PRESETS))
        self.assertIsNone(administration.detect_preset([], ROLE_PRESETS))

    def test_role_changes_swap_preset_roles_and_keep_the_rest(self):
        current = ["Desk User", "Rental Operator", "Cortex Counter Staff", "My Custom Role"]
        add, remove = administration.role_changes(current, ROLE_PRESETS["finance"]["roles"], ROLE_PRESETS)
        self.assertEqual(sorted(add), sorted(ROLE_PRESETS["finance"]["roles"]))
        self.assertEqual(remove, ["Cortex Counter Staff", "Rental Operator"])
        self.assertNotIn("My Custom Role", remove)
        self.assertNotIn("Desk User", remove)

    def test_no_preset_grants_global_admin_roles(self):
        for preset in ROLE_PRESETS.values():
            self.assertFalse({"System Manager", "Administrator", "Cortex System Manager"} & set(preset["roles"]))


class TestContract(unittest.TestCase):
    def test_guard_turns_a_rule_failure_into_an_inline_answer(self):
        def fail():
            raise SignupError("duplicate_rule", "Déjà une règle.")

        result = guarded(fail)["data"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "duplicate_rule")

    def test_fields_the_service_reads_exist_on_the_doctype(self):
        path = os.path.join(APP_DIR, "cortex_rental", "doctype", "rental_pricing_rule", "rental_pricing_rule.json")
        with open(path, encoding="utf-8") as handle:
            fields = {f["fieldname"] for f in json.load(handle)["fields"]}
        self.assertTrue(
            {"company", "rule_name", "calendar_days", "billable_days", "is_active", "description"} <= fields
        )


if __name__ == "__main__":
    unittest.main()
