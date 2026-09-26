"""Lot 8: CSV import rules, rollback, role guardrails and pricing-rule bounds."""

import pytest

from cortex_rental.services import importer
from cortex_rental.tests.fake_frappe import _Dict, fake_frappe, load


def _no_site(_kind, _value):
    return False


# ---- parsing & mapping ---------------------------------------------------------


def test_parse_csv_accepts_semicolons_bom_and_pads_short_rows():
    headers, rows = importer.parse_csv("﻿Nom;Courriel;Téléphone\nAcme;a@acme.test\n".encode("utf-8"))
    assert headers == ["Nom", "Courriel", "Téléphone"]
    assert rows == [["Acme", "a@acme.test", ""]]


def test_parse_csv_rejects_empty_duplicate_headers_and_oversize():
    with pytest.raises(ValueError):
        importer.parse_csv(b"")
    with pytest.raises(ValueError):
        importer.parse_csv(b"Nom,nom\nA,B\n")
    with pytest.raises(ValueError):
        importer.parse_csv(b"Nom\n" + b"x\n" * (importer.MAX_ROWS + 1))


def test_suggest_mapping_matches_french_headers_without_reusing_a_column():
    mapping = importer.suggest_mapping("Equipment", ["Code", "Désignation", "Tarif", "Catégorie"])
    assert mapping["item_code"] == "Code"
    assert mapping["item_name"] == "Désignation"
    assert mapping["daily_rate"] == "Tarif"
    assert mapping["category"] == "Catégorie"
    assert mapping["replacement_value"] is None


def test_check_mapping_requires_required_fields_and_distinct_columns():
    headers = ["Code", "Nom"]
    errors = importer.check_mapping("Equipment", headers, {"item_code": "Code", "item_name": "Code"})
    assert any("Tarif journalier" in e for e in errors)
    assert any("deux champs" in e for e in errors)
    assert importer.check_mapping("Equipment", headers, {"item_code": "Absent"})


# ---- row validation ----------------------------------------------------------------


def test_validate_rows_types_required_and_duplicates():
    headers = ["code", "nom", "tarif", "categorie", "serie"]
    rows = [
        ["CAM-1", "Caméra", "1 250,50", "camera bodies", "oui"],
        ["CAM-2", "", "abc", "", ""],
        ["cam-1", "Doublon", "10", "", ""],
        ["LUM-1", "Projecteur", "20", "Cuisine", "peut-être"],
    ]
    mapping = importer.suggest_mapping("Equipment", headers)
    results = importer.validate_rows("Equipment", headers, rows, mapping, _no_site)
    assert results[0]["errors"] == []
    assert results[0]["values"]["daily_rate"] == 1250.5
    assert results[0]["values"]["category"] == "Camera Bodies"
    assert results[0]["values"]["is_serialized"] is True
    assert results[0]["line"] == 2
    assert any("Nom : obligatoire" in e for e in results[1]["errors"])
    assert any("Tarif journalier : valeur invalide" in e for e in results[1]["errors"])
    assert results[2]["errors"] == ["Doublon de la ligne 2"]
    assert len(results[3]["errors"]) == 2  # unknown category, unreadable boolean
    assert importer.summarize(results) == {"total_rows": 4, "valid_rows": 1, "error_rows": 3}


def test_validate_rows_checks_the_site():
    headers = ["serial", "code", "proprietaire"]
    rows = [["SN-1", "CAM-1", "LUC"], ["SN-2", "NOPE", ""], ["SN-3", "CAM-1", "GHOST"]]
    site = {("profile", "CAM-1"), ("owner", "LUC"), ("serial", "SN-9")}
    results = importer.validate_rows(
        "Serial Numbers",
        headers,
        rows,
        importer.suggest_mapping("Serial Numbers", headers),
        lambda kind, value: (kind, value) in site,
    )
    assert results[0]["errors"] == []
    assert "n’est pas dans le catalogue" in results[1]["errors"][0]
    assert "introuvable" in results[2]["errors"][0]


def test_existing_customer_name_is_an_error_not_a_silent_update():
    headers = ["nom", "type"]
    results = importer.validate_rows(
        "Customers",
        headers,
        [["Acme", "entreprise"], ["Solo", "robot"]],
        importer.suggest_mapping("Customers", headers),
        lambda kind, value: kind == "customer" and value == "Acme",
    )
    assert "existe déjà" in results[0]["errors"][0] or "porte déjà" in results[0]["errors"][0]
    assert results[1]["errors"]


# ---- import + rollback against the schema-strict fake ------------------------------


