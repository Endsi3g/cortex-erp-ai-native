"""Phase 6 : portail de demandes, calendrier public, suivi, chèque. Testé hors bench (base simulée)."""

import json
import pathlib
import unittest
from datetime import date, datetime
from types import SimpleNamespace

from cortex_rental.services import availability_summary, billing, client_portal
from cortex_rental.services.client_portal import PortalError

ROOT = pathlib.Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 7)
ITEMS = {"CAM": "Caméra A7", "LENS": "Objectif 35 mm"}


def form(**over):
    base = {
        "name": "Marie Tremblay",
        "email": "Marie@Exemple.CA",
        "phone": "514-555-0100",
        "organisation": "Studio Nord",
        "project": "Court métrage",
        "starts": "2026-10-20",
        "ends": "2026-10-22",
        "items": [{"item_code": "CAM", "quantity": 2}],
        "message": "Tournage de trois jours.",
        "consent": "1",
        "website": "",
    }
    base.update(over)
    return base


def code_of(**over):
    try:
        client_portal.validate_request(form(**over), TODAY, ITEMS)
    except PortalError as error:
        return error.code
    return None


class TestRequestValidation(unittest.TestCase):
    def test_a_good_request_is_cleaned(self):
        data = client_portal.validate_request(form(name="  Marie   Tremblay "), TODAY, ITEMS)
        self.assertEqual(data["email"], "marie@exemple.ca")
        self.assertEqual(data["name"], "Marie Tremblay")
        self.assertEqual(data["items"], [{"item_code": "CAM", "item_name": "Caméra A7", "quantity": 2}])
        self.assertEqual((data["starts"], data["ends"]), ("2026-10-20", "2026-10-22"))

    def test_bots_and_missing_consent_are_refused(self):
        self.assertEqual(code_of(website="http://spam"), "rejected")
        self.assertEqual(code_of(consent=""), "consent")

    def test_contact_details_are_checked(self):
        self.assertEqual(code_of(name="A"), "name")
        self.assertEqual(code_of(email="pas-un-courriel"), "email")
        self.assertEqual(code_of(phone="abc"), "phone")
        self.assertIsNone(code_of(phone=""))

    def test_period_rules(self):
        self.assertEqual(code_of(starts="2026-10-01"), "past_date")
        self.assertEqual(code_of(starts="2026-10-22", ends="2026-10-20"), "bad_period")
        self.assertEqual(code_of(starts="2026-10-10", ends="2027-03-01"), "too_long")
        self.assertEqual(code_of(starts="2029-01-01", ends="2029-01-02"), "too_far")
        self.assertEqual(code_of(starts="demain"), "bad_date")

    def test_items_must_belong_to_the_company_and_have_sane_quantities(self):
        self.assertEqual(code_of(items=[{"item_code": "AUTRE-SOCIETE"}]), "items")
        self.assertEqual(code_of(items=[{"item_code": "CAM", "quantity": 0}]), "items")
        self.assertEqual(code_of(items=[{"item_code": "CAM", "quantity": 100}]), "items")
        self.assertEqual(code_of(items="pas du json"), "items")
        self.assertEqual(code_of(items=[{"item_code": f"C{i}"} for i in range(31)]), "items")

    def test_items_as_json_text_and_duplicates(self):
        data = client_portal.validate_request(
            form(items=json.dumps([{"item_code": "CAM"}, {"item_code": "CAM"}, {"item_code": "LENS", "quantity": 3}])),
            TODAY,
            ITEMS,
        )
        self.assertEqual([(i["item_code"], i["quantity"]) for i in data["items"]], [("CAM", 1), ("LENS", 3)])

    def test_an_empty_request_needs_a_message(self):
        self.assertEqual(code_of(items=[], message="court"), "empty")
        self.assertIsNone(code_of(items=[], message="Je cherche du matériel de son pour un événement."))

    def test_markup_is_stripped_not_interpreted(self):
        data = client_portal.validate_request(
            form(name="<b>Marie</b> T", message="<script>alert(1)</script>Bonjour à tous"), TODAY, ITEMS
        )
        self.assertNotIn("<", data["name"] + data["message"])
        self.assertIn("Bonjour à tous", data["message"])


