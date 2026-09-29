"""The standalone Cortex app (Vue 3 + frappe-ui served at /cortex): wiring and honesty checks that need no bench."""

import ast
import os
import re
import unittest

from cortex_rental.services.login_options import DEFAULT_LANDING, safe_redirect

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(APP_DIR, "..", "..", ".."))
FRONTEND = os.path.join(APP_DIR, "public", "frontend")


def _read(*parts: str) -> str:
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return handle.read()


def _hook(name: str):
    tree = ast.parse(_read(APP_DIR, "hooks.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"hooks.py defines no {name}")


class TestServing(unittest.TestCase):
    def test_every_path_under_cortex_loads_the_same_page(self):
        self.assertIn({"from_route": "/cortex/<path:app_path>", "to_route": "cortex"}, _hook("website_route_rules"))

    def test_apps_screen_points_at_the_standalone_app(self):
        entry = _hook("add_to_apps_screen")[0]
        self.assertEqual((entry["name"], entry["route"]), ("cortex_rental", "/cortex"))

    def test_page_controller_only_boots_csrf_and_user(self):
        source = _read(APP_DIR, "www", "cortex.py")
        self.assertIn("get_csrf_token", source)
        self.assertEqual(sorted(re.findall(r'"(\w+)":', source)), ["csrf_token", "user"])

    def test_vite_and_router_agree_on_the_route(self):
        self.assertIn("frontendRoute: '/cortex'", _read(FRONTEND, "vite.config.ts"))
        self.assertIn("STANDALONE_BASE = '/cortex'", _read(FRONTEND, "src", "app", "router", "standalone.ts"))

    def test_build_output_is_not_versioned_and_is_built_at_deploy(self):
        ignore = _read(REPO, ".gitignore")
        self.assertIn("public/frontend/dist-spa/", ignore)
        self.assertIn("cortex_rental/www/cortex.html", ignore)
        self.assertIn("npm run build:spa", _read(REPO, "infra", "docker", "entrypoint-bench.sh"))

    def test_the_font_is_the_apps_own(self):
        css = _read(FRONTEND, "src", "app", "standalone.css")
        self.assertIn("InterVar", css)
        self.assertNotIn("googleapis", _read(FRONTEND, "index.html"))


class TestEveryScreenHasADeskPage(unittest.TestCase):
    """Each routed screen is reachable both at /cortex and as a Desk Page (same Vue screen, mounted by the host)."""

    # Screens reached only through a parent screen, or sharing another page's Desk route.
    NO_OWN_PAGE = {"cortex-rental", "cortex-owner-statement", "cortex-copilot", "cortex-serial", "cortex-ai-workspace"}
    ALIASES = {"cortex-operations": "cortex-ops-overview"}

    def _routes(self):
        source = _read(FRONTEND, "src", "app", "router", "routes.ts")
        blocks = re.split(r"\n  \{\n", source)
        found = []
        for block in blocks:
            match = re.search(r"path: '/app/(cortex-[a-z-]+)", block)
            if match and "component:" in block:
                found.append(match.group(1))
        return sorted(set(found))

    def test_routes_are_found(self):
        self.assertGreater(len(self._routes()), 15)

    def test_each_routed_screen_has_a_page(self):
        pages = os.path.join(APP_DIR, "cortex_rental", "page")
        missing = []
        for slug in self._routes():
            slug = self.ALIASES.get(slug, slug)
            if slug in self.NO_OWN_PAGE:
                continue
            if not os.path.isdir(os.path.join(pages, slug.replace("-", "_"))):
                missing.append(slug)
        self.assertEqual(missing, [], f"routed screens without a Desk Page: {missing}")

    def test_admin_pages_are_shortcuts_of_the_administration_workspace(self):
        workspace = _read(APP_DIR, "cortex_rental", "workspace", "cortex_admin", "cortex_admin.json")
        for slug in ("cortex-rental-policy", "cortex-team", "cortex-import", "cortex-audit-event"):
            self.assertIn(slug, workspace)


class TestSafeRedirect(unittest.TestCase):
    def test_same_site_paths_are_kept(self):
        self.assertEqual(safe_redirect("/cortex/rentals"), "/cortex/rentals")

    def test_everything_else_falls_back_to_the_app(self):
        for bad in ("", None, "rentals", "//evil.test", "https://evil.test/x", "/\\evil", "javascript:alert(1)"):
            self.assertEqual(safe_redirect(bad), DEFAULT_LANDING)


class TestShellShowsNoInventedData(unittest.TestCase):
    """The standalone shell used to ship demo search results, a fake approval count and a scripted Copilot."""

    FILES = (
        ("src", "app", "layouts", "components", "UniversalSearch.vue"),
        ("src", "app", "layouts", "components", "AppBottomNav.vue"),
        ("src", "stores", "approvals.ts"),
        ("src", "stores", "copilot.ts"),
    )

    def test_no_demo_identifiers(self):
        for parts in self.FILES:
            self.assertNotIn("DEMO-", _read(FRONTEND, *parts), "/".join(parts))

    def test_copilot_calls_the_gateway_instead_of_simulating_a_reply(self):
        source = _read(FRONTEND, "src", "stores", "copilot.ts")
        self.assertIn("sendChatTurn", source)
        self.assertNotIn("Simulate", source)
        self.assertNotIn("confidenceScore: 0.96", source)

    def test_pending_approvals_are_unknown_until_the_server_answers(self):
        self.assertIn("ref<number | null>(null)", _read(FRONTEND, "src", "stores", "approvals.ts"))


if __name__ == "__main__":
    unittest.main()
