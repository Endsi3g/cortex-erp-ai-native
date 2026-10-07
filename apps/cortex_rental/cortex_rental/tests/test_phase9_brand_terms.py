"""Phase 9 : valeurs de départ des abonnements, conditions du contrat avec consentement, image de marque publique."""

import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from cortex_rental.services import brand, contract_terms, subscriptions

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestSubscriptionDefaults(unittest.TestCase):
    def test_defaults_are_editable_starting_values_and_charge_nothing(self):
        d = subscriptions.default_settings(["Studio B", "Studio A", ""])
        self.assertEqual((d["currency"], d["base_monthly_price"]), ("CAD", 1000.0))
        self.assertEqual(d["included_ai_budget"], 60.0)
        self.assertEqual(d["exempt_companies"], "Studio A\nStudio B")  # existantes exemptées, triées, sans vide
        self.assertFalse(d["base_price_confirmed"])
        self.assertEqual(d["base_price_id"], "")
        keys = {(r["kind"], r["key"]) for r in d["plan_items"]}
        self.assertEqual(
            keys, {("Module", "portal"), ("AI Tier", "equilibre"), ("AI Tier", "avance"), ("AI Tier", "luna")}
        )
        for row in d["plan_items"]:
            self.assertTrue(row["enabled"])  # offerte...
            self.assertFalse(row["price_confirmed"])  # ...mais prix à confirmer
            self.assertEqual(row["stripe_price_id"], "")
            self.assertGreater(row["monthly_price"], 0)

    def test_defaults_are_valid_but_cannot_activate_billing(self):
        d = subscriptions.default_settings(["A"])
        self.assertEqual(subscriptions.settings_problems(d), [])
        problems = subscriptions.settings_problems({**d, "enabled": 1})
        self.assertTrue(any("clé secrète" in p for p in problems))
        self.assertTrue(any("Confirmez le prix de base" in p for p in problems))
        self.assertTrue(any("Confirmez le prix de l'option" in p for p in problems))

    def test_existing_companies_keep_full_access_when_billing_is_switched_on(self):
        d = subscriptions.default_settings(["Studio A"])
        d.update(enabled=1, stripe_secret_key="x", stripe_webhook_secret="y")
        self.assertFalse(subscriptions.compute_entitlements(d, "Studio A", None)["enforced"])
        self.assertTrue(subscriptions.compute_entitlements(d, "Nouvelle Société", None)["enforced"])

    def test_seeding_runs_once_and_never_overwrites_a_configuration(self):
        calls = []

        class Doc(dict):
            def get(self, key, default=None):
                return dict.get(self, key, default)

            def update(self, values):
                calls.append(("update", values))

            def set(self, key, rows):
                calls.append(("set", key, len(rows)))

            def save(self, ignore_permissions=False):
                calls.append(("save", ignore_permissions))

        def fake(doc):
            return SimpleNamespace(
                db=SimpleNamespace(exists=lambda *a, **k: True),
                get_single=lambda name: doc,
                get_all=lambda *a, **k: ["Studio A"],
            )

        original = subscriptions.frappe
        try:
            subscriptions.frappe = fake(Doc())
            self.assertTrue(subscriptions.seed_defaults())
            self.assertIn(("set", "plan_items", 4), calls)
            for configured in (Doc(enabled=1), Doc(plan_items=[1]), Doc(exempt_companies="X")):
                calls.clear()
                subscriptions.frappe = fake(configured)
                self.assertFalse(subscriptions.seed_defaults())
                self.assertEqual(calls, [])
        finally:
            subscriptions.frappe = original

    def test_patch_endpoint_and_form_button_are_in_place(self):
        self.assertIn("cortex_rental.patches.seed_subscription_defaults", (ROOT / "patches.txt").read_text())
        api = (ROOT / "api" / "v1" / "subscriptions.py").read_text(encoding="utf-8")
        self.assertIn('frappe.only_for("System Manager")', api.split("def default_settings", 1)[1])
        js = (
            ROOT / "cortex_rental" / "doctype" / "cortex_subscription_settings" / "cortex_subscription_settings.js"
        ).read_text(encoding="utf-8")
        self.assertIn("Remplir avec les valeurs par défaut", js)
        self.assertIn("Rien n'est enregistré avant", js)


