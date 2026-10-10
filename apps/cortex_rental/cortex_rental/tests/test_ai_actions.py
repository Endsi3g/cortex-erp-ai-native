"""Actions de l'assistant : proposer → aperçu → décision humaine → exécution (sans banc Frappe, faux `frappe`)."""

import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock

from cortex_rental.services.ai import actions, gateway, tools
from cortex_rental.services.tool_policy import AGENT_TOOL_MAP

NOW = datetime(2026, 10, 10, 12, 0, 0)


class FakeDoc(SimpleNamespace):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.flags = SimpleNamespace()
        self.name = kw.get("name", "ACT-1")

    def insert(self, **kw):
        FakeFrappe.store[self.name] = self

    def save(self, **kw):
        FakeFrappe.saved.append((self.name, self.status))


class FakeFrappe:
    store = {}
    saved = []
    perms = True
    open_count = 0
    savepoints = []
    rollbacks = []
    errors = []

    def __init__(self):
        self.utils = SimpleNamespace(now_datetime=lambda: NOW)
        self.db = SimpleNamespace(
            count=lambda *a, **k: FakeFrappe.open_count,
            get_value=self._get_value,
            exists=lambda *a, **k: False,
            savepoint=lambda sp: FakeFrappe.savepoints.append(sp),
            rollback=lambda save_point=None: FakeFrappe.rollbacks.append(save_point),
        )
        self.row = None

    def _get_value(self, doctype, name, fields, as_dict=False, for_update=False):
        return self.row

    def has_permission(self, doctype, ptype):
        return FakeFrappe.perms

    def get_doc(self, spec, name=None):
        if isinstance(spec, dict):
            return FakeDoc(**spec)
        return FakeFrappe.store[name]

    def log_error(self, title=""):
        FakeFrappe.errors.append(title)


def stored(status="Proposed", action_type="create_customer", payload=None, lines=None, expires=None):
    lines = lines or ["Client à créer : Acme"]
    return FakeDoc(
        name="ACT-1",
        status=status,
        action_type=action_type,
        payload_json=json.dumps(payload or {"customer_name": "Acme"}),
        preview_json=json.dumps({"lines": lines, "signature": actions.preview_signature(lines)}),
        expires_at=expires or NOW + timedelta(hours=1),
    )


