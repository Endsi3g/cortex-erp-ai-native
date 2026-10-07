"""Phase 7 : abonnements Cortex (Stripe). Testé par signatures et événements simulés; aucun compte Stripe réel."""

import json
import pathlib
import time
import unittest
from types import SimpleNamespace

from cortex_rental.services import payments, subscriptions
from cortex_rental.services.payments import PaymentError

ROOT = pathlib.Path(__file__).resolve().parents[1]


def item(kind="Module", key="portal", price=49.0, pid="price_portal", enabled=1, confirmed=1):
    return {
        "kind": kind,
        "key": key,
        "label": key,
        "monthly_price": price,
        "stripe_price_id": pid,
        "enabled": enabled,
        "price_confirmed": confirmed,
    }


def ready(**over):
    base = {
        "enabled": 1,
        "currency": "CAD",
        "stripe_secret_key": "cle-secrete-de-test",
        "stripe_webhook_secret": "whsec_x",
        "base_monthly_price": 1000,
        "base_price_id": "price_base",
        "base_price_confirmed": 1,
        "base_includes_tiers": "rapide",
        "included_ai_budget": 0,
        "plan_items": [item(), item("AI Tier", "avance", 120.0, "price_avance")],
        "exempt_companies": "",
    }
    base.update(over)
    return base


class TestSettingsRules(unittest.TestCase):
    def test_defaults_are_valid_and_charge_nothing(self):
        self.assertEqual(
            subscriptions.settings_problems({"enabled": 0, "currency": "CAD", "base_monthly_price": 1000}), []
        )

    def test_a_complete_confirmed_setup_is_valid(self):
        self.assertEqual(subscriptions.settings_problems(ready()), [])

    def test_activation_needs_keys_confirmed_prices_and_stripe_ids(self):
        for field, text in (
            ("stripe_secret_key", "clé secrète"),
            ("stripe_webhook_secret", "webhook"),
            ("base_price_id", "plan de base"),
            ("base_price_confirmed", "Confirmez le prix de base"),
        ):
            problems = subscriptions.settings_problems(ready(**{field: ""}))
            self.assertTrue(any(text in p for p in problems), field)
        self.assertTrue(subscriptions.settings_problems(ready(base_monthly_price=0)))

    def test_no_charge_with_an_unconfirmed_option_price(self):
        problems = subscriptions.settings_problems(ready(plan_items=[item(confirmed=0)]))
        self.assertTrue(any("Confirmez le prix de l'option" in p for p in problems))
        # Une option non offerte n'a pas besoin d'être confirmée.
        self.assertEqual(subscriptions.settings_problems(ready(plan_items=[item(enabled=0, confirmed=0, pid="")])), [])

    def test_formats_and_duplicates(self):
        self.assertTrue(subscriptions.settings_problems(ready(base_price_id="prod_1")))
        self.assertTrue(subscriptions.settings_problems(ready(plan_items=[item(pid="prod_1")])))
        self.assertTrue(subscriptions.settings_problems(ready(plan_items=[item(), item()])))
        self.assertTrue(subscriptions.settings_problems(ready(plan_items=[item(key="inconnu")])))
        self.assertTrue(subscriptions.settings_problems(ready(currency="EUR")))
        self.assertTrue(subscriptions.settings_problems(ready(base_includes_tiers="rapide, gpt9")))


class TestEntitlements(unittest.TestCase):
    def test_nothing_is_restricted_while_billing_is_off_or_company_exempt(self):
        off = subscriptions.compute_entitlements({"enabled": 0}, "A", None)
        self.assertEqual((off["enforced"], off["modules"], off["ai_tiers"]), (False, None, None))
        exempt = subscriptions.compute_entitlements(ready(exempt_companies="Demo\nA"), "A", None)
        self.assertFalse(exempt["enforced"])

    def test_without_an_active_subscription_nothing_is_granted(self):
        for status in (None, "Inactive", "Canceled"):
            ent = subscriptions.compute_entitlements(ready(), "A", {"status": status} if status else None)
            self.assertEqual((ent["enforced"], ent["modules"], ent["ai_tiers"]), (True, [], []))

    def test_active_gets_base_tiers_plus_what_was_bought(self):
        sub = {"status": "Active", "modules": json.dumps(["portal"]), "ai_tiers": json.dumps(["avance"])}
        ent = subscriptions.compute_entitlements(ready(), "A", sub)
        self.assertEqual(ent["modules"], ["portal"])
        self.assertEqual(ent["ai_tiers"], ["avance", "rapide"])
        past_due = subscriptions.compute_entitlements(ready(), "A", {**sub, "status": "Past Due"})
        self.assertEqual(past_due["modules"], ["portal"])  # Stripe relance puis annule lui-même

    def test_unknown_values_in_a_stored_subscription_are_ignored(self):
        sub = {"status": "Active", "modules": json.dumps(["portal", "pirate"]), "ai_tiers": "pas du json"}
        ent = subscriptions.compute_entitlements(ready(), "A", sub)
        self.assertEqual(ent["modules"], ["portal"])
        self.assertEqual(ent["ai_tiers"], ["rapide"])

    def test_entitlements_come_only_from_known_stripe_prices(self):
        ent = subscriptions.entitlements_from_items(
            ["price_base", "price_portal", "price_avance", "price_inconnu"], ready()
        )
        self.assertEqual(ent, {"modules": ["portal"], "ai_tiers": ["avance"]})

    def test_public_catalog_has_no_secret_or_stripe_id_and_hides_unconfirmed_options(self):
        cat = subscriptions.catalog(ready(plan_items=[item(), item("AI Tier", "luna", 20, "price_luna", confirmed=0)]))
        flat = json.dumps(cat)
        for secret in ("cle-secrete-de-test", "whsec_x", "price_base", "price_portal", "price_luna"):
            self.assertNotIn(secret, flat)
        self.assertEqual([o["key"] for o in cat["options"]], ["portal"])
        self.assertEqual(cat["base"]["monthly_price"], 1000.0)


