"""Static checks for the Desk hosting of the Vue 3 + Frappe UI screens.

Every SPA screen that lives under /app/<page> needs a Desk Page with that exact name, otherwise a
link inside the Cortex UI ends on "Page not found". These tests read routes.ts, the Page JSON/JS
files, hooks.py and the host script, so they run without a bench.
"""

import glob
import json
import os
import re
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_DIR = os.path.join(APP_DIR, "cortex_rental")
ROUTES = os.path.join(APP_DIR, "public", "frontend", "src", "app", "router", "routes.ts")

# The Copilot page keeps its own bundle: it mounts the Copilot panel, not a routed screen.
LEGACY_PAGES = {"cortex-assistant"}
# A Workspace slug wins over a Page with the same name, so these SPA paths live in Pages with
# another name; cortex_host.js maps between the two.
PAGE_ALIASES = {"cortex-operations": "cortex-ops-overview", "cortex-rental": "cortex-rental-detail"}
NOT_PAGES = {
    "cortex-approvals",
    "cortex-incoming",
    "cortex-ai-drafts",
    "cortex-agent-activity",
    "cortex-copilot",
    "cortex-rental-policy",
    "cortex-team",
    "cortex-import",
    "cortex-audit-event",
}


def _read(*parts: str) -> str:
    with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


def _spa_pages():
    """First path segment of every routed screen with a component."""
    source = _read("public", "frontend", "src", "app", "router", "routes.ts")
    pages = set()
    for block in re.split(r"\n  \{\n", source):
        path = re.search(r"path: '/app/([^/']+)", block)
        if path and "component:" in block:
            pages.add(path.group(1))
    return pages


def _desk_pages():
    pages = {}
    for path in glob.glob(os.path.join(MODULE_DIR, "page", "*", "*.json")):
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
        pages[doc["name"]] = os.path.dirname(path)
    return pages


class TestDeskHosting(unittest.TestCase):
    def test_every_spa_screen_has_a_desk_page(self):
        expected = {PAGE_ALIASES.get(name, name) for name in _spa_pages() - NOT_PAGES - LEGACY_PAGES}
        missing = expected - set(_desk_pages())
        self.assertFalse(missing, f"SPA routes without a Desk Page: {sorted(missing)}")

    def test_hosted_pages_call_the_host_with_their_own_name(self):
        hosted = [name for name in _desk_pages() if name not in LEGACY_PAGES]
        self.assertGreaterEqual(len(hosted), 13)
        for name in hosted:
            folder = _desk_pages()[name]
            self.assertEqual(os.path.basename(folder), name.replace("-", "_"))
            with open(os.path.join(folder, f"{os.path.basename(folder)}.js"), encoding="utf-8") as handle:
                script = handle.read()
            self.assertIn(f'frappe.pages["{name}"].on_page_show', script)
            self.assertIn("cortex_rental.host.mount(wrapper)", script)
            self.assertTrue(os.path.exists(os.path.join(folder, "__init__.py")), name)

    def test_hosted_pages_do_not_load_an_esbuild_bundle(self):
        for name, folder in _desk_pages().items():
            if name in LEGACY_PAGES:
                continue
            with open(os.path.join(folder, f"{os.path.basename(folder)}.js"), encoding="utf-8") as handle:
                self.assertNotIn("frappe.require", handle.read(), name)
        self.assertEqual(
            sorted(os.listdir(os.path.join(APP_DIR, "public", "js"))),
            ["cortex_assistant", "cortex_copilot", "cortex_host", "cortex_shared"],
        )

    def test_composer_page_is_reached_from_the_spa_composer_path(self):
        host = _read("public", "js", "cortex_host", "cortex_host.js")
        self.assertIn("cortex-transaction-composer", host)
        self.assertIn("/app/cortex-rental/new", host)

    def test_entrypoint_builds_frappe_bundles_when_missing(self):
        # `bench build --app cortex_rental` alone leaves /login and /me unstyled (website.bundle.css 404).
        path = os.path.join(APP_DIR, "..", "..", "..", "infra", "docker", "entrypoint-bench.sh")
        with open(path, encoding="utf-8") as handle:
            script = handle.read()
        self.assertIn("website.bundle", script)
        self.assertIn("desk.bundle", script)
        self.assertRegex(script, r"\n\s+bench build( \|\||\n)")

    def test_no_page_shares_its_name_with_a_workspace(self):
        slugs = set()
        for path in glob.glob(os.path.join(MODULE_DIR, "workspace", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                slugs.add(json.load(handle)["title"].lower().replace(" ", "-"))
        self.assertTrue(slugs)
        self.assertFalse(slugs & set(_desk_pages()), "a Workspace would hide the Page with the same slug")

    def test_host_maps_the_aliased_pages(self):
        host = _read("public", "js", "cortex_host", "cortex_host.js")
        for spa, page in PAGE_ALIASES.items():
            self.assertIn(f'"{spa}": "{page}"', host)

    def test_hosted_pages_are_role_restricted(self):
        for name, folder in _desk_pages().items():
            with open(os.path.join(folder, f"{os.path.basename(folder)}.json"), encoding="utf-8") as handle:
                doc = json.load(handle)
            self.assertTrue(doc["roles"], name)
            self.assertEqual(doc["standard"], "Yes", name)

    def test_host_script_is_loaded_before_any_page(self):
        hooks = _read("hooks.py")
        self.assertIn('"/assets/cortex_rental/js/cortex_host/cortex_host.js"', hooks)
        self.assertTrue(os.path.exists(os.path.join(APP_DIR, "public", "js", "cortex_host", "cortex_host.js")))

    def test_global_scripts_do_not_use_the_website_only_frappe_ready(self):
        for parts in (
            ("public", "js", "cortex_copilot", "cortex_copilot.bundle.js"),
            ("public", "js", "cortex_host", "cortex_host.js"),
        ):
            self.assertNotIn("frappe.ready(", _read(*parts), parts)

    def test_host_never_writes_model_output_as_html(self):
        host = _read("public", "js", "cortex_host", "cortex_host.js")
        self.assertNotIn("innerHTML", host)

    def test_workspace_targets_that_are_hosted_pages_exist(self):
        pages = set(_desk_pages())
        for path in glob.glob(os.path.join(MODULE_DIR, "workspace", "*", "*.json")):
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
            for shortcut in doc.get("shortcuts", []):
                if shortcut["type"] == "Page":
                    self.assertIn(shortcut["link_to"], pages, path)


if __name__ == "__main__":
    unittest.main()
