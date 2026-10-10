"""Contrat avec l'API Gemini : ce que Cortex envoie doit passer la validation d'un serveur fidèle au protocole réel.

Le validateur est celui du faux serveur d'essai (`tools/bench/fake_gemini.py`) : types en majuscules, aucun `parameters` vide,
rôles qui alternent, schémas d'outils complets. Un défaut ici ferait refuser la requête par l'API réelle.
"""

import importlib.util
import os
import unittest

from cortex_rental.services.ai import tools
from cortex_rental.services.ai.providers import GeminiProvider

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "tools", "bench", "fake_gemini.py"))


def load_fake():
    spec = importlib.util.spec_from_file_location("fake_gemini", FAKE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDeclarations(unittest.TestCase):
    def provider(self):
        return GeminiProvider("gemini-3.8-flash", "k")

    def test_a_tool_without_arguments_is_declared_without_parameters(self):
        declarations = self.provider()._declarations([tools.REGISTRY["finance_summary"].declaration()])
        self.assertNotIn("parameters", declarations[0])
        self.assertEqual(declarations[0]["name"], "finance_summary")

    def test_types_are_uppercase_and_empty_required_is_dropped(self):
        decl = self.provider()._declarations([tools.REGISTRY["list_rentals"].declaration()])[0]
        params = decl["parameters"]
        self.assertEqual(params["type"], "OBJECT")
        self.assertNotIn("required", params)  # list_rentals n'a aucun paramètre obligatoire
        self.assertEqual(params["properties"]["state"]["type"], "STRING")

    def test_nested_array_items_are_converted_too(self):
        decl = self.provider()._declarations([tools.REGISTRY["propose_create_quote"].declaration()])[0]
        items = decl["parameters"]["properties"]["items"]
        self.assertEqual(items["type"], "ARRAY")
        self.assertEqual(items["items"]["type"], "OBJECT")
        self.assertEqual(items["items"]["properties"]["quantity"]["type"], "NUMBER")
        self.assertIn("customer", decl["parameters"]["required"])

    def test_the_original_registry_is_not_mutated(self):
        before = tools.REGISTRY["list_rentals"].parameters["type"]
        self.provider()._declarations([tools.REGISTRY["list_rentals"].declaration()])
        self.assertEqual(tools.REGISTRY["list_rentals"].parameters["type"], before)
        self.assertEqual(before, "object")

    def test_override_base_url_only_accepts_https_or_local(self):
        from types import SimpleNamespace
        from unittest import mock

        import cortex_rental.services.ai.providers as providers

        def base(value):
            fake = SimpleNamespace(conf={"cortex_ai_gemini_base_url": value})
            with mock.patch.dict("sys.modules", {"frappe": fake}):
                return GeminiProvider.base_url()

        self.assertEqual(base("http://127.0.0.1:9911/v1beta/"), "http://127.0.0.1:9911/v1beta")
        self.assertEqual(base("https://proxy.exemple.ca/v1beta"), "https://proxy.exemple.ca/v1beta")
        for bad in ("http://evil.example/v1beta", "ftp://x", "javascript:alert(1)", ""):
            self.assertEqual(base(bad), providers.GeminiProvider.BASE_URL)


@unittest.skipUnless(os.path.exists(FAKE), "le faux serveur n'est pas dans ce dossier (testé hors bench)")
class TestAgainstTheProtocolValidator(unittest.TestCase):
    def test_every_registered_tool_passes_the_protocol_validation(self):
        fake = load_fake()
        provider = GeminiProvider("gemini-3.8-flash", "k")
        declarations = [t.declaration() for t in tools.REGISTRY.values()]
        body = provider.request_body("système", [provider.user_message("bonjour")], declarations)
        problems, declared = fake.validate(body)
        self.assertEqual(problems, [])
        self.assertEqual(declared, set(tools.REGISTRY))

    def test_the_old_empty_properties_declaration_would_have_been_refused(self):
        fake = load_fake()
        body = {
            "contents": [{"role": "user", "parts": [{"text": "x"}]}],
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": "finance_summary",
                            "description": "d",
                            "parameters": {"type": "object", "properties": {}, "required": []},
                        }
                    ]
                }
            ],
        }
        problems, _ = fake.validate(body)
        self.assertTrue(any("properties" in p for p in problems))
        self.assertTrue(any("type" in p for p in problems))

    def test_a_tool_reply_must_follow_its_call(self):
        fake = load_fake()
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": "x"}]},
                {"role": "user", "parts": [{"functionResponse": {"name": "a", "response": {}}}]},
            ]
        }
        problems, _ = fake.validate(body)
        self.assertTrue(any("functionResponse" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