def event(kind, obj, created=1000, eid="evt_1"):
    return {"id": eid, "type": kind, "created": created, "data": {"object": obj}}


class TestEventPlanning(unittest.TestCase):
    def sub_object(self, status="active", prices=("price_base", "price_portal"), **extra):
        return {
            "id": "sub_1",
            "customer": "cus_1",
            "status": status,
            "cancel_at_period_end": False,
            "items": {"data": [{"price": {"id": p}, "current_period_end": 1900000000} for p in prices]},
            "metadata": {"company": "A"},
            **extra,
        }

    def test_subscription_updated_maps_status_period_and_entitlements(self):
        changes = subscriptions.plan_event(event("customer.subscription.updated", self.sub_object()), ready(), None)
        self.assertEqual(changes["status"], "Active")
        self.assertEqual(json.loads(changes["modules"]), ["portal"])
        self.assertEqual(changes["current_period_end"], "2030-03-17 17:46:40")
        self.assertEqual(changes["stripe_subscription_id"], "sub_1")

    def test_stripe_statuses_map_without_granting_access_by_mistake(self):
        for stripe, ours in (
            ("past_due", "Past Due"),
            ("unpaid", "Canceled"),
            ("incomplete", "Inactive"),
            ("trialing", "Trialing"),
            ("zzz", "Inactive"),
        ):
            self.assertEqual(subscriptions.map_stripe_status(stripe), ours)

    def test_out_of_order_events_are_skipped(self):
        current = {"status": "Active", "last_event_created": 2000}
        self.assertIsNone(
            subscriptions.plan_event(
                event("customer.subscription.updated", self.sub_object("canceled"), created=1500), ready(), current
            )
        )

    def test_deleted_clears_entitlements(self):
        changes = subscriptions.plan_event(
            event("customer.subscription.deleted", self.sub_object("canceled")),
            ready(),
            {"status": "Active", "last_event_created": 1},
        )
        self.assertEqual((changes["status"], changes["modules"], changes["ai_tiers"]), ("Canceled", "[]", "[]"))

    def test_rental_deposit_checkouts_are_not_ours(self):
        self.assertIsNone(
            subscriptions.plan_event(
                event("checkout.session.completed", {"mode": "payment", "metadata": {"company": "A"}}), ready(), None
            )
        )
        changes = subscriptions.plan_event(
            event("checkout.session.completed", {"mode": "subscription", "customer": "cus_1", "subscription": "sub_1"}),
            ready(),
            None,
        )
        self.assertEqual(changes["stripe_subscription_id"], "sub_1")
        self.assertNotIn("status", changes)  # l'état réel arrive avec l'événement de l'abonnement

    def test_payment_failure_and_recovery(self):
        failed = subscriptions.plan_event(event("invoice.payment_failed", {}), ready(), {"status": "Active"})
        self.assertEqual(failed["status"], "Past Due")
        self.assertIsNone(
            subscriptions.plan_event(event("invoice.payment_failed", {}), ready(), {"status": "Canceled"})
        )
        paid = subscriptions.plan_event(event("invoice.paid", {}), ready(), {"status": "Past Due"})
        self.assertEqual(paid["status"], "Active")
        self.assertIsNone(subscriptions.plan_event(event("invoice.paid", {}), ready(), {"status": "Active"}))

    def test_unknown_event_types_do_nothing(self):
        self.assertIsNone(subscriptions.plan_event(event("charge.refunded", {}), ready(), None))


