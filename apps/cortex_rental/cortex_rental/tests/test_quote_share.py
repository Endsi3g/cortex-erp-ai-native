"""Portail de devis : jeton, instantané, droits du client et contrat des fichiers (sans banc Frappe)."""

import json
import os
import re
import unittest

from cortex_rental.services import payments, quote_share

MODULE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)))


def read(*parts):
    with open(os.path.join(MODULE_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


class TestToken(unittest.TestCase):
    def test_tokens_are_long_random_and_unique(self):
        tokens = {quote_share.new_token() for _ in range(200)}
        self.assertEqual(len(tokens), 200)
        self.assertTrue(all(len(t) >= 40 for t in tokens))

    def test_only_the_hash_is_kept_and_it_is_not_the_token(self):
        token = quote_share.new_token()
        digest = quote_share.hash_token(token)
        self.assertNotEqual(digest, token)
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, quote_share.hash_token(token))

    def test_the_share_doctype_never_stores_the_raw_token(self):
        spec = json.loads(read("cortex_rental", "doctype", "cortex_quote_share", "cortex_quote_share.json"))
        names = {f["fieldname"] for f in spec["fields"]}
        self.assertIn("token_hash", names)
        self.assertNotIn("token", names)
        fields = {f["fieldname"]: f for f in spec["fields"]}
        self.assertTrue(fields["token_hash"].get("hidden"))
        for perm in spec["permissions"]:
            self.assertFalse(perm.get("write") or perm.get("create") or perm.get("delete"), perm)


class TestClientCanOnlyAnswer(unittest.TestCase):
    def test_three_actions_only(self):
        self.assertEqual(set(quote_share.ACTIONS), {"accept", "decline", "changes"})

    def test_guest_endpoints_are_only_respond(self):
        source = read("api", "v1", "quote_share.py")
        guest = re.findall(r"allow_guest=True[^\n]*\n(?:\s*@[^\n]*\n)*\s*def (\w+)", source)
        self.assertEqual(guest, ["respond", "start_payment", "stripe_webhook"])

    def test_guest_respond_is_rate_limited(self):
        source = read("api", "v1", "quote_share.py")
        self.assertRegex(source, r"allow_guest=True.*\n\s*@rate_limit")

    def test_staff_endpoints_require_a_human_staff_role(self):
        source = read("api", "v1", "quote_share.py")
        for name in ("create_share", "list_shares", "revoke_share"):
            body = source.split(f"def {name}")[1].split("@frappe.whitelist")[0]
            self.assertIn("require_human_staff_role()", body, name)

    def test_accepting_does_not_reserve_or_write_the_rental(self):
        source = read("services", "quote_share.py")
        self.assertNotIn("request_reservation", source)
        self.assertNotIn('"Cortex Rental Transaction", tx', source.split("def respond")[1].split("_STATE_MESSAGES")[0])

    def test_public_page_is_noindex_and_escapes_values(self):
        html = read("www", "devis.html")
        self.assertIn("noindex", html)
        self.assertNotIn("|safe", html)
        self.assertNotIn("| safe", html)

    def test_route_rule_maps_the_token(self):
        self.assertIn('"/devis/<token>"', read("hooks.py"))

    def test_email_is_french_and_has_the_link(self):
        html = read("templates", "emails", "cortex_quote_share.html")
        self.assertIn("{{ link }}", html)
        self.assertIn("Consulter le devis", html)


class TestPayments(unittest.TestCase):
    SECRET = "whsec_test"
    BODY = b'{"type":"checkout.session.completed"}'

    def test_signed_event_is_accepted(self):
        header = payments.sign(self.BODY, self.SECRET)
        self.assertTrue(payments.verify_signature(self.BODY, header, self.SECRET))

    def test_wrong_secret_or_tampered_body_is_refused(self):
        header = payments.sign(self.BODY, self.SECRET)
        self.assertFalse(payments.verify_signature(self.BODY, header, "autre"))
        self.assertFalse(payments.verify_signature(self.BODY + b" ", header, self.SECRET))

    def test_old_or_malformed_signatures_are_refused(self):
        old = payments.sign(self.BODY, self.SECRET, stamp=1_000_000)
        self.assertFalse(payments.verify_signature(self.BODY, old, self.SECRET))
        for bad in ("", "t=abc,v1=00", "v1=00", "t=1"):
            self.assertFalse(payments.verify_signature(self.BODY, bad, self.SECRET), bad)
        self.assertFalse(payments.verify_signature(self.BODY, payments.sign(self.BODY, self.SECRET), ""))

    def test_checkout_amount_is_in_cents_and_carries_the_share(self):
        form = payments.checkout_form(
            73365, "CAD", "Acompte", "https://x/ok", "https://x/no", {"share": "abc", "invoice": "F1"}
        )
        self.assertEqual(form["line_items[0][price_data][unit_amount]"], "73365")
        self.assertEqual(form["line_items[0][price_data][currency]"], "cad")
        self.assertEqual(form["metadata[share]"], "abc")

    def test_no_key_means_no_call(self):
        with self.assertRaises(payments.PaymentError):
            payments.create_checkout_session("", {}, "k")

    def test_stripe_keys_are_encrypted_password_fields_and_options_are_off_by_default(self):
        spec = json.loads(read("cortex_rental", "doctype", "cortex_finance_settings", "cortex_finance_settings.json"))
        fields = {f["fieldname"]: f for f in spec["fields"]}
        self.assertEqual(fields["stripe_secret_key"]["fieldtype"], "Password")
        self.assertEqual(fields["stripe_webhook_secret"]["fieldtype"], "Password")
        self.assertEqual(fields["auto_reserve_on_accept"]["default"], "0")
        self.assertEqual(fields["online_payment_enabled"]["default"], "0")

    def test_the_portal_never_receives_a_secret(self):
        source = read("services", "quote_share.py")
        view = source.split("def payment_view")[1].split("def start_payment")[0]
        self.assertNotIn("secret_key", view.replace('options["online_payment"]', ""))
        self.assertNotIn("webhook_secret", view)

    def test_webhook_checks_the_signature_with_the_companys_own_secret(self):
        source = read("services", "quote_share.py")
        body = source.split("def handle_payment_event")[1]
        self.assertIn('options["webhook_secret"]', body)
        self.assertLess(body.index("verify_signature"), body.index("record_payment"))

    def test_payment_recording_is_idempotent_per_session(self):
        body = read("services", "quote_share.py").split("def handle_payment_event")[1]
        self.assertIn('"reference": reference', body)


class TestAutoReserve(unittest.TestCase):
    def test_runs_as_the_person_who_shared_and_falls_back_to_the_team(self):
        source = read("services", "quote_share.py")
        body = source.split("def _after_accept")[1].split("def _notify_team")[0]
        self.assertIn("frappe.set_user(doc.owner)", body)
        self.assertIn("Needs Review", body)
        self.assertIn("transition_to", body)

    def test_live_alert_carries_a_reserve_button_until_reserved(self):
        js = read("public", "js", "cortex_nav.js")
        self.assertIn("offerReservation", js)
        self.assertIn("request_reservation", js)


class TestAccidentalClicks(unittest.TestCase):
    def test_server_refuses_accept_and_decline_without_confirmation(self):
        body = read("services", "quote_share.py").split("def respond")[1].split("_find(token")[0]
        self.assertIn('action in ("accept", "decline")', body)
        self.assertIn("confirmed", body)

    def test_page_asks_for_a_checkbox_and_delays_the_send_button(self):
        html = read("www", "devis.html")
        self.assertIn('id="ok"', html)
        self.assertIn("confirmed:1", html)
        self.assertIn("window.setTimeout(refresh,700)", html)  # anti double toucher
        self.assertIn("if(busy||sent", html)  # un seul envoi

    def test_the_four_actions_are_in_the_fixed_bar_including_pdf(self):
        html = read("www", "devis.html")
        for needle in ('data-pick="accept"', 'data-pick="changes"', 'data-pick="decline"', 'id="pdf"'):
            self.assertIn(needle, html)

    def test_decline_is_not_styled_as_the_primary_action(self):
        html = read("www", "devis.html")
        self.assertIn('send.className = pick==="decline" ? "" : "primary"', html)


class TestText(unittest.TestCase):
    def test_clean_text_has_a_limit(self):
        self.assertLessEqual(len(quote_share.clean_text("a" * 5000)), quote_share.MAX_MESSAGE)


if __name__ == "__main__":
    unittest.main()
