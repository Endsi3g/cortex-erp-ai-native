"""Static integrity checks for the Desk navigation (Workspaces).

These tests read the Workspace / Page / DocType JSON files and the hooks, so they
run without a Frappe bench. They guard the regressions found in the 2026-09-28
audit: duplicated workspace folders, links to pages that do not exist, fake
``DEMO-`` targets, and a boot hook that wrote to the database and hid the
ERPNext workspaces.
"""

import glob
import json
import os
import re
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_DIR = os.path.join(APP_DIR, "cortex_rental")

# DocTypes owned by Frappe/ERPNext, not by this app.
CORE_DOCTYPES = {
    "Item",
    "Serial No",
    "Customer",
    "Sales Invoice",
    "Company",
    "User",
    "Data Import",
}
HUB = "Cortex Rental"
ERPNEXT_TARGETS = {"Accounting", "Stock", "Selling", "Buying", "Projects", "ERPNext Settings"}


def scrub(name: str) -> str:
    return name.replace(" ", "_").replace("-", "_").lower()


def _load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _workspaces():
    result = {}
    for path in sorted(glob.glob(os.path.join(MODULE_DIR, "workspace", "*", "*.json"))):
        result[path] = _load(path)
    return result


def _pages():
    return {_load(p)["name"] for p in glob.glob(os.path.join(MODULE_DIR, "page", "*", "*.json"))}


def _doctypes():
    return {
        _load(p)["name"] for p in glob.glob(os.path.join(MODULE_DIR, "doctype", "*", "*.json")) if "name" in _load(p)
    }


def _read(*parts: str) -> str:
    with open(os.path.join(APP_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestWorkspaceNavigation(unittest.TestCase):
    def test_workspace_folder_matches_scrubbed_title(self):
        workspaces = _workspaces()
        self.assertTrue(workspaces)
        for path, doc in workspaces.items():
            folder = os.path.basename(os.path.dirname(path))
            self.assertEqual(folder, scrub(doc["title"]), path)
            self.assertEqual(os.path.basename(path), f"{folder}.json", path)

    def test_workspace_titles_are_unique(self):
        titles = [doc["title"] for doc in _workspaces().values()]
        self.assertEqual(len(titles), len(set(titles)), titles)

    def test_hub_and_six_groups_exist_with_valid_parent(self):
        docs = {doc["title"]: doc for doc in _workspaces().values()}
        self.assertIn(HUB, docs)
        self.assertEqual(docs[HUB]["parent_page"], "")
        children = [d for d in docs.values() if d["title"] != HUB]
        self.assertEqual(len(children), 6)
        for child in children:
            self.assertEqual(child["parent_page"], HUB, child["title"])
            self.assertEqual(child["public"], 1)
            self.assertEqual(child["is_hidden"], 0)
        sequences = [d["sequence_id"] for d in docs.values()]
        self.assertEqual(len(sequences), len(set(sequences)), "sequence_id must be unique")

    def test_every_workspace_restricts_visibility_by_role(self):
        for path, doc in _workspaces().items():
            self.assertTrue(doc["roles"], f"{path} must declare roles")
            self.assertIn("System Manager", [r["role"] for r in doc["roles"]], path)

    def test_every_target_exists(self):
        pages, doctypes = _pages(), _doctypes() | CORE_DOCTYPES
        for path, doc in _workspaces().items():
            entries = [(s["type"], s["link_to"]) for s in doc.get("shortcuts", [])]
            entries += [(l["link_type"], l["link_to"]) for l in doc.get("links", []) if l.get("type") == "Link"]
            self.assertTrue(entries, f"{path} has no navigation target")
            for kind, target in entries:
                if kind == "Page":
                    self.assertIn(target, pages, f"{path}: unknown Page {target}")
                elif kind == "DocType":
                    self.assertIn(target, doctypes, f"{path}: unknown DocType {target}")
                else:
                    self.fail(f"{path}: unsupported target type {kind}")

    def test_no_demo_or_placeholder_targets(self):
        for path in glob.glob(os.path.join(MODULE_DIR, "workspace", "*", "*.json")):
            self.assertNotIn("DEMO-", _read(path), path)

    def test_content_blocks_reference_declared_shortcuts(self):
        for path, doc in _workspaces().items():
            labels = {s["label"] for s in doc.get("shortcuts", [])}
            cards = {l["label"] for l in doc.get("links", []) if l.get("type") == "Card Break"}
            for block in json.loads(doc["content"]):
                data = block["data"]
                if block["type"] == "shortcut":
                    self.assertIn(data["shortcut_name"], labels, path)
                elif block["type"] == "card":
                    self.assertIn(data["card_name"], cards, path)

    def test_live_count_filters_are_valid(self):
        counted = 0
        for path, doc in _workspaces().items():
            for shortcut in doc.get("shortcuts", []):
                if shortcut.get("stats_filter"):
                    counted += 1
                    parsed = json.loads(shortcut["stats_filter"])
                    self.assertEqual(shortcut["type"], "DocType", path)
                    self.assertTrue(all(row[0] == shortcut["link_to"] for row in parsed), path)
        self.assertGreaterEqual(counted, 2, "approvals and inbound requests should show live counts")

    def test_count_filters_use_declared_status_options(self):
        for doctype, folder in (
            ("Approval Request", "approval_request"),
            ("Cortex Inbound Request", "cortex_inbound_request"),
        ):
            fields = _load(os.path.join(MODULE_DIR, "doctype", folder, f"{folder}.json"))["fields"]
            options = next(f["options"].split("\n") for f in fields if f["fieldname"] == "status")
            for doc in _workspaces().values():
                for shortcut in doc.get("shortcuts", []):
                    if shortcut["link_to"] == doctype and shortcut.get("stats_filter"):
                        for _, field, _, value in json.loads(shortcut["stats_filter"]):
                            self.assertEqual(field, "status")
                            self.assertIn(value, options)


class TestNavigationHooks(unittest.TestCase):
    def test_boot_hook_does_not_write_or_hide_workspaces(self):
        hooks = _read("hooks.py")
        # A read-only boot flag is allowed (onboarding); the old hook wrote to tabWorkspace.
        self.assertNotIn("setup_cortex_sidebar", hooks)
        self.assertNotIn("get_workspace_sidebar_items", hooks)
        setup = _read("setup.py")
        self.assertNotIn("tabWorkspace", setup)
        self.assertNotIn("is_hidden", setup)

    def test_restore_patch_is_registered_and_limited_to_erpnext_areas(self):
        patches = _read("patches.txt")
        self.assertIn("cortex_rental.patches.restore_erpnext_workspaces", patches)
        source = _read("patches", "restore_erpnext_workspaces.py")
        listed = set(re.findall(r'"([A-Za-z ]+)"', source.split("ERPNEXT_WORKSPACES")[1].split(")")[0]))
        self.assertEqual(listed, ERPNEXT_TARGETS)
        self.assertNotIn("Cortex", source.split("ERPNEXT_WORKSPACES")[1].split(")")[0])


if __name__ == "__main__":
    unittest.main()
