"""Static guarantees for the login, sign-up, password and verification pages."""

import os
import re
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts: str) -> str:
    with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


def _hex(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _luminance(colour: str) -> float:
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _hex(colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestLoginTemplate(unittest.TestCase):
    html = _read("www", "login.html")

    def test_frappe_hooks_are_preserved(self):
        for token in (
            "login_email",
            "login_password",
            "for-login",
            "for-forgot",
            "for-email-login",
            "btn-login",
            "social-logins",
        ):
            self.assertIn(token, self.html)

    def test_two_panel_structure_and_single_h1(self):
        self.assertIn("cx-auth__panel", self.html)
        self.assertIn("cx-auth__aside", self.html)
        # Two <h1> exist in the source only because of a Jinja if/else; one is rendered.
        self.assertEqual(self.html.count("<h1"), self.html.count('<h1 class="cx-auth__title"'))
        self.assertLessEqual(self.html.count("<h1"), 2)

    def test_light_and_dark_logo(self):
        self.assertIn("app-logo--light", self.html)
        self.assertIn("app-logo--dark", self.html)

    def test_no_powered_by_and_no_invented_testimonial(self):
        for text in (self.html, _read("templates", "includes", "footer", "footer_powered.html")):
            self.assertNotIn("Powered by", text)
            self.assertNotIn("ERPNext", text)
        self.assertNotIn("testimonial", self.html.lower())

    def test_social_sign_in_comes_before_the_password_form(self):
        first_social = self.html.index('class="social-logins')
        first_form = self.html.index("{{ email_login_body() }}")
        self.assertLess(first_social, first_form)

    def test_inputs_have_visible_labels(self):
        for field in ("login_email", "login_password"):
            self.assertRegex(self.html, rf'<label[^>]*for="{field}"')


class TestLoginStyles(unittest.TestCase):
    css = _read("public", "css", "cortex-login.css")

    def test_uses_app_font_not_a_second_family(self):
        self.assertIn("InterVar", self.css)
        for family in ("Plus Jakarta", "Lora", "IBM Plex"):
            self.assertNotIn(family, self.css)
        self.assertTrue(os.path.exists(os.path.join(APP_DIR, "public", "fonts", "Inter.var.woff2")))

    def test_field_icons_are_pinned_against_frappe_rules(self):
        block = self.css[self.css.index(".field-icon {") :].split("}", 1)[0]
        self.assertIn("top: 14px !important", block)

    def test_dark_and_adaptive_rules_exist(self):
        self.assertIn("prefers-color-scheme: dark", self.css)
        for width in ("640px", "380px"):
            self.assertIn(f"max-width: {width}", self.css)

    def test_text_tokens_meet_aa_on_their_surfaces(self):
        # Mirrors the light-scheme constants used for small text.
        self.assertGreaterEqual(contrast("#525252", "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast("#066336", "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast("#ffffff", "#066336"), 4.5)


class TestLoginScript(unittest.TestCase):
    js = _read("public", "js", "cortex_login.js")

    def test_csrf_and_endpoints(self):
        self.assertIn("X-Frappe-CSRF-Token", self.js)
        self.assertIn("cortex_rental.api.v1.access.request_access", self.js)
        self.assertIn("reset_password", self.js)


class TestAuthPagesShipTheirControllers(unittest.TestCase):
    def test_hyphenated_pages_have_underscored_controllers(self):
        for page in ("cortex-verify", "update-password"):
            self.assertTrue(os.path.exists(os.path.join(APP_DIR, "www", page + ".html")))
            self.assertTrue(os.path.exists(os.path.join(APP_DIR, "www", page.replace("-", "_") + ".py")))

    def test_emails_are_branded_and_french(self):
        emails = os.path.join(APP_DIR, "templates", "emails")
        names = os.listdir(emails)
        self.assertTrue(names)
        for name in names:
            body = _read("templates", "emails", name)
            self.assertNotRegex(body, re.compile("erpnext", re.I), name)


if __name__ == "__main__":
    unittest.main()
