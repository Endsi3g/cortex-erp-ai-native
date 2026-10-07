"""Phase 5 : modèles de taxes validés côté serveur, formats d'impression intégrés, Finance et paiements."""

import json
import pathlib
import unittest
from types import SimpleNamespace

from cortex_rental.services import tax_presets

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "cortex_rental"


class TestTaxPresets(unittest.TestCase):
    def test_quebec_preset_matches_the_doctype_defaults(self):
        fields = {
            f["fieldname"]: f
            for f in json.loads(
                (MODULE / "doctype" / "cortex_finance_settings" / "cortex_finance_settings.json").read_text(
                    encoding="utf-8"
                )
            )["fields"]
        }
        qc = tax_presets.PRESETS["qc"]
        self.assertEqual(float(fields["tps_rate"]["default"]), qc["tps_rate"])
        self.assertEqual(float(fields["tvq_rate"]["default"]), qc["tvq_rate"])

    def test_every_preset_stays_inside_the_servers_rate_limits(self):
        for key, preset in tax_presets.PRESETS.items():
            self.assertTrue(0 <= preset["tps_rate"] <= tax_presets.MAX_RATE, key)
            self.assertTrue(0 <= preset["tvq_rate"] <= tax_presets.MAX_RATE, key)

    def test_matching_preset_recognises_exact_rates_only(self):
        self.assertEqual(tax_presets.matching_preset({"apply_taxes": 1, "tps_rate": 5, "tvq_rate": 9.975}), "qc")
        self.assertEqual(tax_presets.matching_preset({"apply_taxes": 1, "tps_rate": 5, "tvq_rate": 0}), "tps")
        self.assertEqual(tax_presets.matching_preset({"apply_taxes": 0, "tps_rate": 0, "tvq_rate": 0}), "none")
        self.assertEqual(tax_presets.matching_preset({"apply_taxes": 1, "tps_rate": 5, "tvq_rate": 10}), "custom")

    def test_apply_requires_write_permission_and_a_known_preset(self):
        class Thrown(Exception):
            pass

        def throw(message, exc=None):
            raise (exc or Thrown)(message)

        original = tax_presets.frappe
        try:
            tax_presets.frappe = SimpleNamespace(
                throw=throw,
                ValidationError=ValueError,
                PermissionError=PermissionError,
                has_permission=lambda *a, **k: False,
            )
            with self.assertRaises(ValueError):
                tax_presets.apply_preset("Cortex Test", "hst-ontario")
            with self.assertRaises(PermissionError):
                tax_presets.apply_preset("Cortex Test", "qc")
        finally:
            tax_presets.frappe = original

    def test_validation_still_bounds_manual_rates(self):
        source = (MODULE / "doctype" / "cortex_finance_settings" / "cortex_finance_settings.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("0 <= (self.get(field) or 0) <= 30", source)

    def test_endpoints_are_registered_with_explicit_methods(self):
        source = (ROOT / "api" / "v1" / "billing.py").read_text(encoding="utf-8")
        self.assertIn('@frappe.whitelist(methods=["GET"])\n    @defense.safe_input\n    def tax_presets', source)
        self.assertIn(
            '@frappe.whitelist(methods=["POST"])\n    @defense.safe_input\n    @defense.limit_user("tax_preset", 20)\n    def apply_tax_preset',
            source,
        )


class TestInvoicePrintFormats(unittest.TestCase):
    def formats(self):
        out = {}
        for folder in (MODULE / "print_format").iterdir():
            if folder.is_dir():
                path = folder / f"{folder.name}.json"
                if path.exists():
                    out[folder.name] = json.loads(path.read_text(encoding="utf-8"))
        return out

    def test_a4_and_letter_formats_exist_and_are_standard_jinja(self):
        formats = self.formats()
        self.assertEqual({f["name"] for f in formats.values()}, {"Facture Cortex A4", "Facture Cortex Lettre"})
        for fmt in formats.values():
            self.assertEqual(fmt["doc_type"], "Cortex Rental Invoice")
            self.assertEqual((fmt["standard"], fmt["custom_format"], fmt["print_format_type"]), ("Yes", 1, "Jinja"))
        self.assertIn("size: A4", formats["facture_cortex_a4"]["css"])
        self.assertIn("size: letter", formats["facture_cortex_lettre"]["css"])

    def test_template_renders_with_real_looking_data(self):
        try:
            import jinja2
        except ImportError:
            self.skipTest("jinja2 n'est pas installé")

        class Row(SimpleNamespace):
            def get_formatted(self, field, doc=None):
                return f"{getattr(self, field):.2f} $"

        class Doc(SimpleNamespace):
            def get_formatted(self, field):
                value = getattr(self, field)
                return f"{value:.2f} $" if isinstance(value, (int, float)) else str(value)

        doc = Doc(
            company="Cortex Test",
            name="CR-INV-0001",
            customer="CUST-1",
            rental_transaction="CR-TRX-0001",
            issue_date="2026-10-07",
            due_date="2026-10-21",
            tps_number="123456789 RT0001",
            tvq_number="",
            lines=[Row(description="Caméra A7", item_code="CAM", qty=2, days=3, rate=150.0, amount=900.0)],
            subtotal=900.0,
            tps_amount=45.0,
            tvq_amount=89.78,
            total=1034.78,
            amount_paid=300.0,
            balance=734.78,
            notes="Merci!",
        )
        frappe = SimpleNamespace(db=SimpleNamespace(get_value=lambda *a, **k: "Studio Mont-Royal"))
        for fmt in self.formats().values():
            html = jinja2.Template(fmt["html"]).render(doc=doc, frappe=frappe, _=lambda s: s)
            for expected in (
                "CR-INV-0001",
                "Studio Mont-Royal",
                "Caméra A7",
                "1034.78 $",
                "734.78 $",
                "TPS",
                "TVQ",
                "Merci!",
            ):
                self.assertIn(expected, html)
            self.assertNotIn("TVQ : ", html)  # numéro de TVQ vide : jamais « TVQ : » seul

    def test_patch_registered_and_never_overrides_a_chosen_default(self):
        self.assertIn("cortex_rental.patches.set_invoice_print_defaults", (ROOT / "patches.txt").read_text())
        source = (ROOT / "patches" / "set_invoice_print_defaults.py").read_text(encoding="utf-8")
        self.assertIn('frappe.db.get_value("DocType", DOCTYPE, "default_print_format")', source)


class TestFinanceScreens(unittest.TestCase):
    def test_finance_workspace_shows_invoice_tables_and_keeps_shortcuts(self):
        ws = json.loads((MODULE / "workspace" / "cortex_finance" / "cortex_finance.json").read_text(encoding="utf-8"))
        content = json.loads(ws["content"])
        quick = [b["data"]["quick_list_name"] for b in content if b["type"] == "quick_list"]
        self.assertEqual(quick, ["Factures à encaisser", "Factures récentes"])
        self.assertEqual({q["label"] for q in ws["quick_lists"]}, set(quick))
        shortcuts = {b["data"]["shortcut_name"] for b in content if b["type"] == "shortcut"}
        self.assertTrue({"Factures", "Paiements", "Réglages financiers", "Créances par client"} <= shortcuts)

    def test_payment_form_leads_with_the_customer_and_opens_its_invoice(self):
        js = (MODULE / "doctype" / "cortex_rental_payment" / "cortex_rental_payment.js").read_text(encoding="utf-8")
        self.assertIn("customers.summary", js)
        self.assertIn('frappe.set_route("Form", "Cortex Rental Invoice", frm.doc.invoice)', js)

    def test_payment_list_has_kind_indicators(self):
        js = (MODULE / "doctype" / "cortex_rental_payment" / "cortex_rental_payment_list.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Refund", js)
        self.assertIn("Remboursement", js)

    def test_new_email_label_is_translated(self):
        self.assertIn("New Email,Nouveau courriel", (ROOT / "translations" / "fr.csv").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
