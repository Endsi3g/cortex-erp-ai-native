"""Mon compte v2 : appareils, statistiques, approbations (règle des deux personnes et seul approbateur)."""

import json
import os
import unittest

from cortex_rental.services.devices import device_label, fingerprint, parse_user_agent

BASE = os.path.dirname(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(BASE, *parts), encoding="utf-8") as handle:
        return handle.read()


IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
PIXEL = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36"


class TestUserAgentParsing(unittest.TestCase):
    def test_iphone_is_identified_as_ios_phone_with_safari(self):
        info = parse_user_agent(IOS)
        self.assertEqual(
            (info["os"], info["os_version"], info["device_type"], info["browser"]), ("iOS", "18", "Phone", "Safari")
        )

    def test_edge_is_not_mistaken_for_chrome_and_windows_version_is_honest(self):
        info = parse_user_agent(EDGE)
        self.assertEqual(info["browser"], "Edge")
        self.assertEqual(info["os_version"], "10 ou 11")  # NT 10.0 ne distingue pas Windows 10 de 11

    def test_android_model_is_read(self):
        info = parse_user_agent(PIXEL)
        self.assertEqual((info["model"], info["device_type"]), ("Pixel 8", "Phone"))

    def test_an_empty_agent_is_never_guessed(self):
        self.assertEqual(device_label(parse_user_agent("")), "Appareil non identifié")

    def test_the_session_id_is_never_stored_only_its_hash(self):
        self.assertNotEqual(fingerprint("abc"), "abc")
        self.assertEqual(len(fingerprint("abc")), 64)
        src = read("services", "devices.py")
        self.assertNotIn('"sid":', src)


class TestRevocation(unittest.TestCase):
    def test_a_person_can_only_revoke_their_own_sessions(self):
        src = read("services", "account.py")
        body = src.split("def sign_out_session")[1].split("def sign_out_other_sessions")[0]
        self.assertIn("_user()", body)
        self.assertIn("devices.revoke(user,", body)

    def test_the_current_device_cannot_be_revoked_from_the_list(self):
        self.assertIn("current_sid", read("services", "devices.py").split("def revoke(")[1].split("def revoke_all")[0])

    def test_team_revocation_requires_the_owner_and_membership_and_is_audited(self):
        body = read("services", "administration.py").split("def sign_out_member")[1].split("# ---- imports")[0]
        for needle in ("_require_team_admin(company)", "_require_member(company, email)", "record_mutation"):
            self.assertIn(needle, body)

    def test_disabling_a_member_closes_their_sessions(self):
        body = read("services", "administration.py").split("def set_member_enabled")[1].split("def team_devices")[0]
        self.assertIn("devices.revoke_all(email", body)

    def test_login_is_tracked_by_a_session_hook(self):
        self.assertIn('on_session_creation = ["cortex_rental.services.devices.on_login"]', read("hooks.py"))


class TestApprovalRules(unittest.TestCase):
    def test_raw_approval_form_is_not_offered_and_a_dialog_replaces_it(self):
        data = json.loads(read("cortex_rental", "doctype", "approval_request", "approval_request.json"))
        self.assertEqual(data.get("in_create"), 1)
        self.assertIn(
            "requestContractApproval", read("cortex_rental", "doctype", "approval_request", "approval_request_list.js")
        )

    def test_requester_cannot_approve_or_reject_their_own_request_unless_sole_approver(self):
        src = read("cortex_rental", "doctype", "approval_request", "approval_request.py")
        self.assertIn("sole_approver_may_self_approve(self.company, current_user)", src)
        self.assertIn("self_approved", src)
        self.assertIn("Retirer ma demande", src)

    def test_the_sole_approver_rule_is_a_company_setting_off_by_default(self):
        data = json.loads(read("cortex_rental", "doctype", "cortex_finance_settings", "cortex_finance_settings.json"))
        field = next(f for f in data["fields"] if f["fieldname"] == "allow_sole_approver_self_approval")
        self.assertEqual(field["default"], "0")
        self.assertIn("if not flag", read("cortex_rental", "doctype", "approval_request", "approval_request.py"))

    def test_withdraw_is_for_the_author_only(self):
        src = read("cortex_rental", "doctype", "approval_request", "approval_request.py")
        self.assertIn("Seule la personne qui a fait la demande peut la retirer", src)


