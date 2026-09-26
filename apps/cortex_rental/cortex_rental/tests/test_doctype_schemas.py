"""Static guards on the DocType JSON shipped by this app (what `bench migrate` would reject)."""

import json
import pathlib
import unittest

DOCTYPE_DIR = pathlib.Path(__file__).resolve().parents[1] / "cortex_rental" / "doctype"
# frappe.model.default_fields + child-table fields: never usable as custom fieldnames.
RESERVED = {
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "parent",
    "parentfield",
    "parenttype",
    "doctype",
}


def _doctypes():
    for path in sorted(DOCTYPE_DIR.glob("*/*.json")):
        data = json.loads(path.read_text())
        if data.get("doctype") == "DocType":
            yield path, data


class TestDocTypeSchemas(unittest.TestCase):
    def test_no_reserved_fieldnames(self):
        offenders = [
            f"{data['name']}.{field['fieldname']}"
            for _, data in _doctypes()
            for field in data["fields"]
            if field.get("fieldname") in RESERVED
        ]
        self.assertEqual(offenders, [])

    def test_fieldnames_are_unique(self):
        for _, data in _doctypes():
            names = [f["fieldname"] for f in data["fields"]]
            self.assertEqual(len(names), len(set(names)), data["name"])

    def test_field_order_matches_fields_when_present(self):
        for _, data in _doctypes():
            if "field_order" in data:
                self.assertEqual(
                    sorted(data["field_order"]), sorted(f["fieldname"] for f in data["fields"]), data["name"]
                )

    def test_table_fields_point_to_child_doctypes_of_this_app(self):
        children = {data["name"] for _, data in _doctypes() if data.get("istable")}
        for _, data in _doctypes():
            for field in data["fields"]:
                if field["fieldtype"] == "Table":
                    self.assertIn(field["options"], children, f"{data['name']}.{field['fieldname']}")

    def test_every_doctype_has_a_controller_module(self):
        for path, data in _doctypes():
            self.assertTrue((path.parent / f"{path.parent.name}.py").exists(), data["name"])
            self.assertTrue((path.parent / "__init__.py").exists(), data["name"])


if __name__ == "__main__":
    unittest.main()