class TestPublicStates(unittest.TestCase):
    def test_every_inbound_status_has_a_client_wording(self):
        for status in ("Received", "Processing", "Processed", "Rejected"):
            view = client_portal.public_state(status)
            self.assertTrue(view["label"] and view["text"] and view["state"])
        self.assertEqual(client_portal.public_state("???")["state"], "received")

    def test_tokens_are_hashed_and_unique(self):
        self.assertNotEqual(client_portal.hash_token("a"), "a")
        self.assertEqual(len(client_portal.hash_token("a")), 64)


class TestDayStatuses(unittest.TestCase):
    NOW = datetime(2026, 10, 7, 12, 0)

    def item(self, fleet, blocks):
        return {
            "item_code": "CAM",
            "item_name": "Caméra",
            "category": "Camera",
            "fleet_quantity": fleet,
            "blocks": blocks,
        }

    def block(self, state, start, end, qty=1, hold_until=None):
        return {
            "rental_state": state,
            "starts_at": start,
            "ends_at": end,
            "qty": qty,
            "hold_until": hold_until,
            "customer": "SECRET",
        }

    def test_statuses_per_day_without_leaking_anything(self):
        items = [
            self.item(2, [self.block("Contract", "2026-10-21 00:00:00", "2026-10-22 00:00:00", 1)]),
            self.item(1, [self.block("Reservation", "2026-10-21 00:00:00", "2026-10-22 00:00:00", 1)]),
            self.item(0, []),
        ]
        rows = availability_summary.day_statuses(items, "2026-10-20", 3, self.NOW)
        self.assertEqual(rows[0]["days"], ["ok", "partial", "ok"])
        self.assertEqual(rows[1]["days"], ["ok", "full", "ok"])
        self.assertEqual(rows[2]["days"], ["none", "none", "none"])
        flat = json.dumps(rows)
        self.assertNotIn("SECRET", flat)
        self.assertNotIn("qty", flat)

    def test_quote_holds_count_only_while_valid(self):
        live = self.block("Quote", "2026-10-20 00:00:00", "2026-10-21 00:00:00", 1, "2026-10-08 12:00:00")
        expired = self.block("Quote", "2026-10-20 00:00:00", "2026-10-21 00:00:00", 1, "2026-10-06 12:00:00")
        self.assertEqual(
            availability_summary.day_statuses([self.item(1, [live])], "2026-10-20", 1, self.NOW)[0]["days"], ["full"]
        )
        self.assertEqual(
            availability_summary.day_statuses([self.item(1, [expired])], "2026-10-20", 1, self.NOW)[0]["days"], ["ok"]
        )

    def test_period_bounds(self):
        with self.assertRaises(ValueError):
            availability_summary.day_statuses([], "2026-10-20", 0, self.NOW)
        with self.assertRaises(ValueError):
            availability_summary.day_statuses([], "2026-10-20", 400, self.NOW)


class FakeDb:
    def __init__(self, enabled=True, today_count=0, inbound=None):
        self.enabled = enabled
        self.today_count = today_count
        self.inbound = inbound
        self.inserted = []

    def get_value(self, doctype, filters, fields=None, as_dict=False):
        if doctype == client_portal.SETTINGS:
            return SimpleNamespace(name="Cortex Test", portal_slug="studio") if self.enabled else None
        if doctype == "Company":
            return {"company_name": "Studio Test", "company_logo": ""}
        if doctype == client_portal.INBOUND:
            return self.inbound
        return None

    def count(self, doctype, filters=None):
        return self.today_count


class FakeDoc(SimpleNamespace):
    def insert(self, ignore_permissions=False):
        self.name = "CR-INB-2026-00001"
        self.ignored = ignore_permissions
        FakeDoc.last = self


