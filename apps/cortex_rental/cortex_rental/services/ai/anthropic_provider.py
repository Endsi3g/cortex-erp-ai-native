"""Anthropic Messages API client with streaming and tool use.

Plain HTTP (urllib) so the Frappe app needs no extra dependency. The
transport is injectable: tests feed recorded SSE lines, production opens
an HTTPS connection. The API key only ever comes from site_config
(`anthropic_api_key`); it is never sent to the browser.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 120


class AnthropicError(RuntimeError):
    """The API refused or failed; the message is safe to show."""


@dataclass
class ModelTurn:
    """One assistant message: its content blocks as the API returned them."""

    content: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")

    @property
    def tool_uses(self) -> List[Dict[str, Any]]:
        return [b for b in self.content if b.get("type") == "tool_use"]


Transport = Callable[[Dict[str, Any], Dict[str, str]], Iterable[bytes]]


def http_transport(body: Dict[str, Any], headers: Dict[str, str]) -> Iterable[bytes]:
    request = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        response = urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            pass
        raise AnthropicError(f"Anthropic a refusé la requête ({exc.code}). {detail}".strip()) from exc
    except urllib.error.URLError as exc:
        raise AnthropicError("Impossible de joindre l’API Anthropic.") from exc
    with response:
        for line in response:
            yield line


def parse_sse(lines: Iterable[bytes]) -> Iterable[Dict[str, Any]]:
    """Server-sent events → decoded JSON `data` payloads."""
    for raw in lines:
        line = raw.decode("utf-8").rstrip("\r\n") if isinstance(raw, bytes) else raw.rstrip("\r\n")
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                yield json.loads(payload)


class AnthropicProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, transport: Optional[Transport] = None):
        if not api_key:
            raise AnthropicError("Clé API Anthropic absente : définir anthropic_api_key dans site_config.")
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.transport = transport or http_transport

    def stream_turn(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        on_text: Optional[Callable[[str], None]] = None,
    ) -> ModelTurn:
        """Run one model call, streaming text deltas to `on_text`; returns the full assistant turn."""
        body = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
        }
        turn = ModelTurn()
        partial_json: Dict[int, str] = {}
        for event in parse_sse(self.transport(body, headers)):
            kind = event.get("type")
            if kind == "message_start":
                turn.input_tokens = int(event.get("message", {}).get("usage", {}).get("input_tokens") or 0)
            elif kind == "content_block_start":
                block = dict(event["content_block"])
                if block.get("type") == "tool_use":
                    block["input"] = {}
                    partial_json[event["index"]] = ""
                turn.content.append(block)
            elif kind == "content_block_delta":
                delta = event["delta"]
                block = turn.content[event["index"]]
                if delta.get("type") == "text_delta":
                    block["text"] = block.get("text", "") + delta["text"]
                    if on_text:
                        on_text(delta["text"])
                elif delta.get("type") == "input_json_delta":
                    partial_json[event["index"]] += delta.get("partial_json", "")
            elif kind == "content_block_stop":
                index = event["index"]
                if index in partial_json:
                    raw = partial_json.pop(index)
                    try:
                        turn.content[index]["input"] = json.loads(raw) if raw else {}
                    except json.JSONDecodeError:
                        turn.content[index]["input"] = {"_invalid_json": raw}
            elif kind == "message_delta":
                turn.stop_reason = event.get("delta", {}).get("stop_reason") or turn.stop_reason
                turn.output_tokens = int(event.get("usage", {}).get("output_tokens") or turn.output_tokens)
            elif kind == "error":
                raise AnthropicError(event.get("error", {}).get("message") or "Erreur du modèle.")
        return turn
