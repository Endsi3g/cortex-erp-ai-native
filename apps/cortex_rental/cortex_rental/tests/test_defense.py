"""Code défensif : validation des fichiers, santé, frein de débit et contrat statique de tous les endpoints exposés."""

import ast
import os
import re
import unittest

from cortex_rental.services import defense, health

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 8
GIF = b"GIF89a" + b"\x00" * 16

# Seuls ces appels peuvent être faits sans compte; chacun doit être limité par adresse IP ou signé.
GUEST_ALLOWLIST = {
    "request_access",
    "resend_verification",
    "access_status",
    "respond",
    "start_payment",
    "choose_cheque",
    "portal_calendar",
    "submit_portal_request",
    "stripe_webhook",
    "health",
    "ready",
}


class TestImageSniffing(unittest.TestCase):
    def test_real_images_are_recognised(self):
        self.assertEqual(defense.sniff_image(PNG), "png")
        self.assertEqual(defense.sniff_image(JPEG), "jpg")
        self.assertEqual(defense.sniff_image(WEBP), "webp")

    def test_gif_only_when_allowed(self):
        self.assertIsNone(defense.sniff_image(GIF))
        self.assertEqual(defense.sniff_image(GIF, allowed=("gif",)), "gif")

    def test_disguised_files_are_refused(self):
        for fake in (
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            b"<html><script>alert(1)</script></html>",
            b"MZ\x90\x00\x03",  # exécutable Windows
            b"%PDF-1.7",
            b"",
            None,
            "<svg></svg>",  # Frappe renvoie du texte pour un contenu lisible
        ):
            self.assertIsNone(defense.sniff_image(fake), fake)

    def test_riff_that_is_not_webp_is_refused(self):
        self.assertIsNone(defense.sniff_image(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 8))


class TestRateLimitWithoutFrappe(unittest.TestCase):
    def test_hit_lets_everything_through_without_a_cache(self):
        # Sans bench (tests unitaires) il n'y a pas de Redis : on ne bloque rien.
        if defense.frappe is None:
            self.assertTrue(defense.hit("x", 1, 60))


class TestHealth(unittest.TestCase):
    def test_pending_patches_ignores_headers_and_comments(self):
        lines = ["[pre_model_sync]", "", "[post_model_sync]", "a.one", "a.two  # note", "# commentaire", "a.three"]
        self.assertEqual(health.pending_patches(lines, ["a.one", "a.three"]), ["a.two"])
        self.assertEqual(health.pending_patches(lines, ["a.one", "a.two", "a.three"]), [])

    def test_the_report_never_leaks_versions_or_hosts(self):
        src = open(os.path.join(APP_DIR, "api", "v1", "health.py"), encoding="utf-8").read()
        for leak in ("MariaDB", "Frappe Framework", "version"):
            self.assertNotIn(leak, src)

    def test_only_database_and_cache_are_critical(self):
        self.assertEqual(set(health.CRITICAL), {"database", "cache"})
        self.assertIn("scheduler", health.CHECKS)
        self.assertIn("migrations", health.CHECKS)


def _endpoints():
    """Tous les `@frappe.whitelist` de l'application : (fichier, fonction, décorateurs, source)."""
    found = []
    for folder, _dirs, files in os.walk(APP_DIR):
        if "tests" in folder or "__pycache__" in folder or "dev_tools" in folder:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8") as handle:
                src = handle.read()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.FunctionDef):
                    decorators = [ast.unparse(d) for d in node.decorator_list]
                    if any("frappe.whitelist" in d for d in decorators):
                        found.append(
                            (os.path.relpath(path, APP_DIR), node.name, decorators, ast.get_source_segment(src, node))
                        )
    return found


