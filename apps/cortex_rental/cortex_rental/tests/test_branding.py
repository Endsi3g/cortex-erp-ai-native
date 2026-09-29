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

    def test_spa_favicon_points_to_a_shipped_file(self):
        index = _read("public", "frontend", "index.html")
        href = re.search(r'rel="icon"[^>]*href="/([^"]+)"', index).group(1)
        self.assertTrue(os.path.exists(os.path.join(APP_DIR, "public", "frontend", "public", href)))


if __name__ == "__main__":
    unittest.main()
