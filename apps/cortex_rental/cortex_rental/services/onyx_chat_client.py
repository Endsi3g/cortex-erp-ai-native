"""
OnyxChatClient: the one seam between Cortex and a real Onyx deployment.
No real Onyx backend is connected in this pass (see HANDOFF.md) —
`MockOnyxChatClient` is the only implementation, deliberately built so
swapping in a real HTTP-calling client later means implementing this
same interface, not rewriting the gateway that calls it.

MockOnyxChatClient's responses are keyword-driven and deterministic
(not random) so tests are reproducible — it does not call any real
model. It never fabricates a real system state (e.g. it never claims a
specific quantity is available); its "verified_fact" blocks are
explicitly synthetic and labeled as coming from the mock, not from a
live AvailabilityService call, because none was actually made.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


@dataclass
class OnyxChatResult:
    onyx_message_id: str
    text: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    model_provider: str = "mock"
    model_name: str = "mock-onyx-client"
    routing_reason: str = "MockOnyxChatClient — no real Onyx backend connected in this pass."
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[str] = field(default_factory=list)
    onyx_session_id: Optional[str] = None


class OnyxConfigurationError(RuntimeError):
    """Onyx is selected but has no usable server-side configuration."""


class OnyxChatClient(ABC):
    @abstractmethod
    def send_message(
        self,
        message: str,
        chat_session_id: Optional[str],
        persona_id: str,
        allowed_tool_ids: List[str],
        context: Dict[str, Any],
    ) -> OnyxChatResult:
        raise NotImplementedError


class MockOnyxChatClient(OnyxChatClient):
    def send_message(
        self,
        message: str,
        chat_session_id: Optional[str],
        persona_id: str,
        allowed_tool_ids: List[str],
        context: Dict[str, Any],
    ) -> OnyxChatResult:
        lowered = message.lower()
        mock_id = f"mock-onyx-{abs(hash((message, persona_id))) % 10_000_000}"

        if not allowed_tool_ids:
            return OnyxChatResult(
                onyx_message_id=mock_id,
                text="Cet agent n'a accès à aucun outil pour cette action.",
                blocks=[
                    {
                        "type": "missing_information",
                        "fields": ["outil autorisé pour cet agent"],
                        "suggested_next_action": (
                            "Aucun outil MCP en lecture seule n'existe encore pour cet agent "
                            "(voir services/tool_policy.py) — gap connu, pas une erreur de routage."
                        ),
                    }
                ],
            )

        if "conflit" in lowered or "conflict" in lowered:
            return OnyxChatResult(
                onyx_message_id=mock_id,
                text="Conflit potentiel détecté (réponse simulée — aucun appel réel à AvailabilityService).",
                blocks=[
                    {
                        "type": "risk",
                        "severity": "warning",
                        "title": "Conflit de disponibilité (simulé)",
                        "explanation": (
                            "MockOnyxChatClient : ceci est une réponse simulée, pas une lecture réelle "
                            "de Cortex Rental Transaction."
                        ),
                        "source_ids": [],
                    }
                ],
                tool_calls=["check_inventory_availability"]
                if "check_inventory_availability" in allowed_tool_ids
                else [],
            )

        if "disponib" in lowered or "availab" in lowered:
            return OnyxChatResult(
                onyx_message_id=mock_id,
                text="Vérification simulée de la disponibilité.",
                blocks=[
                    {
                        "type": "verified_fact",
                        "title": "Disponibilité (réponse simulée — MockOnyxChatClient)",
                        "items": ["Aucun appel réel à AvailabilityService n'a été fait dans ce mock."],
                        "source_ids": [],
                        "checked_at": "mock",
                    },
                    {
                        "type": "proposal",
                        "title": "Préparer une soumission",
                        "summary": "Créer un brouillon de soumission à partir de cette conversation.",
                        "impact": ["Aucune réservation ne serait créée", "Simulation uniquement dans ce pass"],
                        "action": "create_quote_draft",
                        "requires_approval": False,
                    },
                ],
                tool_calls=["check_inventory_availability"]
                if "check_inventory_availability" in allowed_tool_ids
                else [],
            )

        return OnyxChatResult(
            onyx_message_id=mock_id,
            text="Réponse simulée générique (MockOnyxChatClient — aucun Onyx réel connecté).",
            blocks=[
                {
                    "type": "missing_information",
                    "fields": [],
                    "suggested_next_action": (
                        "Reformulez avec un mot-clé lié à la disponibilité ou à un conflit pour "
                        "voir un exemple de bloc plus riche dans ce mock."
                    ),
                }
            ],
        )


class HttpOnyxChatClient(OnyxChatClient):
    """Server-side adapter for Onyx's non-streaming chat API.

    All credentials, persona IDs and Onyx tool IDs come from trusted
    Frappe site configuration. Cortex tool names are mapped to Onyx's
    numeric tool IDs and intersected with the server-side policy before
    they are sent upstream. An empty mapping grants no tools.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 90):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = max(10, min(int(timeout), 180))

    @staticmethod
    def _config() -> Dict[str, Any]:
        if not frappe or not getattr(frappe, "conf", None):
            return {}
        conf = frappe.conf
        return {
            "base_url": conf.get("onyx_base_url"),
            "api_key": conf.get("onyx_api_key"),
            "timeout": conf.get("onyx_timeout_seconds", 90),
            "persona_ids": conf.get("onyx_persona_ids", {}),
            "tool_id_map": conf.get("onyx_tool_id_map", {}),
            "model_name": conf.get("onyx_model_name"),
        }

    @classmethod
    def from_site_config(cls) -> "HttpOnyxChatClient":
        config = cls._config()
        base_url = config.get("base_url")
        api_key = config.get("api_key")
        if not base_url or not api_key:
            raise OnyxConfigurationError(
                "Onyx is not configured. Set onyx_base_url and onyx_api_key in Frappe site configuration."
            )
        if not str(base_url).startswith(("http://", "https://")):
            raise OnyxConfigurationError("onyx_base_url must use HTTP or HTTPS.")
        return cls(str(base_url), str(api_key), config.get("timeout", 90))

    def send_message(
        self,
        message: str,
        chat_session_id: Optional[str],
        persona_id: str,
        allowed_tool_ids: List[str],
        context: Dict[str, Any],
    ) -> OnyxChatResult:
        config = self._config()
        persona_map = config.get("persona_ids") or {}
        tool_map = config.get("tool_id_map") or {}
        try:
            upstream_persona = int(persona_map.get(persona_id, 0))
        except (TypeError, ValueError):
            raise OnyxConfigurationError(f"Invalid Onyx persona ID for {persona_id}.")

        # Cortex policy contains semantic tool names; Onyx expects numeric
        # database IDs. Never pass a string name or broaden to all tools.
        upstream_tool_ids = []
        for tool_name in allowed_tool_ids:
            candidate = tool_map.get(tool_name)
            if candidate is None:
                continue
            try:
                upstream_tool_ids.append(int(candidate))
            except (TypeError, ValueError):
                raise OnyxConfigurationError(f"Invalid Onyx tool ID mapping for {tool_name}.")

        payload: Dict[str, Any] = {
            "message": message,
            "allowed_tool_ids": sorted(set(upstream_tool_ids)),
            "stream": False,
            "include_citations": True,
            "additional_context": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
        }
        if chat_session_id:
            payload["chat_session_id"] = chat_session_id
        else:
            payload["chat_session_info"] = {"persona_id": upstream_persona}

        request = urllib.request.Request(
            f"{self.base_url}/api/chat/send-chat-message",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Avoid returning arbitrary upstream HTML/body content (which may
            # include private details) to the user-facing error message.
            raise RuntimeError(f"Onyx returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Onyx could not complete the chat request.") from exc

        answer = result.get("answer_citationless") or result.get("answer")
        if result.get("error_msg"):
            raise RuntimeError("Onyx could not complete the chat request.")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Onyx returned an empty response.")

        citation_info = result.get("citation_info") or []
        source_ids = [
            str(citation.get("document_id"))
            for citation in citation_info
            if isinstance(citation, dict) and citation.get("document_id")
        ]
        tool_calls = [
            str(call.get("tool_name"))
            for call in (result.get("tool_calls") or [])
            if isinstance(call, dict) and call.get("tool_name")
        ]
        upstream_session = result.get("chat_session_id")
        return OnyxChatResult(
            onyx_message_id=str(result.get("message_id") or "onyx-response"),
            onyx_session_id=str(upstream_session) if upstream_session else None,
            text=answer.strip(),
            blocks=[{"type": "assistant_text", "text": answer.strip(), "source_ids": source_ids}],
            model_provider="Onyx",
            model_name=str(config.get("model_name") or "Configured Onyx model"),
            routing_reason="Server-side Onyx persona and tool policy",
            tool_calls=tool_calls,
        )