class FakeFrappe:
    def __init__(self, existing_events=(), companies=("A",), sub=None):
        self.events = set(existing_events)
        self.companies = set(companies)
        self.sub = dict(sub) if sub else None
        self.inserted = []
        self.writes = []
        self.db = SimpleNamespace(exists=self.exists, get_value=self.get_value, set_value=self.set_value)

    def exists(self, doctype, name=None):
        if doctype == subscriptions.EVENT:
            return name in self.events
        if doctype == "Company":
            return name in self.companies
        if doctype == subscriptions.SUBSCRIPTION:
            return self.sub is not None
        return False

    def get_value(self, doctype, filters, fields=None, as_dict=False):
        if doctype == subscriptions.SUBSCRIPTION:
            if isinstance(filters, dict):
                return (
                    "A"
                    if self.sub and filters.get("stripe_customer_id") == self.sub.get("stripe_customer_id")
                    else None
                )
            return self.sub
        return None

    def set_value(self, doctype, name, changes):
        self.writes.append((doctype, name, dict(changes)))
        if self.sub is not None:
            self.sub.update(changes)

    def get_doc(self, payload):
        outer = self

        class Doc:
            def insert(self, ignore_permissions=False):
                outer.inserted.append(payload)
                if payload["doctype"] == subscriptions.EVENT:
                    outer.events.add(payload["event_id"])
                if payload["doctype"] == subscriptions.SUBSCRIPTION:
                    outer.sub = {"status": "Inactive", "last_event_created": 0}

        return Doc()

    def log_error(self, **kwargs):
        pass


class TestWebhook(unittest.TestCase):
    def setUp(self):
        self._frappe = subscriptions.frappe
        self._load = subscriptions.load_settings
        self._audit = subscriptions._audit
        subscriptions.load_settings = lambda with_secrets=False: ready()
        subscriptions._audit = lambda *a, **k: None

    def tearDown(self):
        subscriptions.frappe = self._frappe
        subscriptions.load_settings = self._load
        subscriptions._audit = self._audit

    def payload(self, **over):
        body = event(
            "customer.subscription.updated",
            {
                "id": "sub_1",
                "customer": "cus_1",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_portal"}}]},
                "metadata": {"company": "A"},
            },
            created=int(time.time()),
        )
        body.update(over)
        return json.dumps(body).encode()

    def test_bad_or_missing_signature_is_refused_and_writes_nothing(self):
        fake = subscriptions.frappe = FakeFrappe()
        body = self.payload()
        self.assertEqual(subscriptions.handle_event(body, "")["code"], "bad_signature")
        self.assertEqual(subscriptions.handle_event(body, payments.sign(body, "autre-secret"))["code"], "bad_signature")
        stale = payments.sign(body, "whsec_x", stamp=int(time.time()) - 3600)
        self.assertEqual(subscriptions.handle_event(body, stale)["code"], "bad_signature")
        self.assertEqual((fake.inserted, fake.writes), ([], []))

    def test_billing_off_ignores_everything(self):
        subscriptions.load_settings = lambda with_secrets=False: ready(enabled=0)
        subscriptions.frappe = FakeFrappe()
        body = self.payload()
        self.assertEqual(subscriptions.handle_event(body, payments.sign(body, "whsec_x"))["code"], "bad_signature")

    def test_a_valid_event_updates_once_and_a_replay_is_ignored(self):
        fake = subscriptions.frappe = FakeFrappe()
        body = self.payload()
        header = payments.sign(body, "whsec_x")
        first = subscriptions.handle_event(body, header)
        self.assertEqual(first, {"ok": True, "outcome": "Active"})
        writes_after_first = list(fake.writes)
        self.assertEqual(json.loads(writes_after_first[0][2]["modules"]), ["portal"])
        second = subscriptions.handle_event(body, payments.sign(body, "whsec_x"))
        self.assertEqual(second, {"ok": True, "duplicate": True})
        self.assertEqual(fake.writes, writes_after_first)  # le rejeu n'a rien écrit
        self.assertEqual(sum(1 for p in fake.inserted if p["doctype"] == subscriptions.EVENT), 1)

    def test_an_unknown_company_is_recorded_but_changes_nothing(self):
        fake = subscriptions.frappe = FakeFrappe(companies=())
        body = self.payload()
        result = subscriptions.handle_event(body, payments.sign(body, "whsec_x"))
        self.assertEqual(result["outcome"], "ignored")
        self.assertEqual(fake.writes, [])

    def test_bad_payload_is_refused(self):
        subscriptions.frappe = FakeFrappe()
        body = b"pas du json"
        self.assertEqual(subscriptions.handle_event(body, payments.sign(body, "whsec_x"))["code"], "bad_payload")