class TestSubmitAndTrack(unittest.TestCase):
    def setUp(self):
        self._frappe = client_portal.frappe
        self._notify = client_portal._notify_team
        self._known = client_portal.known_items
        self._now = getattr(client_portal, "now_datetime", None)
        self._url = getattr(client_portal, "get_url", None)
        client_portal.known_items = lambda company: ITEMS
        client_portal._notify_team = lambda *a, **k: None
        client_portal.now_datetime = lambda: datetime(2026, 10, 7, 12, 0)
        client_portal.get_url = lambda path: f"https://cortex.test{path}"

    def tearDown(self):
        client_portal.frappe = self._frappe
        client_portal._notify_team = self._notify
        client_portal.known_items = self._known
        client_portal.now_datetime = self._now
        client_portal.get_url = self._url

    def frappe(self, **db):
        return SimpleNamespace(db=FakeDb(**db), get_doc=lambda payload: FakeDoc(**payload))

    def future_form(self):
        year = date.today().year + 1
        return form(starts=f"{year}-03-10", ends=f"{year}-03-12")

    def test_a_closed_portal_answers_like_a_missing_one(self):
        client_portal.frappe = self.frappe(enabled=False)
        with self.assertRaises(PortalError) as raised:
            client_portal.submit_request("studio", self.future_form())
        self.assertEqual(raised.exception.code, "closed")
        self.assertIsNone(client_portal.company_for_slug("pas un identifiant!"))

    def test_submission_stores_only_the_token_hash_and_creates_a_plain_inbound_request(self):
        client_portal.frappe = self.frappe()
        result = client_portal.submit_request("studio", self.future_form())
        token = result["tracking_url"].rsplit("/", 1)[1]
        doc = FakeDoc.last
        self.assertEqual(doc.tracking_hash, client_portal.hash_token(token))
        self.assertNotIn(token, json.dumps(doc.__dict__, default=str))
        self.assertEqual(
            (doc.doctype, doc.source_channel, doc.status), ("Cortex Inbound Request", "Web Portal", "Received")
        )
        self.assertTrue(doc.ignored)
        self.assertEqual(json.loads(doc.raw_payload)["items"][0]["item_code"], "CAM")

    def test_daily_cap_protects_the_team(self):
        client_portal.frappe = self.frappe(today_count=client_portal.DAILY_CAP)
        with self.assertRaises(PortalError) as raised:
            client_portal.submit_request("studio", self.future_form())
        self.assertEqual(raised.exception.code, "busy")

    def test_tracking_shows_nothing_personal_and_cleans_the_team_message(self):
        row = SimpleNamespace(
            name="CR-INB-2026-00001",
            company="Cortex Test",
            status="Processed",
            raw_payload=json.dumps(
                {
                    "email": "marie@exemple.ca",
                    "phone": "514-555-0100",
                    "name": "Marie",
                    "starts": "2026-10-20",
                    "ends": "2026-10-22",
                    "items": [
                        {"item_code": "CAM", "item_name": "Caméra A7", "quantity": 2},
                        {"item_code": "LENS", "item_name": "Objectif", "quantity": 1},
                    ],
                }
            ),
            public_message="<i>Un devis suit</i> demain.",
            creation=datetime(2026, 10, 7, 9, 30),
        )
        client_portal.frappe = SimpleNamespace(
            db=FakeDb(inbound=row),
            get_all=lambda *a, **k: [
                SimpleNamespace(item_code="CAM", image="/files/cam.jpg"),
                SimpleNamespace(item_code="LENS", image="/private/files/secret.jpg"),
            ],
        )
        view = client_portal.track("un-jeton")
        flat = json.dumps(view, ensure_ascii=False)
        self.assertEqual(view["state"], "done")
        self.assertNotIn("marie@exemple.ca", flat)
        self.assertNotIn("514-555-0100", flat)
        self.assertEqual(view["team_message"], "Un devis suit demain.")
        self.assertEqual(
            view["items"],
            [
                {"item_name": "Caméra A7", "quantity": 2, "image": "/files/cam.jpg"},
                {"item_name": "Objectif", "quantity": 1, "image": ""},  # photo privée : jamais montrée à un visiteur
            ],
        )

    def test_unknown_token_is_unknown(self):
        client_portal.frappe = SimpleNamespace(db=FakeDb(inbound=None))
        self.assertEqual(client_portal.track("nimporte"), {"state": "unknown"})
        self.assertEqual(client_portal.track(""), {"state": "unknown"})


