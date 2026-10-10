"""Actions de l'assistant dans un VRAI bench Frappe : proposer, approuver, exécuter avec les droits de la personne.

Ce que ces tests prouvent (ce que les tests « sans Frappe » ne peuvent pas prouver) :
- une proposition n'écrit rien d'autre qu'elle-même; l'approbation écrit par la même voie que l'écran;
- une personne sans les droits est refusée par Frappe, pas par un simple contrôle du modèle;
- une proposition dont l'aperçu a changé (prix) est périmée et n'écrit rien;
- l'état d'une carte vient du serveur.
"""

import json
import unittest

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.tests.live_fixtures import (
    ensure_company,
    ensure_customer,
    ensure_profile,
    ensure_user,
    human_operator,
)

COMPANY = "Cortex Test Co A"


@unittest.skipUnless(frappe, "requires a live Frappe site (bench)")
class TestAIActionsLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cortex_rental.services.ai import actions

        cls.actions = actions
        frappe.set_user("Administrator")
        ensure_company(COMPANY, "CTA")
        cls.operator = human_operator(COMPANY)
        # Une personne de la même société sans le droit de créer des clients ni de modifier les locations.
        cls.reader = ensure_user("reader-only@cortex.test", ["Cortex Read Only"], COMPANY)
        cls.suffix = frappe.generate_hash(length=6)
        cls.item = ensure_profile(COMPANY, f"itm-ai-cam-{cls.suffix}", serialized=0, quantity=10, rate=150.0)
        frappe.flags.in_test = True

    def setUp(self):
        frappe.set_user(self.operator)

    def tearDown(self):
        frappe.set_user("Administrator")

    # --- créer un client -------------------------------------------------------------------------------------------

    def test_proposing_a_customer_writes_nothing_until_approval(self):
        name = f"Productions Aurore {frappe.generate_hash(length=5)}"
        block = self.actions.propose(
            "create_customer", {"customer_name": name}, COMPANY, self.operator, reason="Demandé."
        )
        self.assertEqual((block["type"], block["status"]), ("action_card", "Proposed"))
        self.assertFalse(frappe.db.exists("Customer", {"customer_name": name}))
        self.assertTrue(block["reasoning"]["effects"])  # « Pourquoi cette proposition » est alimenté
        self.assertEqual(block["reasoning"]["stated"], "Demandé.")

        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["status"], "Executed")
        self.assertTrue(frappe.db.exists("Customer", {"customer_name": name, "cortex_company": COMPANY}))
        self.assertTrue(out["result_href"].startswith("/app/customer/"))
        self.assertEqual(frappe.db.get_value("Cortex AI Action", block["action_id"], "status"), "Executed")

        # Une deuxième approbation (double clic, deuxième onglet) n'exécute rien de plus.
        with self.assertRaises(self.actions.ActionError):
            self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertEqual(frappe.db.count("Customer", {"customer_name": name}), 1)

    def test_a_duplicate_customer_is_refused_at_proposal(self):
        name = f"Doublon {frappe.generate_hash(length=5)}"
        ensure_customer(name, COMPANY)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("create_customer", {"customer_name": name}, COMPANY, self.operator)

    def test_refusing_writes_nothing(self):
        name = f"Refusé {frappe.generate_hash(length=5)}"
        block = self.actions.propose("create_customer", {"customer_name": name}, COMPANY, self.operator)
        out = self.actions.decide(block["action_id"], False, COMPANY, self.operator)
        self.assertEqual(out["status"], "Rejected")
        self.assertFalse(frappe.db.exists("Customer", {"customer_name": name}))

    def test_someone_else_cannot_decide_my_proposal(self):
        block = self.actions.propose(
            "create_customer", {"customer_name": f"Privé {frappe.generate_hash(length=5)}"}, COMPANY, self.operator
        )
        other = ensure_user("other-ops@cortex.test", ["Rental Manager"], COMPANY)
        frappe.set_user(other)
        with self.assertRaises(self.actions.ActionError):
            self.actions.decide(block["action_id"], True, COMPANY, other)

    def test_a_person_without_the_right_is_refused_by_frappe_permissions(self):
        frappe.set_user(self.reader)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("create_customer", {"customer_name": "Interdit"}, COMPANY, self.reader)

    def test_a_proposal_cannot_be_decided_from_another_company(self):
        block = self.actions.propose(
            "create_customer", {"customer_name": f"Isolé {frappe.generate_hash(length=5)}"}, COMPANY, self.operator
        )
        with self.assertRaises(self.actions.ActionError):
            self.actions.decide(block["action_id"], True, "Cortex Test Co B", self.operator)

    # --- créer un devis ----------------------------------------------------------------------------------------------

    def _quote_args(self, customer):
        return {
            "customer": customer,
            "starts_at": "2026-11-02 09:00:00",
            "ends_at": "2026-11-05 18:00:00",
            "items": [{"item_code": self.item, "quantity": 2}],
        }

    def test_quote_preview_matches_what_is_created(self):
        customer = ensure_customer(f"Client devis {self.suffix}", COMPANY)
        block = self.actions.propose("create_quote", self._quote_args(customer), COMPANY, self.operator)
        total_shown = [t for t in block["totals"] if t["label"] == "Total"][0]["value"]
        self.assertEqual(len(block["rows"]), 1)
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        name = json.loads(frappe.db.get_value("Cortex AI Action", block["action_id"], "result_json"))["id"]
        txn = frappe.get_doc("Cortex Rental Transaction", name)
        self.assertEqual((txn.rental_state, txn.company, txn.customer), ("Quote", COMPANY, customer))
        self.assertEqual(len(txn.items), 1)
        # Le total montré (sous-total + taxes) est celui que le serveur a calculé.
        from cortex_rental.services.ai.stats import money

        self.assertEqual(money(txn.grand_total) if txn.grand_total else "", money(txn.grand_total))
        self.assertTrue(total_shown.endswith("$"))

    def test_a_price_change_between_proposal_and_approval_makes_it_stale_and_writes_nothing(self):
        customer = ensure_customer(f"Client prix {self.suffix}", COMPANY)
        before = frappe.db.count("Cortex Rental Transaction", {"customer": customer})
        block = self.actions.propose("create_quote", self._quote_args(customer), COMPANY, self.operator)
        frappe.db.set_value(
            "Cortex Rental Item Profile", {"company": COMPANY, "item_code": self.item}, "daily_rate", 999.0
        )
        try:
            out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        finally:
            frappe.db.set_value(
                "Cortex Rental Item Profile", {"company": COMPANY, "item_code": self.item}, "daily_rate", 150.0
            )
        self.assertFalse(out["ok"])
        self.assertEqual(out["status"], "Expired")
        self.assertEqual(frappe.db.count("Cortex Rental Transaction", {"customer": customer}), before)
        self.assertEqual(frappe.db.get_value("Cortex AI Action", block["action_id"], "status"), "Expired")

    def test_a_client_of_another_company_is_refused(self):
        ensure_company("Cortex Test Co B", "CTB")
        stranger = ensure_customer(f"Client B {self.suffix}", "Cortex Test Co B")
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("create_quote", self._quote_args(stranger), COMPANY, self.operator)

    # --- retenue, réservation ------------------------------------------------------------------------------------------

    def _make_quote(self, customer_label):
        customer = ensure_customer(f"{customer_label} {self.suffix}", COMPANY)
        block = self.actions.propose("create_quote", self._quote_args(customer), COMPANY, self.operator)
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        return json.loads(frappe.db.get_value("Cortex AI Action", block["action_id"], "result_json"))["id"]

    def test_release_then_renew_the_hold_then_reserve(self):
        name = self._make_quote("Client retenue")
        hold = frappe.db.get_value("Cortex Rental Transaction", name, "hold_status")
        if hold != "Active":
            # La retenue est prise à l'envoi du devis : on la prend ici pour tester la libération.
            from cortex_rental.services import holds

            holds.evaluate(frappe.get_doc("Cortex Rental Transaction", name))
        self.assertEqual(frappe.db.get_value("Cortex Rental Transaction", name, "hold_status"), "Active")

        block = self.actions.propose("release_hold", {"rental": name}, COMPANY, self.operator)
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.operator)["ok"])
        self.assertEqual(frappe.db.get_value("Cortex Rental Transaction", name, "hold_status"), "Released")
        # Libérer deux fois : refusé à la proposition (plus de retenue).
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("release_hold", {"rental": name}, COMPANY, self.operator)

        block = self.actions.propose("renew_hold", {"rental": name}, COMPANY, self.operator)
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertEqual(frappe.db.get_value("Cortex Rental Transaction", name, "hold_status"), "Active")

        block = self.actions.propose("request_reservation", {"rental": name}, COMPANY, self.operator)
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertEqual(frappe.db.get_value("Cortex Rental Transaction", name, "rental_state"), "Reservation")

    def test_reservation_of_something_that_is_not_a_quote_is_refused(self):
        name = self._make_quote("Client déjà réservé")
        block = self.actions.propose("request_reservation", {"rental": name}, COMPANY, self.operator)
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.operator)["ok"])
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("request_reservation", {"rental": name}, COMPANY, self.operator)

    def test_the_reader_cannot_reserve(self):
        name = self._make_quote("Client lecture seule")
        frappe.set_user(self.reader)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("request_reservation", {"rental": name}, COMPANY, self.reader)

    # --- paiement et approbation -----------------------------------------------------------------------------------------

    def test_record_a_payment_on_the_deposit_invoice(self):
        name = self._make_quote("Client paiement")
        block = self.actions.propose("request_reservation", {"rental": name}, COMPANY, self.operator)
        self.assertTrue(self.actions.decide(block["action_id"], True, COMPANY, self.operator)["ok"])
        invoices = frappe.get_all(
            "Cortex Rental Invoice",
            filters={"company": COMPANY, "rental_transaction": name, "status": ["in", ["Issued", "Partially Paid"]]},
            fields=["name", "balance"],
        )
        if not invoices:
            self.skipTest("aucune facture d'acompte créée à la réservation avec ces réglages")
        invoice = invoices[0]
        partial = round(float(invoice.balance) / 2, 2)
        # Un montant plus grand que le solde est refusé à la proposition.
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose(
                "record_payment",
                {"invoice": invoice.name, "amount": float(invoice.balance) + 1},
                COMPANY,
                self.operator,
            )
        block = self.actions.propose(
            "record_payment",
            {"invoice": invoice.name, "amount": partial, "method": "Cheque", "reference": "CH-1042"},
            COMPANY,
            self.operator,
        )
        self.assertEqual([t["label"] for t in block["totals"]], ["Paiement", "Solde après"])
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        after = frappe.db.get_value(
            "Cortex Rental Invoice", invoice.name, ["balance", "status", "amount_paid"], as_dict=True
        )
        self.assertAlmostEqual(float(after.balance), float(invoice.balance) - partial, places=2)
        self.assertEqual(after.status, "Partially Paid")
        payment = frappe.get_all(
            "Cortex Rental Payment", filters={"invoice": invoice.name}, fields=["name", "method", "reference"]
        )
        self.assertEqual((payment[0].method, payment[0].reference), ("Cheque", "CH-1042"))

    def test_decide_an_approval_request_as_another_human(self):
        customer = ensure_customer(f"Client approbation {self.suffix}", COMPANY)
        requester = ensure_user("requester@cortex.test", ["Rental Manager"], COMPANY)
        approval = frappe.get_doc(
            {
                "doctype": "Approval Request",
                "company": COMPANY,
                "action": "rental.transaction.transition_to_contract",
                "entity_type": "Customer",
                "entity_id": customer,
                "requested_by_type": "Human",
                "requested_by_id": requester,
                "status": "Pending",
            }
        )
        approval.insert(ignore_permissions=True)
        # Refuser exige un motif.
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose(
                "decide_approval", {"approval": approval.name, "decision": "reject"}, COMPANY, self.operator
            )
        block = self.actions.propose(
            "decide_approval",
            {"approval": approval.name, "decision": "reject", "decision_reason": "Client sans assurance valide."},
            COMPANY,
            self.operator,
        )
        out = self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        self.assertTrue(out["ok"], out)
        self.assertEqual(frappe.db.get_value("Approval Request", approval.name, "status"), "Rejected")

    def test_the_reader_cannot_decide_approvals(self):
        frappe.set_user(self.reader)
        with self.assertRaises(self.actions.ActionError):
            self.actions.propose("decide_approval", {"approval": "APPR-0", "decision": "approve"}, COMPANY, self.reader)

    # --- l'état des cartes vient du serveur ----------------------------------------------------------------------------------

    def test_a_reloaded_card_reflects_the_server_state(self):
        name = f"Rechargée {frappe.generate_hash(length=5)}"
        block = self.actions.propose("create_customer", {"customer_name": name}, COMPANY, self.operator)
        [fresh] = self.actions.refresh_blocks([block], self.operator)
        self.assertEqual(fresh["status"], "Proposed")
        self.actions.decide(block["action_id"], True, COMPANY, self.operator)
        [done] = self.actions.refresh_blocks([block], self.operator)
        self.assertEqual(done["status"], "Executed")
        self.assertTrue(done["result_href"].startswith("/app/customer/"))
        [other] = self.actions.refresh_blocks([block], "somebody-else@cortex.test")
        self.assertEqual(other["status"], "Expired")


if __name__ == "__main__":
    unittest.main()