class TestInsightsAreReadOnlyAndScoped(unittest.TestCase):
    def test_every_endpoint_acts_on_the_signed_in_person_only(self):
        src = read("api", "v1", "account.py")
        for name in ("stats", "history", "my_approvals", "login_history", "inbox", "preferences"):
            body = src.split(f"def {name}(")[1].split("@frappe.whitelist")[0]
            self.assertTrue("_me()" in body or "account._user()" in body, name)
            self.assertNotIn("user:", body.split("):")[0], name)  # aucun paramètre ne désigne une autre personne

    def test_reminders_respect_personal_preferences(self):
        self.assertIn("account_insights.wants(user, pref)", read("services", "reminders.py"))


class TestAccountPagesAndRoles(unittest.TestCase):
    PAGES = ("profil", "statistiques", "approbations", "activite", "securite", "notifications", "societe")

    def test_each_account_page_is_a_dedicated_entry_in_the_sidebar(self):
        nav = read("public", "js", "cortex_nav.js")
        admin = nav.split('title: "Administration"')[1]
        self.assertNotIn('title: "Mon compte"', nav)  # fusionné dans « Administration »
        for page in self.PAGES:
            self.assertIn(f'href: "/app/cortex-account/{page}"', admin)
            self.assertIn(f'owns: ["cortex-account/{page}"]', admin)

    def test_each_account_page_has_a_subtitle(self):
        pages = read("public", "js", "cortex_pages.js")
        for page in self.PAGES:
            self.assertIn(f'"cortex-account/{page}":', pages)

    def test_roles_are_shown_as_one_plain_profile_never_as_a_pile_of_pills(self):
        src = read("services", "account_insights.py")
        for label in ("Propriétaire", "Gestionnaire", "Comptoir", "Inventaire", "Finance", "Lecture seule"):
            self.assertIn(f'"{label}"', src)
        page = read("cortex_rental", "page", "cortex_account", "cortex_account.js")
        self.assertNotIn("cx-acct-chip", page)

    def test_the_page_is_single_column_and_left_aligned(self):
        css = read("public", "css", "cortex-account.css")
        self.assertNotIn("cx-acct-cols", read("cortex_rental", "page", "cortex_account", "cortex_account.js"))
        self.assertIn(".cx-acct-body {\n\tdisplay: grid;", css)

    def test_statistics_open_the_list_that_composes_them(self):
        page = read("cortex_rental", "page", "cortex_account", "cortex_account.js")
        self.assertIn("data-go=", page)
        src = read("services", "account_insights.py")
        for kind in ("quotes_created", "checkouts", "returns", "payments_recorded"):
            self.assertIn(f'"{kind}":', src)

    def test_team_activity_is_only_for_people_who_can_read_the_audit_log(self):
        body = read("services", "account_insights.py").split("def history(")[1].split("# -----")[0]
        self.assertIn('frappe.has_permission("Audit Event", "read")', body)
        self.assertIn("confirmed_by", body)

    def test_profile_photo_is_a_real_circle_and_uploadable(self):
        css = read("public", "css", "cortex-account.css")
        self.assertIn("aspect-ratio: 1 / 1;", css)
        self.assertIn("FileUploader", read("cortex_rental", "page", "cortex_account", "cortex_account.js"))


class TestPresenceTooltip(unittest.TestCase):
    def test_the_pill_shows_only_avatars_and_the_detail_is_a_tooltip(self):
        nav = read("public", "js", "cortex_nav.js")
        self.assertNotIn("cx-pill-count", nav)
        self.assertIn('role: "tooltip"', nav)
        self.assertIn("describeRoute()", nav)

    def test_the_screen_a_person_is_on_is_text_only_short_lived_and_never_written_to_records(self):
        src = read("services", "team_activity.py")
        self.assertIn("expires_in_sec=WHERE_TTL_SECONDS", src)
        self.assertIn("[:80]", src)
        self.assertNotIn("db.set_value", src.split("def remember_where")[1].split("def recall_where")[0])


