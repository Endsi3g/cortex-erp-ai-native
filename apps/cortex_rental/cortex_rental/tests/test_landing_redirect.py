"""Tests de la redirection par défaut de l'application vers /app (sans banc Frappe)."""

import os
import re
import unittest

from cortex_rental import hooks

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestLandingRedirectHooks(unittest.TestCase):
    def test_default_home_page_hooks_are_configured_to_app(self):
        self.assertEqual(hooks.home_page, "app")
        self.assertEqual(hooks.website_user_home_page, "app")

    def test_root_website_redirect_is_configured_with_status_302(self):
        rules = [
            r
            for r in getattr(hooks, "website_redirects", [])
            if r.get("source") == "/" and r.get("target") == "/app"
        ]
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.get("redirect_http_status"), 302)

    def test_root_redirect_pattern_matches_only_root_path(self):
        # Reproduction exacte de l'algorithme Frappe de resolve_redirect
        rule = next(
            r
            for r in hooks.website_redirects
            if r.get("source") == "/" and r.get("target") == "/app"
        )
        pattern = rule["source"].strip("/ ") + "$"

        # La racine (chemin vide après découpage dans Frappe) doit matcher
        self.assertTrue(bool(re.match(pattern, "")))
        self.assertEqual(re.sub(pattern, rule["target"], ""), "/app")

        # Les autres chemins ne doivent pas être interceptés
        for path in ("app", "devis/token-123", "demande/tournage", "suivi/contrat-456", "api/method/test"):
            self.assertFalse(bool(re.match(pattern, path)), f"Le chemin {path} ne doit pas être redirigé")


class TestBrandNavigationLink(unittest.TestCase):
    def test_brand_logo_links_to_app(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertIn('class: "cx-brand", href: "/app"', js)
        self.assertNotIn('class: "cx-brand", href: "/app/cortex-rental"', js)

    def test_brand_logo_intercepts_click_for_desk_smooth_navigation(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertIn("frappe.set_route(homeRoute)", js)