class TestContractTerms(unittest.TestCase):
    def test_company_text_wins_and_empty_falls_back_to_the_starting_template(self):
        self.assertEqual(contract_terms.terms_text("  Mes conditions \r\n"), "Mes conditions")
        self.assertEqual(contract_terms.terms_text(""), contract_terms.DEFAULT_TERMS.strip())
        self.assertEqual(contract_terms.terms_text(None), contract_terms.DEFAULT_TERMS.strip())
        self.assertLessEqual(len(contract_terms.terms_text("x" * 50000)), contract_terms.MAX_TERMS)

    def test_template_covers_the_essentials_and_states_the_consent(self):
        text = contract_terms.DEFAULT_TERMS.lower()
        for word in (
            "acompte",
            "retour",
            "dommages",
            "annulation",
            "paiement",
            "lu et compris",
            "signature électronique",
            "québec",
        ):
            self.assertIn(word, text)

    def test_snapshot_freezes_text_version_hash_and_requirement(self):
        snap = contract_terms.snapshot_terms(
            {"contract_terms": "Conditions A", "contract_terms_version": 3, "contract_require_consent": 1}
        )
        self.assertEqual((snap["terms_text"], snap["terms_version"], snap["terms_required"]), ("Conditions A", 3, True))
        self.assertEqual(snap["terms_hash"], contract_terms.terms_hash("Conditions A"))
        self.assertNotEqual(contract_terms.terms_hash("Conditions A"), contract_terms.terms_hash("Conditions B"))
        # Consentement exigé par défaut, désactivable par la société.
        self.assertTrue(contract_terms.snapshot_terms({})["terms_required"])
        self.assertFalse(contract_terms.snapshot_terms({"contract_require_consent": 0})["terms_required"])

    def test_acceptance_needs_the_explicit_consent_when_required(self):
        required = {"terms_required": True}
        self.assertIn("lu et compris", contract_terms.check_acceptance(required, 0))
        self.assertIn("lu et compris", contract_terms.check_acceptance(required, ""))
        for yes in (1, "1", True, "true", "on"):
            self.assertIsNone(contract_terms.check_acceptance(required, yes))
        self.assertIsNone(contract_terms.check_acceptance({"terms_required": False}, 0))
        self.assertIsNone(
            contract_terms.check_acceptance({}, 0)
        )  # devis envoyé avant cette règle : pas d'exigence rétroactive

    def test_technical_proof_is_a_hash_not_the_raw_address(self):
        proof = contract_terms.technical_proof("203.0.113.7", "Mozilla/5.0", "abc")
        self.assertEqual(len(proof), 64)
        self.assertNotIn("203.0.113.7", proof)
        self.assertNotEqual(proof, contract_terms.technical_proof("203.0.113.8", "Mozilla/5.0", "abc"))

    def test_respond_checks_consent_before_writing_and_keeps_the_proof(self):
        source = (ROOT / "services" / "quote_share.py").read_text(encoding="utf-8")
        body = source.split("def respond(", 1)[1].split("\n_STATE_MESSAGES", 1)[0]
        self.assertLess(body.index("check_acceptance"), body.index("frappe.db.set_value(SHARE, doc.name, changes)"))
        for field in ("terms_version", "terms_hash", "terms_accepted_at", "terms_accept_proof"):
            self.assertIn(field, body)
        api = (ROOT / "api" / "v1" / "quote_share.py").read_text(encoding="utf-8")
        self.assertIn("terms_accepted: int = 0", api)

    def test_version_goes_up_when_the_text_changes(self):
        source = (
            ROOT / "cortex_rental" / "doctype" / "cortex_finance_settings" / "cortex_finance_settings.py"
        ).read_text(encoding="utf-8")
        self.assertIn('self.has_value_changed("contract_terms")', source)
        self.assertIn("contract_terms_version", source)

    def test_doctype_fields_exist(self):
        def fields(slug):
            data = json.loads((ROOT / "cortex_rental" / "doctype" / slug / f"{slug}.json").read_text(encoding="utf-8"))
            return {f["fieldname"]: f for f in data["fields"]}

        finance = fields("cortex_finance_settings")
        self.assertEqual(finance["contract_require_consent"]["default"], "1")
        self.assertEqual(finance["contract_terms_version"]["read_only"], 1)
        self.assertEqual(finance["portal_banner_image"]["fieldtype"], "Attach Image")
        share = fields("cortex_quote_share")
        self.assertTrue({"terms_version", "terms_hash", "terms_accepted_at", "terms_accept_proof"} <= set(share))
        self.assertEqual(fields("cortex_rental_item_profile")["image"]["fieldtype"], "Attach Image")


