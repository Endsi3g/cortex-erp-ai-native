"""Société d'un dossier précis : la location d'une autre société autorisée n'est plus refusée à tort."""

from types import SimpleNamespace

import pytest

from cortex_rental.permissions import agent_scopes


class _Throw(Exception):
    pass


def _fake_frappe(allowed, doc_company, header=None, form=None, is_admin=False):
    db = SimpleNamespace(
        get_value=lambda doctype, name, field: doc_company if name else None,
        table_exists=lambda _doctype: True,
    )
    request = SimpleNamespace(headers={"X-Company-ID": header} if header else {})

    def throw(message, exc=None):
        raise (exc or _Throw)(message)

    return SimpleNamespace(
        db=db,
        local=SimpleNamespace(request=request, form_dict=form or {}),
        session=SimpleNamespace(user="Administrator" if is_admin else "agent@example.com"),
        get_roles=lambda user=None: ["System Manager"] if is_admin else ["Rental Manager"],
        get_all=lambda *a, **k: list(allowed),
        throw=throw,
        PermissionError=PermissionError,
        defaults=SimpleNamespace(
            get_user_default=lambda *a, **k: sorted(allowed)[0],
            get_global_default=lambda *a, **k: sorted(allowed)[0],
        ),
    )


def test_document_company_is_used_when_the_person_is_authorised(monkeypatch):
    fake = _fake_frappe(["A", "B"], doc_company="B", is_admin=True)
    monkeypatch.setattr(agent_scopes, "frappe", fake)
    # Sans le correctif, le contexte par défaut était « A » et la location de « B » était refusée.
    assert agent_scopes.get_company_context() == "A"
    assert agent_scopes.get_company_context_for_document("Cortex Rental Transaction", "T-1") == "B"


def test_document_of_a_company_the_person_cannot_act_on_is_not_accepted(monkeypatch):
    fake = _fake_frappe(["A"], doc_company="B")
    monkeypatch.setattr(agent_scopes, "frappe", fake)
    # Retour au contexte habituel : la société « A » ; le contrôle de propriété de l'API refuse ensuite « B ».
    assert agent_scopes.get_company_context_for_document("Cortex Rental Transaction", "T-1") == "A"


def test_explicit_hint_is_still_validated(monkeypatch):
    fake = _fake_frappe(["A"], doc_company="A", header="Z")
    monkeypatch.setattr(agent_scopes, "frappe", fake)
    with pytest.raises(PermissionError):
        agent_scopes.get_company_context_for_document("Cortex Rental Transaction", "T-1")


def test_explicit_hint_inside_the_authorised_set_wins(monkeypatch):
    fake = _fake_frappe(["A", "B"], doc_company="B", header="A", is_admin=True)
    monkeypatch.setattr(agent_scopes, "frappe", fake)
    assert agent_scopes.get_company_context_for_document("Cortex Rental Transaction", "T-1") == "A"


def test_missing_name_falls_back_to_the_usual_context(monkeypatch):
    fake = _fake_frappe(["A", "B"], doc_company="B", is_admin=True)
    monkeypatch.setattr(agent_scopes, "frappe", fake)
    assert agent_scopes.get_company_context_for_document("Cortex Rental Transaction", None) == "A"


def test_document_handlers_resolve_the_company_from_the_document():
    """Contrat statique : les actions par location n'utilisent plus la société par défaut seule."""
    import pathlib

    root = pathlib.Path(agent_scopes.__file__).resolve().parents[1] / "api" / "v1"
    for filename, handlers in {
        "rentals.py": [
            "request_reservation",
            "change_state",
            "request_contract",
            "get_rental_audit",
            "update_quote_draft",
        ],
        "checkout.py": ["record_checkout_scan", "complete_checkout"],
        "quote_share.py": ["create_share", "list_shares"],
    }.items():
        source = (root / filename).read_text(encoding="utf-8")
        for handler in handlers:
            body = source.split(f"def {handler}(", 1)[1].split("@frappe.whitelist", 1)[0]
            assert "get_company_context_for_document(" in body, f"{filename}:{handler}"