def test_import_rows_creates_item_and_profile_and_rollback_removes_them_newest_first():
    with fake_frappe(user="admin@cortex.test", roles=["System Manager"]) as fake:
        fake.singles["Stock Settings"] = {"item_group": "Caméras", "stock_uom": "Nos"}
        imports = load("cortex_rental.api.v1.imports")
        results = [
            {"line": 2, "values": {"item_code": "CAM-1", "item_name": "Caméra", "daily_rate": 100.0}, "errors": []},
            {"line": 3, "values": {}, "errors": ["Nom : obligatoire"]},
        ]
        records, errors, imported = imports.import_rows("Equipment", results, "Cortex Demo")
        assert imported == 1
        assert [r[1] for r in records] == ["Item", "Cortex Rental Item Profile"]
        assert errors == [{"line": 3, "errors": ["Nom : obligatoire"]}]
        profile = fake.tables["Cortex Rental Item Profile"][0]
        assert profile["company"] == "Cortex Demo" and profile["replacement_value"] == 0

        rows = [_Dict(record_doctype=d, record_name=n, rolled_back=0) for _line, d, n in records]
        deleted, kept = imports.rollback_records(rows)
        assert (deleted, kept) == (2, [])
        assert fake.tables["Item"] == [] and fake.tables["Cortex Rental Item Profile"] == []


def test_a_failing_row_is_rolled_back_to_its_savepoint():
    with fake_frappe(user="admin@cortex.test", roles=["System Manager"]) as fake:
        imports = load("cortex_rental.api.v1.imports")
        # No item group anywhere: the Item cannot be created, nothing of the row may remain.
        results = [{"line": 2, "values": {"item_code": "X", "item_name": "X", "daily_rate": 1.0}, "errors": []}]
        records, errors, imported = imports.import_rows("Equipment", results, "Cortex Demo")
        assert (records, imported) == ([], 0)
        assert "groupe d’articles" in errors[0]["errors"][0]
        assert not fake.tables.get("Cortex Rental Item Profile")


def test_rollback_keeps_linked_documents_and_says_why():
    with fake_frappe(user="admin@cortex.test", roles=["System Manager"]) as fake:
        imports = load("cortex_rental.api.v1.imports")
        fake.tables["Customer"] = [{"name": "CUST-1"}, {"name": "CUST-2"}]
        fake.link_guard["Customer:CUST-1"] = "Lié à Sales Invoice SINV-1"
        rows = [_Dict(record_doctype="Customer", record_name=n, rolled_back=0) for n in ("CUST-1", "CUST-2")]
        deleted, kept = imports.rollback_records(rows)
        assert deleted == 1
        assert kept == [{"doctype": "Customer", "name": "CUST-1", "reason": "Lié à Sales Invoice SINV-1"}]
        assert [r["name"] for r in fake.tables["Customer"]] == ["CUST-1"]
        assert rows[0].rolled_back == 0 and rows[1].rolled_back == 1


# ---- team guardrails and policy bounds ---------------------------------------------


def test_role_changes_only_touch_manageable_roles():
    admin = load("cortex_rental.api.v1.admin")
    current = ["Rental Operator", "Accounts User", "System Manager"]
    changes = admin.role_changes(current, ["Cortex Counter Staff"])
    assert changes == {"add": ["Cortex Counter Staff"], "remove": ["Rental Operator"]}
    with pytest.raises(ValueError):
        admin.role_changes(current, ["System Manager"])
    with pytest.raises(ValueError):
        admin.role_changes(current, ["Agent Service Account"])


def test_role_target_guardrails():
    admin = load("cortex_rental.api.v1.admin")
    with pytest.raises(PermissionError):
        admin.check_role_target("me@x.test", "me@x.test", [])
    with pytest.raises(PermissionError):
        admin.check_role_target("me@x.test", "bot@x.test", ["Agent Service Account"])
    with pytest.raises(PermissionError):
        admin.check_role_target("me@x.test", "Administrator", [])
    admin.check_role_target("me@x.test", "you@x.test", ["Rental Operator"])


def test_admin_gates_refuse_agents_and_non_admins():
    with fake_frappe(user="bot@cortex.test", roles=["System Manager", "Agent Service Account"]) as fake:
        admin = load("cortex_rental.api.v1.admin")
        with pytest.raises(fake.PermissionError):
            admin.require_admin()
    with fake_frappe(user="ops@cortex.test", roles=["Cortex System Manager"]) as fake:
        admin = load("cortex_rental.api.v1.admin")
        admin.require_admin()
        with pytest.raises(fake.PermissionError):
            admin.require_system_manager()


def test_pricing_rule_bounds():
    admin = load("cortex_rental.api.v1.admin")
    admin.validate_rule(7, 3)
    for calendar_days, billable in ((0, 1), (366, 10), (7, 0), (7, 8)):
        with pytest.raises(ValueError):
            admin.validate_rule(calendar_days, billable)