class TestBrand(unittest.TestCase):
    def test_only_public_files_are_exposed(self):
        self.assertEqual(brand.public_file("/files/logo.png"), "/files/logo.png")
        for bad in (
            "/private/files/x.png",
            "https://evil.example/x.png",
            "/files/../private/x",
            "/files/a.png?x=1",
            "",
            None,
            "javascript:alert(1)",
        ):
            self.assertEqual(brand.public_file(bad), "", bad)

    def test_accent_is_validated_and_text_stays_readable_on_it(self):
        self.assertEqual(brand.accent("#7C2D12"), "#7c2d12")
        self.assertEqual(brand.accent("red; background:url(x)"), brand.DEFAULT_ACCENT)
        self.assertEqual(brand.accent(""), brand.DEFAULT_ACCENT)

        def ratio(a, b):
            la, lb = brand._luminance(a), brand._luminance(b)
            return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

        for color in ("#066336", "#7c2d12", "#fde047", "#ffffff", "#000000", "#2563eb", "#f59e0b"):
            ink = brand.readable_text_on(color)
            self.assertGreaterEqual(ratio(color, ink), 4.5, color)

    def test_branding_payload_is_clean(self):
        row = {
            "portal_tagline": "  Location   de matériel  ",
            "portal_banner_image": "/files/b.jpg",
            "portal_accent_color": "#7c2d12",
        }
        out = brand.branding(row, {"company_logo": "/private/files/logo.png"})
        self.assertEqual(out["logo"], "")  # logo privé : non montré
        self.assertEqual(
            (out["banner"], out["tagline"], out["accent"]), ("/files/b.jpg", "Location de matériel", "#7c2d12")
        )
        self.assertEqual(out["accent_ink"], "#ffffff")
        self.assertEqual(len(brand.branding({"portal_tagline": "x" * 500})["tagline"]), 140)
        self.assertEqual(brand.branding(None)["accent"], brand.DEFAULT_ACCENT)  # société sans réglage : couleur Cortex


class TestCortexSiteLink(unittest.TestCase):
    def test_site_url_accepts_only_clean_https_addresses(self):
        self.assertEqual(
            brand.site_url(" https://cortex.example/rejoindre?x=1 "), "https://cortex.example/rejoindre?x=1"
        )
        self.assertEqual(brand.site_url("https://cortex.example:8443"), "https://cortex.example:8443")
        for bad in (
            "",
            None,
            "http://cortex.example",
            "javascript:alert(1)",
            "//cortex.example",
            'https://x.example/"onmouseover="a',
            "https://x.example/ a",
            "https://" + "a" * 300,
        ):
            self.assertEqual(brand.site_url(bad), "", bad)


