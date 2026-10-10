"""Catalogue d'actions (retenue, réservation, paiement, approbation) et « Pourquoi cette proposition » (sans banc Frappe)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from pydantic import TypeAdapter

from cortex_rental.schemas.chat_schemas import ChatBlock
from cortex_rental.services.ai import action_catalog as cat
from cortex_rental.services.ai import actions, tools


class Row(dict):
    __getattr__ = dict.get


def fake(**kw):
    """Un faux `frappe` minimal : db.exists/get_value et has_permission pilotés par le test."""
    state = SimpleNamespace(
        exists=kw.get("exists", True), value=kw.get("value"), perm=kw.get("perm", True), doc=kw.get("doc")
    )
    return SimpleNamespace(
        db=SimpleNamespace(exists=lambda *a, **k: state.exists, get_value=lambda *a, **k: state.value),
        has_permission=lambda *a, **k: state.perm,
        get_doc=lambda *a, **k: state.doc,
        get_roles=lambda *a, **k: ["Rental Manager"],
    )


def tx(**kw):
    base = dict(
        name="CR-1",
        customer="Acme",
        rental_state="Quote",
        hold_status="Active",
        hold_until="2026-10-12 09:00:00",
        starts_at="2026-10-14 09:00:00",
        ends_at="2026-10-16 18:00:00",
        items=[],
        grand_total=655.36,
    )
    base.update(kw)
    return Row(base)


class TestReasoning(unittest.TestCase):
    def test_reasoning_combines_stated_checks_and_effects_without_duplicates(self):
        r = actions.reasoning_for(
            ["Effet 1"],
            "  Le client  a demandé  ça. ",
            ["Recherche de clients", "Recherche de clients", "Vérification de la disponibilité"],
        )
        self.assertEqual(r["stated"], "Le client a demandé ça.")
        self.assertEqual(r["checks"], ["Recherche de clients", "Vérification de la disponibilité"])
        self.assertEqual(r["effects"], ["Effet 1"])

    def test_nothing_to_say_means_no_section(self):
        self.assertIsNone(actions.reasoning_for((), "", ()))

    def test_stated_reason_is_capped(self):
        self.assertEqual(len(actions.reasoning_for((), "x" * 5000, ())["stated"]), 600)

    def test_card_with_reasoning_validates_against_the_schema(self):
        block = actions.block_for(
            {
                "name": "A-1",
                "action_type": "record_payment",
                "label": "Enregistrer un paiement",
                "summary": "s",
                "lines": ["l"],
                "reasoning": actions.reasoning_for(["Un effet"], "Parce que.", ["Résumé financier"]),
            }
        )
        TypeAdapter(ChatBlock).validate_python(block)
        self.assertEqual(block["reasoning"]["checks"], ["Résumé financier"])


class TestHoldActions(unittest.TestCase):
    def test_release_requires_a_quote_with_an_active_hold(self):
        with mock.patch.object(cat, "frappe", fake(doc=tx(rental_state="Contract"))):
            with self.assertRaises(actions.ActionError):
                cat._prepare_release_hold({"rental": "CR-1"}, "Société A")
        with mock.patch.object(cat, "frappe", fake(doc=tx(hold_status="Released"))):
            with self.assertRaises(actions.ActionError):
                cat._prepare_release_hold({"rental": "CR-1"}, "Société A")

    def test_release_preview_names_the_rental_and_client(self):
        with mock.patch.object(cat, "frappe", fake(doc=tx())):
            prepared = cat._prepare_release_hold({"rental": "CR-1"}, "Société A")
        self.assertEqual(prepared.payload, {"rental": "CR-1"})
        self.assertIn("CR-1", [r["value"] for r in prepared.rows])
        self.assertIn("Acme", [r["value"] for r in prepared.rows])

    def test_unknown_rental_or_missing_permission_is_refused(self):
        with mock.patch.object(cat, "frappe", fake(exists=False)):
            with self.assertRaises(actions.ActionError):
                cat._prepare_renew_hold({"rental": "CR-9"}, "Société A")
        with mock.patch.object(cat, "frappe", fake(doc=tx(), perm=False)):
            with self.assertRaises(actions.ActionError):
                cat._prepare_renew_hold({"rental": "CR-1"}, "Société A")
        with self.assertRaises(actions.ActionError):
            cat._prepare_renew_hold({}, "Société A")

    def test_renewal_that_takes_no_hold_is_reported_as_a_failure(self):
        from cortex_rental.services import holds

        with (
            mock.patch.object(cat, "frappe", fake(doc=tx())),
            mock.patch.object(
                holds, "evaluate", return_value={"status": "Insufficient", "note": "Disponibilité insuffisante"}
            ),
        ):
            with self.assertRaises(ValueError) as ctx:
                cat._run_renew_hold({"rental": "CR-1"}, "Société A")
        self.assertIn("insuffisante", str(ctx.exception))


class TestPayment(unittest.TestCase):
    INV = Row(name="INV-1", customer="Acme", status="Issued", total=500, balance=300)

    def prepare(self, args, inv=None):
        with mock.patch.object(cat, "frappe", fake(value=inv or self.INV)):
            return cat._prepare_payment({"invoice": "INV-1", **args}, "Société A")

    def test_valid_payment_shows_balance_before_and_after(self):
        p = self.prepare({"amount": 100, "method": "Cheque", "reference": "  123  "})
        self.assertEqual(p.payload, {"invoice": "INV-1", "amount": 100.0, "method": "Cheque", "reference": "123"})
        self.assertEqual(p.totals[1]["value"], "200,00 $")

    def test_invalid_payments_are_refused_with_a_clear_reason(self):
        for args, word in (
            ({"amount": 0}, "supérieur"),
            ({"amount": 301}, "dépasse"),
            ({"amount": "abc"}, "obligatoire"),
            ({"amount": 10, "method": "Bitcoin"}, "Mode"),
        ):
            with self.assertRaises(actions.ActionError) as ctx:
                self.prepare(args)
            self.assertIn(word, str(ctx.exception), args)

    def test_paid_or_cancelled_invoice_refuses_a_payment(self):
        for status in ("Paid", "Cancelled"):
            with self.assertRaises(actions.ActionError):
                self.prepare({"amount": 10}, inv=Row(name="INV-1", customer="Acme", status=status, total=5, balance=0))

    def test_other_company_invoice_is_not_found(self):
        with mock.patch.object(cat, "frappe", fake(value=None)):
            with self.assertRaises(actions.ActionError):
                cat._prepare_payment({"invoice": "INV-X", "amount": 10}, "Société A")


class TestDecision(unittest.TestCase):
    APPROVAL = Row(
        name="APPR-1",
        action="rental.transaction.transition_to_contract",
        entity_type="Cortex Rental Transaction",
        entity_id="CR-1",
        requested_by_id="b@test.com",
        status="Pending",
    )

    def prepare(self, args, row=None):
        from cortex_rental.api.v1 import approval_queue

        with (
            mock.patch.object(cat, "frappe", fake(value=row or self.APPROVAL)),
            mock.patch.object(approval_queue, "_require_approver"),
        ):
            return cat._prepare_decision({"approval": "APPR-1", **args}, "Société A")

    def test_reject_needs_a_reason_but_approve_does_not(self):
        with self.assertRaises(actions.ActionError):
            self.prepare({"decision": "reject"})
        self.assertEqual(
            self.prepare({"decision": "reject", "decision_reason": "Client sans assurance"}).payload["decision"],
            "reject",
        )
        self.assertEqual(self.prepare({"decision": "approve"}).payload["decision"], "approve")

    def test_only_pending_requests_and_known_decisions(self):
        with self.assertRaises(actions.ActionError):
            self.prepare({"decision": "approve"}, row=Row(**{**self.APPROVAL, "status": "Approved"}))
        with self.assertRaises(actions.ActionError):
            self.prepare({"decision": "maybe"})

    def test_a_person_without_approver_role_is_refused(self):
        from cortex_rental.api.v1 import approval_queue

        def deny():
            raise PermissionError("Votre rôle ne permet pas de décider une approbation.")

        with (
            mock.patch.object(cat, "frappe", fake(value=self.APPROVAL)),
            mock.patch.object(approval_queue, "_require_approver", side_effect=deny),
        ):
            with self.assertRaises(actions.ActionError):
                cat._prepare_decision({"approval": "APPR-1", "decision": "approve"}, "Société A")


class TestRegistryAndTools(unittest.TestCase):
    def test_every_catalog_action_has_effects_and_a_tool(self):
        for name in ("release_hold", "renew_hold", "request_reservation", "record_payment", "decide_approval"):
            spec = actions.ACTIONS[name]
            self.assertTrue(spec.effects, name)
        self.assertEqual(len(tools.PROPOSING_TOOLS), len(set(tools.PROPOSING_TOOLS)))
        self.assertEqual(len(tools.PROPOSING_TOOLS), len(actions.ACTIONS))

    def test_proposing_tools_ask_for_a_reason_and_pass_the_consulted_checks(self):
        for name in tools.PROPOSING_TOOLS:
            self.assertIn("reason", tools.REGISTRY[name].parameters["properties"], name)
        captured = {}

        def fake_propose(action_type, args, company, user, reason="", checks=()):
            captured.update(type=action_type, args=args, reason=reason, checks=checks)
            return {"type": "action_card"}

        token = tools.CONSULTED.set(["Recherche de clients"])
        try:
            with (
                mock.patch.object(
                    tools,
                    "frappe",
                    SimpleNamespace(conf={"cortex_ai_actions": 1}, session=SimpleNamespace(user="a@test.com")),
                ),
                mock.patch.object(tools, "_company", return_value="Société A"),
                mock.patch.object(actions, "propose", side_effect=fake_propose),
            ):
                out = tools.propose_release_hold(reason="Le client a annulé.", rental="CR-1")
        finally:
            tools.CONSULTED.reset(token)
        self.assertEqual(
            (captured["type"], captured["args"], captured["reason"]),
            ("release_hold", {"rental": "CR-1"}, "Le client a annulé."),
        )
        self.assertEqual(captured["checks"], ("Recherche de clients",))
        self.assertIn("action_block", out)

    def test_approval_motif_does_not_collide_with_the_explanation(self):
        props = tools.REGISTRY["propose_decide_approval"].parameters["properties"]
        self.assertIn("decision_reason", props)
        self.assertIn("reason", props)


if __name__ == "__main__":
    unittest.main()