class TestPublicPagesRender(unittest.TestCase):
    def render(self, name, **ctx):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 n'est pas installé")
        env = jinja2.Environment(autoescape=True)
        return env.from_string((ROOT / "www" / name).read_text(encoding="utf-8")).render(**ctx)

    def test_request_page_renders_open_and_closed(self):
        html = self.render(
            "demande.html", state="ok", info={"name": "Studio <Test>", "logo": ""}, slug="studio", title="t"
        )
        self.assertIn("Demander une location", html)
        self.assertIn("&lt;Test&gt;", html)  # le nom de la société est échappé
        self.assertIn('"studio"', html)
        closed = self.render("demande.html", state="closed", info={}, slug="", title="t")
        self.assertIn("Ce portail n'est pas disponible", closed)
        self.assertNotIn("<form", closed)

    def test_tracking_page_renders_states_and_escapes_the_team_message(self):
        view = {
            "state": "review",
            "label": "En cours d'examen",
            "text": "…",
            "reference": "CR-INB-1",
            "company": "Studio",
            "logo": "",
            "received": "2026-10-07 09:30",
            "starts": "2026-10-20",
            "ends": "2026-10-22",
            "items": [{"item_name": "Caméra", "quantity": 2}],
            "team_message": "<script>x</script>",
        }
        html = self.render("suivi.html", state="review", view=view, title="t", fmt_day=lambda v: v)
        self.assertIn("En cours d&#39;examen", html)  # l'apostrophe est échappée par Jinja
        self.assertIn("Caméra", html)
        self.assertIn("× 2", html)
        self.assertNotIn("<script>x</script>", html)
        self.assertIn(
            "Demande introuvable", self.render("suivi.html", state="unknown", view={}, title="t", fmt_day=lambda v: v)
        )

    def test_route_rules_and_noindex(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"/demande/<slug>"', hooks)
        self.assertIn('"/suivi/<token>"', hooks)
        for page in ("demande.html", "suivi.html"):
            self.assertIn("noindex", (ROOT / "www" / page).read_text(encoding="utf-8"))


class TestChequeAndSync(unittest.TestCase):
    def test_share_payment_follows_the_invoice_once_paid(self):
        calls = []
        original = billing.frappe
        try:
            billing.frappe = SimpleNamespace(
                db=SimpleNamespace(
                    get_value=lambda *a, **k: "Paid",
                    set_value=lambda doctype, name, field, value: calls.append((doctype, name, field, value)),
                ),
                get_all=lambda *a, **k: ["SHARE-1"],
                log_error=lambda **k: None,
            )
            billing._sync_share_payment("INV-1")
            self.assertEqual(calls, [("Cortex Quote Share", "SHARE-1", "payment_status", "Paid")])
            calls.clear()
            billing.frappe.db.get_value = lambda *a, **k: "Partially Paid"
            billing._sync_share_payment("INV-1")
            self.assertEqual(calls, [])  # un acompte partiel ne règle pas la page
        finally:
            billing.frappe = original

    def test_cheque_is_a_company_option_and_the_client_cannot_mark_it_paid(self):
        source = (ROOT / "services" / "quote_share.py").read_text(encoding="utf-8")
        body = source.split("def choose_cheque", 1)[1].split("\ndef ", 1)[0]
        self.assertIn('options["accept_cheque"]', body)
        self.assertIn('"payment_status": "Pending"', body)
        self.assertNotIn('"payment_status": "Paid"', body)
        page = (ROOT / "www" / "devis.html").read_text(encoding="utf-8")
        self.assertIn("quote_share.choose_cheque", page)
        self.assertIn("view.payment.cheque.chosen", page)

    def test_portal_fields_and_validation_exist(self):
        fields = {
            f["fieldname"]
            for f in json.loads(
                (
                    ROOT / "cortex_rental" / "doctype" / "cortex_finance_settings" / "cortex_finance_settings.json"
                ).read_text(encoding="utf-8")
            )["fields"]
        }
        self.assertTrue({"portal_requests_enabled", "portal_slug", "accept_cheque", "cheque_payable_to"} <= fields)
        source = (
            ROOT / "cortex_rental" / "doctype" / "cortex_finance_settings" / "cortex_finance_settings.py"
        ).read_text(encoding="utf-8")
        self.assertIn("déjà utilisé", source)

    def test_finance_lists_follow_cheques_and_portal_requests(self):
        ws = json.loads(
            (ROOT / "cortex_rental" / "workspace" / "cortex_finance" / "cortex_finance.json").read_text(
                encoding="utf-8"
            )
        )
        names = [b["data"]["quick_list_name"] for b in json.loads(ws["content"]) if b["type"] == "quick_list"]
        self.assertIn("Chèques annoncés", names)
        self.assertIn("Demandes du portail", names)
        self.assertEqual({q["label"] for q in ws["quick_lists"]}, set(names))


if __name__ == "__main__":
    unittest.main()
