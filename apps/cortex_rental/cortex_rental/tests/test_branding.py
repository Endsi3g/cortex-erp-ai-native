"""Branding assets referenced by the app must exist and follow the palette rules."""

import os
import re
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FORBIDDEN = ("#4F46E5", "#7C3AED", "#6D28D9")  # former indigo placeholder and violet family


def _read(*parts: str) -> str:
    with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestBranding(unittest.TestCase):
    def test_app_logo_file_exists_and_is_on_palette(self):
        hooks = _read("hooks.py")
        match = re.search(r'^app_logo_url = "/assets/cortex_rental/(.+)"', hooks, re.M)
        self.assertIsNotNone(match)
        logo = _read("public", *match.group(1).split("/"))
        self.assertIn("<title", logo)
        self.assertNotIn("<text", logo, "logo must use outlines, not live text")
        for colour in FORBIDDEN:
            self.assertNotIn(colour.lower(), logo.lower())


if __name__ == "__main__":
    unittest.main()


class TestNoErpnextInVisibleText(unittest.TestCase):
    """The product name is Cortex: screens, labels and messages never name the underlying ERP.

    Code, module names, field names and `required_apps` keep `erpnext` (it is the system of record).
    """

    def test_screens_locales_and_doctype_labels_do_not_name_erpnext(self):
        import glob
        import re

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        patterns = [
            "cortex_rental/page/*/*.json",
            "cortex_rental/workspace/*/*.json",
            "cortex_rental/number_card/*/*.json",
            "cortex_rental/dashboard_chart/*/*.json",
            "cortex_rental/report/*/*",
            "cortex_rental/onboarding_step/*/*.json",
            "cortex_rental/module_onboarding/*/*.json",
            "translations/*.csv",
            "fixtures/*.json",
        ]
        offenders = []
        for pattern in patterns:
            for path in glob.glob(os.path.join(root, pattern), recursive=True):
                with open(path, encoding="utf-8") as handle:
                    if re.search(r"erp\s?next", handle.read(), re.IGNORECASE):
                        offenders.append(os.path.relpath(path, root))
        for path in glob.glob(os.path.join(root, "cortex_rental", "doctype", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                labels = re.findall(r'"label":\s*"([^"]*)"', handle.read())
            if any(re.search(r"erp\s?next", label, re.IGNORECASE) for label in labels):
                offenders.append(os.path.relpath(path, root))
        self.assertEqual(offenders, [])