class TestCheckoutForm(unittest.TestCase):
    def test_form_uses_configured_prices_and_never_client_prices(self):
        form = subscriptions.checkout_form(
            "A", ready(), [{"kind": "Module", "key": "portal"}], "", "https://x.test/app"
        )
        self.assertEqual(form["mode"], "subscription")
        self.assertEqual(form["line_items[0][price]"], "price_base")
        self.assertEqual(form["line_items[1][price]"], "price_portal")
        self.assertEqual(form["metadata[company]"], "A")
        self.assertEqual(form["subscription_data[metadata][company]"], "A")
        self.assertNotIn("customer", form)
        self.assertNotIn("cle-secrete-de-test", json.dumps(form))
        self.assertIn("customer", subscriptions.checkout_form("A", ready(), [], "cus_9", "https://x.test"))

    def test_unoffered_or_unconfirmed_options_are_refused(self):
        with self.assertRaises(PaymentError):
            subscriptions.checkout_form("A", ready(), [{"kind": "Module", "key": "inconnu"}], "", "u")
        with self.assertRaises(PaymentError):
            subscriptions.checkout_form(
                "A", ready(plan_items=[item(confirmed=0)]), [{"kind": "Module", "key": "portal"}], "", "u"
            )

    def test_checkout_needs_billing_to_be_on_and_ready(self):
        original, load = subscriptions.frappe, subscriptions.load_settings
        try:
            subscriptions.frappe = SimpleNamespace()
            subscriptions.load_settings = lambda with_secrets=False: ready(enabled=0)
            with self.assertRaises(PaymentError):
                subscriptions.start_checkout("A", [])
            subscriptions.load_settings = lambda with_secrets=False: ready(base_price_confirmed=0)
            with self.assertRaises(PaymentError):
                subscriptions.start_checkout("A", [])
        finally:
            subscriptions.frappe, subscriptions.load_settings = original, load


class TestGatingAndContracts(unittest.TestCase):
    def test_ai_tiers_follow_the_subscription_only_when_billing_is_on(self):
        from cortex_rental.services.ai import gateway
        from cortex_rental.services.ai import settings as ai_settings

        values = dict(ai_settings.DEFAULTS)
        values.update(api_key="g", anthropic_api_key="a", openai_api_key="", company_limits={})
        original = subscriptions.allows_tier
        try:
            subscriptions.allows_tier = lambda company, key: key == "rapide"
            self.assertEqual(gateway.resolve_tier(values, "rapide", "A")["key"], "rapide")
            with self.assertRaises(gateway.TierUnavailable):
                gateway.resolve_tier(values, "avance", "A")
            # Sans société (appel interne) ou facturation off : comportement d'avant.
            self.assertEqual(gateway.resolve_tier(values, "avance")["key"], "avance")
            subscriptions.allows_tier = lambda company, key: True
            self.assertEqual(gateway.resolve_tier(values, "avance", "A")["key"], "avance")
        finally:
            subscriptions.allows_tier = original

    def test_doctypes_and_endpoints_are_in_place(self):
        for slug in (
            "cortex_subscription_settings",
            "cortex_subscription",
            "cortex_subscription_item",
            "cortex_stripe_event",
        ):
            path = ROOT / "cortex_rental" / "doctype" / slug / f"{slug}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual({f["fieldname"] for f in data["fields"]}, set(data["field_order"]), slug)
        settings = json.loads(
            (
                ROOT
                / "cortex_rental"
                / "doctype"
                / "cortex_subscription_settings"
                / "cortex_subscription_settings.json"
            ).read_text(encoding="utf-8")
        )
        fields = {f["fieldname"]: f for f in settings["fields"]}
        self.assertEqual(fields["enabled"]["default"], "0")
        self.assertEqual(fields["base_price_confirmed"]["default"], "0")
        self.assertEqual(fields["stripe_secret_key"]["fieldtype"], "Password")
        self.assertEqual([p["role"] for p in settings["permissions"]], ["System Manager"])
        api = (ROOT / "api" / "v1" / "subscriptions.py").read_text(encoding="utf-8")
        for name in ("get_subscription", "start_checkout", "open_portal"):
            self.assertIn(
                "_require_owner_company()", api.split(f"def {name}", 1)[1].split("@frappe.whitelist", 1)[0], name
            )
        self.assertIn("rate_limit", api.split("def subscription_webhook", 1)[0].rsplit("@frappe.whitelist", 1)[1])

    def test_rental_and_subscription_webhooks_use_different_secrets(self):
        quote = (ROOT / "services" / "quote_share.py").read_text(encoding="utf-8")
        self.assertIn("stripe_webhook_secret", quote)
        self.assertNotIn("Cortex Subscription Settings", quote)
        self.assertIn(
            "Cortex Subscription Settings", (ROOT / "services" / "subscriptions.py").read_text(encoding="utf-8")
        )


if __name__ == "__main__":
    unittest.main()