class TestPublicPages(unittest.TestCase):
    def render(self, name, **ctx):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 n'est pas installé")
        env = jinja2.Environment(autoescape=True)
        return env.from_string((ROOT / "www" / name).read_text(encoding="utf-8")).render(**ctx)

    def test_every_public_page_has_the_cortex_footer_and_noindex(self):
        for page in ("demande.html", "suivi.html", "devis.html"):
            html = (ROOT / "www" / page).read_text(encoding="utf-8")
            self.assertIn("Propulsé par Cortex", html, page)
            self.assertIn("cortex-logo.svg", html, page)

    def test_footer_links_to_the_cortex_site_only_when_one_is_configured(self):
        for page, ctx in (
            ("demande.html", {"state": "ok", "info": {"name": "S"}, "slug": "s", "title": "t"}),
            ("suivi.html", {"view": {"state": "unknown"}, "state": "unknown", "title": "t"}),
        ):
            linked = self.render(page, cortex_site="https://cortex.example/", **ctx)
            self.assertIn('<a href="https://cortex.example/" target="_blank" rel="noopener"', linked, page)
            plain = self.render(page, cortex_site="", **ctx)
            self.assertNotIn('target="_blank" rel="noopener" aria-label="Propulsé par Cortex', plain, page)
            self.assertIn("Propulsé par Cortex", plain, page)  # le texte reste, sans lien inventé
            self.assertIn("cortex-logo-reversed.svg", plain, page)  # logo lisible en mode sombre

    def test_received_screen_is_airy_with_an_icon_only_copy_button_on_narrow_screens(self):
        html = (ROOT / "www" / "demande.html").read_text(encoding="utf-8")
        self.assertIn('id="copy" class="primary ib" aria-label="Copier le lien"', html)
        self.assertIn(".ib .lbl{display:none}", html)  # petit écran : icône seule, le nom accessible reste
        self.assertIn('class="card faq"', html)
        self.assertNotIn("grid2", html)  # une seule colonne : une idée par carte

    def test_request_page_shows_logo_banner_tagline_and_the_branded_color(self):
        info = {
            "name": "Studio",
            "logo": "/files/l.png",
            "banner": "/files/b.jpg",
            "tagline": "Matériel pro",
            "accent": "#7c2d12",
            "accent_ink": "#ffffff",
        }
        html = self.render("demande.html", state="ok", info=info, slug="studio", title="t")
        self.assertIn('src="/files/l.png"', html)
        self.assertIn('src="/files/b.jpg"', html)
        self.assertIn("Matériel pro", html)
        self.assertIn("--brand:#7c2d12", html)
        for control in ("copy", "ics", "mail", "print", "again", "open-track", "track-link", "recap-items"):
            self.assertIn(f'id="{control}"', html)  # écran « Demande reçue » interactif
        plain = self.render("demande.html", state="ok", info={"name": "Studio"}, slug="studio", title="t")
        self.assertNotIn('class="hero"', plain.split("<body>", 1)[1])

    def test_quote_page_asks_for_the_consent_and_shows_the_frozen_terms(self):
        quote = {
            "company": "Studio",
            "logo": "",
            "reference": "CR-1",
            "customer": "Acme",
            "starts_at": "2026-10-20 09:00:00",
            "ends_at": "2026-10-22 09:00:00",
            "billable_days": 2,
            "project": "",
            "message": "",
            "valid_until": "2026-11-01",
            "total": 100,
            "subtotal": 87,
            "tps": 4,
            "tvq": 9,
            "lines": [
                {
                    "item_name": "Caméra",
                    "quantity": 1,
                    "billable_days": 2,
                    "daily_rate": 50,
                    "amount": 100,
                    "image": "/files/c.jpg",
                    "discount_percentage": 0,
                }
            ],
            "deposit_total": 0,
            "deposit_percent": 0,
            "terms_text": "Condition A\nCondition B",
            "terms_version": 4,
            "terms_required": True,
            "brand": {"accent": "#7c2d12", "accent_ink": "#ffffff"},
        }
        view = {"state": "ok", "quote": quote}
        html = self.render(
            "devis.html",
            view=view,
            quote=quote,
            token="tok",
            view_token="tok",
            fmt=str,
            num=str,
            share=lambda a: 0,
            pct=lambda a: 0,
            fmt_date=str,
            fmt_day=str,
            title="t",
        )
        self.assertIn("Conditions du contrat", html)
        self.assertIn("version 4", html)
        self.assertIn("Condition A", html)
        self.assertIn('id="terms-ok"', html)
        self.assertIn("J'ai lu et compris les conditions du contrat", html)
        self.assertIn("terms_accepted:termsOk.checked?1:0", html)
        self.assertIn('src="/files/c.jpg"', html)
        self.assertIn("termsRequired=true", html.replace(" ", ""))

    def test_inline_scripts_of_rendered_pages_are_valid_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node est requis")
        import re

        html = self.render("demande.html", state="ok", info={"name": "S"}, slug="s", title="t") + self.render(
            "suivi.html",
            state="review",
            view={
                "state": "review",
                "label": "L",
                "text": "T",
                "reference": "R",
                "company": "C",
                "received": "x",
                "starts": "2026-10-20",
                "ends": "2026-10-22",
                "items": [],
                "team_message": "",
            },
            title="t",
            fmt_day=str,
        )
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        self.assertEqual(len(scripts), 2)
        with tempfile.TemporaryDirectory() as folder:
            for index, code in enumerate(scripts):
                path = pathlib.Path(folder) / f"s{index}.js"
                path.write_text(code, encoding="utf-8")
                result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