class TestApprovalPolicyAndExport(unittest.TestCase):
    def test_enabling_the_rule_needs_the_owner_and_an_acknowledgement_and_is_audited(self):
        src = read("services", "approval_policy.py")
        self.assertIn("can_manage_team(user)", src)
        self.assertIn("if enabled and not acknowledged", src)
        self.assertIn("cortex.approvals.self_approval_changed", src)

    def test_benefits_and_dangers_are_written_once_and_shown_in_the_dialog(self):
        src = read("services", "approval_policy.py")
        self.assertIn("BENEFITS", src)
        self.assertIn("DANGERS", src)
        dialog = read("public", "js", "cortex_policy.js")
        self.assertIn("p.benefits", dialog)
        self.assertIn("p.dangers", dialog)
        self.assertIn("J'ai compris les risques", dialog)

    def test_a_patch_resets_the_old_default(self):
        self.assertIn("disable_sole_approver_default", read("patches.txt"))

    def test_the_internal_action_code_is_never_shown_on_the_approval_form(self):
        form = read("cortex_rental", "doctype", "approval_request", "approval_request.js")
        self.assertIn('frm.toggle_display("action", false)', form)
        self.assertIn("approvalActionLabel", form)

    def test_export_is_one_button_that_asks_for_the_format(self):
        page = read("cortex_rental", "page", "cortex_account", "cortex_account.js")
        self.assertNotIn("Télécharger (CSV)", page)
        self.assertIn("cortex.exportData", page)
        export = read("public", "js", "cortex_export.js")
        self.assertIn("buildPdf", export)
        self.assertIn("buildCsv", export)
        self.assertIn('choice("pdf"', export)

    def test_the_logo_is_owner_only_public_and_never_svg(self):
        src = read("services", "administration.py").split("def set_company_logo")[1].split("# ---- appareils")[0]
        self.assertIn("_require_team_admin(company)", src)
        self.assertIn('LOGO_EXT = (".png", ".jpg", ".jpeg", ".webp")', read("services", "administration.py"))
        self.assertIn('"is_private": 0', src)
        self.assertIn("cortex.company.logo_changed", src)

    def test_the_logo_is_a_step_of_the_onboarding(self):
        data = json.loads(read("cortex_rental", "module_onboarding", "cortex_rental", "cortex_rental.json"))
        self.assertIn("Ajouter le logo de votre entreprise", [s["step"] for s in data["steps"]])


class TestLinkedDossier(unittest.TestCase):
    def test_forms_show_their_linked_dossier(self):
        for doctype in ("cortex_rental_transaction", "cortex_rental_invoice", "cortex_rental_payment"):
            self.assertIn("cortex.dossier(frm)", read("cortex_rental", "doctype", doctype, f"{doctype}.js"))

    def test_the_dossier_is_read_only_company_scoped_and_permission_checked(self):
        src = read("services", "dossier.py")
        self.assertIn("doc.company != company", src)
        self.assertIn('frappe.has_permission(doctype, "read", doc)', src)
        self.assertNotIn(".save(", src)
        self.assertNotIn(".insert(", src)
        for doctype in ("INVOICE", "PAYMENT", '"Approval Request"', '"Audit Event"'):
            self.assertIn(f"_can({doctype})", src)

    def test_the_dossier_is_registered(self):
        hooks = read("hooks.py")
        self.assertIn("cortex_dossier.js", hooks)
        self.assertIn("cortex-dossier.css", hooks)


class TestAvailabilityCellActions(unittest.TestCase):
    def test_a_cell_offers_a_prefilled_quote_and_the_existing_loans(self):
        vue = read("public", "js", "cortex_availability", "CortexAvailability.vue")
        self.assertIn("Créer un devis avec cet équipement ce jour-là", vue)
        self.assertIn("cortex_rental.api.v1.rentals.create_quote_draft", vue)
        self.assertIn("item_code: s.row.item.item_code", vue)
        self.assertIn("cortex_rental.api.v1.dossier.get", vue)

    def test_account_styles_never_reuse_a_navigation_class_name(self):
        css = read("public", "css", "cortex-account.css")
        self.assertNotIn("\\n.cx-sub {", css)
