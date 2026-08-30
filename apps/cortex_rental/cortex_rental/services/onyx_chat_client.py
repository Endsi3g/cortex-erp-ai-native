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
