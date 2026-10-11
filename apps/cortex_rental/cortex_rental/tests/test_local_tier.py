"""Niveau Cortex Local (Gemma 4 par Docker Model Runner, API compatible OpenAI) : sans banc Frappe, avec un faux serveur local."""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from cortex_rental.services import subscriptions
from cortex_rental.services.ai import settings as ai_settings
from cortex_rental.services.ai.gateway import TierUnavailable, resolve_tier
from cortex_rental.services.ai.providers import AIConfigurationError, LocalOpenAIProvider, OpenAIProvider, provider_for


def values(**over):
    base = dict(ai_settings.DEFAULTS)
    base.update(api_key="", anthropic_api_key="", openai_api_key="", local_base_url="", company_limits={})
    base.update(over)
    return base


class TestLocalTier(unittest.TestCase):
    def test_ai_prefix_selects_the_local_provider_without_a_key(self):
        provider = provider_for("ai/gemma4", "")
        self.assertIsInstance(provider, LocalOpenAIProvider)
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertFalse(provider.requires_key)

    def test_tier_is_offered_only_when_the_runner_address_is_set(self):
        rows = {t["key"]: t for t in ai_settings.tiers(values())}
        self.assertFalse(rows["local"]["configured"])
        rows = {t["key"]: t for t in ai_settings.tiers(values(local_base_url="http://127.0.0.1:12434/engines/v1"))}
        self.assertTrue(rows["local"]["configured"])
        self.assertEqual(rows["local"]["model"], "ai/gemma4")
        self.assertEqual(rows["local"]["cost_index"], 0)  # pas de coût par jeton, pas d'indice inventé
        self.assertEqual(ai_settings.default_tier(values(local_base_url="http://x", default_tier="rapide")), "local")

    def test_resolve_refuses_clearly_without_the_runner(self):
        with self.assertRaises(AIConfigurationError):
            resolve_tier(values(), "local")  # rien de configuré du tout
        with self.assertRaises(TierUnavailable):
            resolve_tier(
                values(api_key="g"), "local"
            )  # un autre niveau existe : refus net, jamais de remplacement silencieux

    def test_known_to_subscriptions_without_a_price(self):
        self.assertIn("local", subscriptions.ALL_TIERS)
        self.assertFalse([r for r in subscriptions.DEFAULT_OPTIONS if r[1] == "local"])

    def test_chat_request_accepts_the_local_key(self):
        from cortex_rental.schemas.chat_schemas import SendMessageRequest

        self.assertIn("local", SendMessageRequest.model_fields["model_tier"].annotation.__args__[0].__args__)


class FakeRunner(BaseHTTPRequestHandler):
    seen = {}
    reply = {}

    def do_POST(self):
        FakeRunner.seen = {
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "body": json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
        }
        data = json.dumps(FakeRunner.reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestLocalProviderExchange(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), FakeRunner)
        threading.Thread(target=self.server.handle_request, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}/engines/v1"

    def tearDown(self):
        self.server.server_close()

    def test_request_shape_and_thought_markers_removed(self):
        FakeRunner.reply = {
            "choices": [
                {"message": {"role": "assistant", "content": "<|channel>thought\nje réfléchis<channel|>Bonjour !"}}
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 4},
        }
        provider = provider_for("ai/gemma4", "", max_output_tokens=256, temperature=0.2)
        tools = [{"name": "list_rentals", "description": "d", "parameters": {"type": "object", "properties": {}}}]
        with mock.patch.object(LocalOpenAIProvider, "base_url", classmethod(lambda cls: self.base)):
            result = provider.generate("Tu es utile.", [provider.user_message("Salut")], tools)
        self.assertEqual(FakeRunner.seen["path"], "/engines/v1/chat/completions")
        self.assertIsNone(FakeRunner.seen["auth"])  # aucune clé envoyée
        body = FakeRunner.seen["body"]
        self.assertEqual(body["model"], "ai/gemma4")
        self.assertNotIn("reasoning_effort", body)
        self.assertEqual(body["max_tokens"], 256)
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(body["tools"][0]["function"]["name"], "list_rentals")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "Tu es utile."})
        self.assertEqual(result.text, "Bonjour !")  # jamais la réflexion brute du modèle
        self.assertEqual((result.input_tokens, result.output_tokens), (11, 4))

    def test_tool_calls_are_parsed(self):
        FakeRunner.reply = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "list_rentals", "arguments": '{"state":"Quote"}'},
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }
        provider = provider_for("ai/gemma4", "")
        with mock.patch.object(LocalOpenAIProvider, "base_url", classmethod(lambda cls: self.base)):
            result = provider.generate("s", [provider.user_message("q")], [])
        self.assertEqual([(c.name, c.args) for c in result.tool_calls], [("list_rentals", {"state": "Quote"})])

    def test_without_an_address_the_error_says_what_to_set(self):
        provider = provider_for("ai/gemma4", "")
        with mock.patch.object(LocalOpenAIProvider, "base_url", classmethod(lambda cls: "")):
            with self.assertRaises(AIConfigurationError) as ctx:
                provider.generate("s", [provider.user_message("q")], [])
        self.assertIn("cortex_ai_local_base_url", str(ctx.exception))


class TestLocalRunnerRestart(unittest.TestCase):
    """Le moteur local qui plante tout de suite (5xx rapide) est relancé UNE fois; un délai dépassé ne l'est jamais."""

    def provider(self):
        return LocalOpenAIProvider("ai/gemma4", timeout=30)

    def test_fast_server_error_is_retried_once(self):
        from cortex_rental.services.ai.providers import AIProviderError

        ok = mock.Mock()
        calls = [AIProviderError("indisponible", status=503, retryable=True), ok]

        def fake(self_, *a, **k):
            r = calls.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        with mock.patch.object(OpenAIProvider, "generate", fake), mock.patch("time.sleep") as nap:
            self.assertIs(self.provider().generate("", [], []), ok)
        self.assertEqual(calls, [])
        nap.assert_called_once()

    def test_second_failure_is_raised_and_a_timeout_is_not_retried(self):
        from cortex_rental.services.ai.providers import AIProviderError

        count = {"n": 0}

        def boom(self_, *a, **k):
            count["n"] += 1
            raise AIProviderError("indisponible", status=503, retryable=True)

        with mock.patch.object(OpenAIProvider, "generate", boom), mock.patch("time.sleep"):
            with self.assertRaises(AIProviderError):
                self.provider().generate("", [], [])
        self.assertEqual(count["n"], 2)

        count["n"] = 0

        def slow(self_, *a, **k):
            count["n"] += 1
            raise AIProviderError("trop long", retryable=False)

        with mock.patch.object(OpenAIProvider, "generate", slow):
            with self.assertRaises(AIProviderError):
                self.provider().generate("", [], [])
        self.assertEqual(count["n"], 1)


if __name__ == "__main__":
    unittest.main()
