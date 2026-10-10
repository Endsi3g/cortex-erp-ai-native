"""Mesure d'usage PostHog : éteinte sans clé, anonyme, masquée par défaut, branchée au Desk."""

import pathlib
import unittest

from cortex_rental.services import analytics

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = "phc_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
SECRET = "cle-de-chiffrement-du-site"


class TestAnalyticsConfig(unittest.TestCase):
    def build(self, **kwargs):
        args = {"key": KEY, "secret": SECRET}
        args.update(kwargs)
        return analytics.build_config("marie@exemple.ca", "Studio A", ["Rental Manager", "System Manager"], **args)

    def test_off_without_a_valid_key(self):
        for key in (None, "", "abc", "phc_court", "sk_" + "x" * 30):
            self.assertIsNone(self.build(key=key))

    def test_off_when_disabled_or_for_system_accounts(self):
        self.assertIsNone(self.build(disabled=True))
        self.assertIsNone(self.build(secret=""))
        for user in ("Administrator", "Guest", ""):
            self.assertIsNone(analytics.build_config(user, "Studio A", [], key=KEY, secret=SECRET))

    def test_person_is_anonymous_and_stable(self):
        config = self.build()
        again = self.build()
        self.assertEqual(config["distinct_id"], again["distinct_id"])
        self.assertNotIn("marie", str(config).lower())
        self.assertNotIn("exemple.ca", str(config))
        other = analytics.build_config("jean@exemple.ca", "Studio A", [], key=KEY, secret=SECRET)
        self.assertNotEqual(config["distinct_id"], other["distinct_id"])
        rotated = self.build(secret="autre-cle")
        self.assertNotEqual(config["distinct_id"], rotated["distinct_id"])
        # Le compte n'est pas sensible à la casse du courriel.
        upper = analytics.build_config("MARIE@exemple.ca", "Studio A", [], key=KEY, secret=SECRET)
        self.assertEqual(config["distinct_id"], upper["distinct_id"])

    def test_masked_by_default_and_unmasked_only_by_explicit_site_choice(self):
        masked = self.build()
        self.assertFalse(masked["capture_pii"])
        self.assertIn(".form-control", masked["mask_text_selector"])
        self.assertIn(".cx-chat-message", masked["mask_text_selector"])
        open_ = self.build(capture_pii=True)
        self.assertTrue(open_["capture_pii"])
        self.assertEqual(open_["mask_text_selector"], "")

    def test_company_is_the_group_and_roles_are_sorted(self):
        config = self.build()
        self.assertEqual(config["group"], {"company": "Studio A"})
        self.assertEqual(config["person"]["roles"], ["Rental Manager", "System Manager"])

    def test_host_is_https_only_with_a_safe_default(self):
        self.assertEqual(analytics.clean_host("https://eu.i.posthog.com/"), "https://eu.i.posthog.com")
        self.assertEqual(analytics.clean_host("https://ph.exemple.ca"), "https://ph.exemple.ca")
        for bad in ("", None, "http://eu.i.posthog.com", "javascript:alert(1)", "https://x.com/path", "//evil.com"):
            self.assertEqual(analytics.clean_host(bad), analytics.DEFAULT_HOST)


class TestAnalyticsWiring(unittest.TestCase):
    def test_script_is_loaded_by_the_desk_and_boot_exposes_the_config(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn("/assets/cortex_rental/js/cortex_analytics.js", hooks)
        auth = (ROOT / "auth_hooks.py").read_text(encoding="utf-8")
        self.assertIn("bootinfo.cortex_analytics", auth)
        self.assertTrue((ROOT / "public/js/cortex_analytics.js").exists())

    def test_script_respects_privacy_choices_and_holds_no_key(self):
        script = (ROOT / "public/js/cortex_analytics.js").read_text(encoding="utf-8")
        for needle in ("doNotTrack", "globalPrivacyControl", "respect_dnt", "maskAllInputs", "capture_pageview: false"):
            self.assertIn(needle, script)
        self.assertNotIn("phc_", script)  # la clé vient du site, jamais du dépôt
        self.assertNotIn("posthog.com", script.replace('".i.posthog.com"', "").replace('"-assets.i.posthog.com"', ""))


if __name__ == "__main__":
    unittest.main()