class ActionsCase(unittest.TestCase):
    def setUp(self):
        FakeFrappe.store, FakeFrappe.saved, FakeFrappe.savepoints, FakeFrappe.rollbacks = {}, [], [], []
        FakeFrappe.errors = []
        FakeFrappe.perms, FakeFrappe.open_count = True, 0
        self.fake = FakeFrappe()
        patcher = mock.patch.object(actions, "frappe", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        audit = mock.patch.object(actions, "_audit", side_effect=lambda *a, **k: self.audits.append(a[1]))
        self.audits = []
        audit.start()
        self.addCleanup(audit.stop)

    def row_for(self, doc, user="a@test.com", company="Société A"):
        FakeFrappe.store[doc.name] = doc
        self.fake.row = SimpleNamespace(
            company=company,
            requested_by=user,
            status=doc.status,
            action_type=doc.action_type,
            expires_at=doc.expires_at,
        )

    def register_fake(self, run, lines=("Ligne",)):
        spec = actions.ActionSpec(
            "create_customer",
            "Créer un client",
            "Customer",
            "create",
            lambda args, company: actions.Prepared({"customer_name": "Acme"}, "Nouveau client : Acme", list(lines)),
            run,
        )
        return mock.patch.dict(actions.ACTIONS, {"create_customer": spec})


class TestPure(unittest.TestCase):
    def test_signature_changes_when_the_preview_changes(self):
        a = actions.preview_signature(["x — 10 $"])
        self.assertEqual(a, actions.preview_signature(["x — 10 $"]))
        self.assertNotEqual(a, actions.preview_signature(["x — 11 $"]))

    def test_missing_expiry_counts_as_expired(self):
        self.assertTrue(actions.is_expired(None, NOW))
        self.assertTrue(actions.is_expired(NOW - timedelta(seconds=1), NOW))
        self.assertFalse(actions.is_expired(NOW + timedelta(seconds=1), NOW))

    def test_block_says_nothing_is_done_until_approval(self):
        block = actions.block_for({"name": "ACT-1", "label": "Créer un client", "summary": "S", "lines": ["L"]})
        self.assertEqual(block["type"], "proposal")
        self.assertEqual(
            (block["action"], block["draft_id"], block["requires_approval"]), ("decide_ai_action", "ACT-1", True)
        )
        self.assertIn("Rien n'est fait tant que vous n'approuvez pas.", block["impact"])

    def test_block_validates_against_the_chat_schema(self):
        from pydantic import TypeAdapter

        from cortex_rental.schemas.chat_schemas import ChatBlock

        block = actions.block_for({"name": "ACT-1", "label": "Créer un client", "summary": "S", "lines": ["L"]})
        TypeAdapter(ChatBlock).validate_python(block)

    def test_registry_only_holds_known_actions(self):
        self.assertEqual(set(actions.ACTIONS), {"create_customer", "create_quote"})


class TestPropose(ActionsCase):
    def test_proposing_stores_a_proposal_and_writes_nothing_else(self):
        ran = []
        with self.register_fake(lambda p, c: ran.append(p)):
            block = actions.propose("create_customer", {"customer_name": "Acme"}, "Société A", "a@test.com")
        self.assertEqual(ran, [])  # proposer n'exécute jamais
        doc = FakeFrappe.store[block["draft_id"]]
        self.assertEqual((doc.status, doc.requested_by, doc.company), ("Proposed", "a@test.com", "Société A"))
        self.assertTrue(doc.flags.from_ai_actions)
        self.assertEqual(self.audits, ["cortex.ai_action.proposed"])

    def test_unknown_action_and_missing_permission_are_refused(self):
        with self.assertRaises(actions.ActionError):
            actions.propose("drop_database", {}, "Société A", "a@test.com")
        FakeFrappe.perms = False
        with self.assertRaises(actions.ActionError):
            actions.propose("create_customer", {"customer_name": "Acme"}, "Société A", "a@test.com")

    def test_too_many_open_proposals_are_refused(self):
        FakeFrappe.open_count = actions.MAX_OPEN_PER_USER
        with self.assertRaises(actions.ActionError):
            actions.propose("create_customer", {"customer_name": "Acme"}, "Société A", "a@test.com")


class TestDecide(ActionsCase):
    def test_other_person_or_other_company_cannot_decide(self):
        doc = stored()
        self.row_for(doc, user="a@test.com")
        with self.assertRaises(actions.ActionError):
            actions.decide("ACT-1", True, "Société A", "b@test.com")
        with self.assertRaises(actions.ActionError):
            actions.decide("ACT-1", True, "Société B", "a@test.com")
        self.fake.row = None
        with self.assertRaises(actions.ActionError):
            actions.decide("ACT-404", True, "Société A", "a@test.com")

    def test_already_decided_cannot_run_twice(self):
        self.row_for(stored(status="Executed"))
        with self.assertRaises(actions.ActionError):
            actions.decide("ACT-1", True, "Société A", "a@test.com")

    def test_reject_runs_nothing(self):
        ran = []
        self.row_for(stored())
        with self.register_fake(lambda p, c: ran.append(p)):
            out = actions.decide("ACT-1", False, "Société A", "a@test.com")
        self.assertEqual((out["status"], ran), ("Rejected", []))
        self.assertEqual(self.audits, ["cortex.ai_action.rejected"])

    def test_approve_runs_once_with_the_validated_payload_and_records_the_result(self):
        ran = []
        doc = stored(lines=["Ligne"])
        self.row_for(doc)

        def run(payload, company):
            ran.append((payload, company))
            return {"id": "CUST-1", "label": "Ouvrir", "route": ["Form", "Customer", "CUST-1"]}

        with self.register_fake(run):
            out = actions.decide("ACT-1", True, "Société A", "a@test.com")
        self.assertEqual(ran, [({"customer_name": "Acme"}, "Société A")])
        self.assertTrue(out["ok"])
        self.assertEqual(doc.status, "Executed")
        self.assertEqual(json.loads(doc.result_json)["id"], "CUST-1")
        self.assertEqual(doc.decided_by, "a@test.com")
        self.assertEqual(self.audits, ["cortex.ai_action.executed"])
        self.assertEqual(FakeFrappe.savepoints, [actions.SAVEPOINT])

    def test_expired_proposal_is_closed_and_not_run(self):
        ran = []
        doc = stored(expires=NOW - timedelta(minutes=1))
        self.row_for(doc)
        with self.register_fake(lambda p, c: ran.append(p)):
            out = actions.decide("ACT-1", True, "Société A", "a@test.com")
        self.assertEqual((out["ok"], out["status"], ran), (False, "Expired", []))
        self.assertEqual(
            doc.status, "Expired"
        )  # l'issue est notée (résultat, pas exception : l'exception annulerait la note)

    def test_changed_preview_makes_the_proposal_stale(self):
        ran = []
        doc = stored(lines=["Ancien prix 100 $"])
        self.row_for(doc)
        with self.register_fake(lambda p, c: ran.append(p), lines=("Nouveau prix 120 $",)):
            out = actions.decide("ACT-1", True, "Société A", "a@test.com")
        self.assertEqual((out["status"], ran), ("Expired", []))
        self.assertIn("changé", out["message"])

    def test_failing_run_rolls_back_and_is_reported_as_failure_never_success(self):
        doc = stored(lines=["Ligne"])
        self.row_for(doc)

        def boom(payload, company):
            raise ValueError("Un client portant ce nom existe déjà.")

        with self.register_fake(boom):
            out = actions.decide("ACT-1", True, "Société A", "a@test.com")
        self.assertEqual((out["ok"], out["status"]), (False, "Failed"))
        self.assertEqual(doc.status, "Failed")
        self.assertEqual(FakeFrappe.rollbacks, [actions.SAVEPOINT])
        self.assertIn("existe déjà", doc.error)
        self.assertIn("cortex.ai_action.failed", self.audits)


class TestToolsAndGateway(unittest.TestCase):
    def test_proposing_tools_are_hidden_unless_the_site_enables_them(self):
        names = list(tools.PROPOSING_TOOLS) + ["list_rentals"]
        with mock.patch.object(tools, "frappe", SimpleNamespace(conf={})):
            self.assertEqual([t.name for t in tools.exposed(names)], ["list_rentals"])
        with mock.patch.object(tools, "frappe", SimpleNamespace(conf={"cortex_ai_actions": 1})):
            self.assertEqual({t.name for t in tools.exposed(names)}, set(names))

    def test_proposing_tool_refuses_when_disabled(self):
        with mock.patch.object(tools, "frappe", SimpleNamespace(conf={})):
            out = tools.propose_create_customer("Acme")
        self.assertIn("error", out)

    def test_every_proposing_tool_is_registered_and_granted(self):
        for name in tools.PROPOSING_TOOLS:
            self.assertIn(name, tools.REGISTRY)
            self.assertIn(name, AGENT_TOOL_MAP["cortex-operations"])

    def test_no_tool_writes_directly(self):
        # Les outils « propose_* » ne passent que par actions.propose : aucun ne crée de document lui-même.
        import inspect

        for name in tools.PROPOSING_TOOLS:
            source = inspect.getsource(tools.REGISTRY[name].fn)
            self.assertNotIn("insert(", source)
            self.assertNotIn("frappe.get_doc", source)

    def test_gateway_labels_the_new_tools(self):
        for name in tools.PROPOSING_TOOLS:
            self.assertIn(name, gateway.TOOL_LABELS)


if __name__ == "__main__":
    unittest.main()