class TestEndpointContract(unittest.TestCase):
    def test_there_are_endpoints_to_audit(self):
        self.assertGreater(len(_endpoints()), 100)

    def test_every_endpoint_declares_its_http_methods(self):
        missing = [f"{p}:{n}" for p, n, d, _ in _endpoints() if not any("methods=" in x for x in d)]
        self.assertEqual(missing, [])

    def test_writes_are_post_only(self):
        verbs = re.compile(
            r"^(save|set|create|update|delete|revoke|sign_out|invite|finish|skip|complete|approve|reject|decide|record|change)"
        )
        loose = [
            f"{p}:{n}"
            for p, n, d, _ in _endpoints()
            if verbs.match(n) and not any("'POST'" in x or '"POST"' in x for x in d if "whitelist" in x)
        ]
        self.assertEqual(loose, [])

    def test_guest_endpoints_are_exactly_the_allowlist_and_all_limited(self):
        guests = {n: d for _p, n, d, _ in _endpoints() if any("allow_guest=True" in x for x in d)}
        self.assertEqual(set(guests), GUEST_ALLOWLIST)
        unlimited = [n for n, d in guests.items() if not any("rate_limit" in x for x in d)]
        self.assertEqual(unlimited, [])

    def test_every_non_guest_endpoint_reads_the_session_or_checks_a_permission(self):
        gate = re.compile(
            r"require_human_staff_role|get_company_context|has_permission|_require_|frappe\.session\.user|frappe\.only_for|"
            r"get_roles|account\.|account_insights\.|_user\(\)|guarded\(|check_permission"
        )
        weak = []
        for path, name, decorators, body in _endpoints():
            if any("allow_guest=True" in d for d in decorators):
                continue
            if path.startswith("cortex_rental/doctype"):  # méthodes de documents : contrôlées par les services appelés
                continue
            if not gate.search(body):
                weak.append(f"{path}:{name}")
        self.assertEqual(weak, [])

    def test_sensitive_actions_are_rate_limited_per_person(self):
        limited = {n for _p, n, d, _ in _endpoints() if any("limit_user" in x for x in d)}
        for needed in (
            "invite_team_member",
            "set_company_logo",
            "update_photo",
            "finish_onboarding",
            "sign_out_session",
        ):
            self.assertIn(needed, limited)


class TestExternalCallsAndSecrets(unittest.TestCase):
    def _sources(self):
        for folder, _dirs, files in os.walk(os.path.join(APP_DIR, "services")):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(folder, name)
                    yield path, open(path, encoding="utf-8").read()

    def test_every_outbound_http_call_has_a_timeout(self):
        for path, src in self._sources():
            for match in re.finditer(r"urlopen\(([^)]*)\)", src):
                self.assertIn(
                    "timeout", match.group(1), f"{os.path.relpath(path, APP_DIR)} : appel sans délai d'attente"
                )

    def test_secrets_are_never_hard_coded(self):
        pattern = re.compile("(sk_" + "live_|sk_" + "test_|AI" + "za[0-9A-Za-z_\\-]{20,}|whsec" + "_[0-9A-Za-z]{10,})")
        for folder, _dirs, files in os.walk(APP_DIR):
            if "__pycache__" in folder or "node_modules" in folder:
                continue
            for name in files:
                if name.endswith((".py", ".js", ".json", ".vue", ".html", ".csv")):
                    with open(os.path.join(folder, name), encoding="utf-8", errors="ignore") as handle:
                        self.assertIsNone(pattern.search(handle.read()), f"secret possible dans {name}")


class TestSecurityHeadersAndBrake(unittest.TestCase):
    def test_headers_are_registered_and_do_not_override_existing_ones(self):
        hooks = open(os.path.join(APP_DIR, "hooks.py"), encoding="utf-8").read()
        self.assertIn("cortex_rental.services.defense.security_headers", hooks)
        self.assertIn("cortex_rental.services.defense.request_brake", hooks)

        class Response:
            headers = {}

        class Headers(dict):
            def setdefault(self, key, value):
                return super().setdefault(key, value)

        response = Response()
        response.headers = Headers({"X-Frame-Options": "DENY"})
        defense.security_headers(response, None)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Strict-Transport-Security", response.headers)  # jamais en clair

    def test_microphone_is_allowed_for_the_page_itself_only(self):
        """La saisie vocale de l'assistant exige `microphone=(self)` ; `()` la bloquait pour tout le monde."""

        class Headers(dict):
            pass

        class Response:
            headers = Headers()

        response = Response()
        response.headers = Headers()
        defense.security_headers(response, None)
        policy = response.headers["Permissions-Policy"]
        self.assertIn("microphone=(self)", policy)
        self.assertNotIn("microphone=*", policy)
        self.assertIn("geolocation=()", policy)  # le reste reste fermé

    def test_the_global_brake_is_far_above_human_use(self):
        self.assertGreaterEqual(defense.USER_PER_MINUTE, 600)
        self.assertLessEqual(defense.GUEST_PER_MINUTE, 200)


if __name__ == "__main__":
    unittest.main()
