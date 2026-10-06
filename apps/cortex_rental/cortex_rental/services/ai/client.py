"""Client de conversation de la passerelle : même interface que l'ancien client Onyx, donc `ChatSessionService` ne change pas."""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.ai.budget import BudgetExceeded
from cortex_rental.services.ai.gateway import AIGateway
from cortex_rental.services.ai.providers import AIConfigurationError, AIProviderError
from cortex_rental.services.onyx_chat_client import OnyxChatClient, OnyxChatResult


class GatewayChatClient(OnyxChatClient):
    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or AIGateway()

    def send_message(
        self,
        message: str,
        chat_session_id: Optional[str],
        persona_id: str,
        allowed_tool_ids: List[str],
        context: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> OnyxChatResult:
        from cortex_rental.permissions.agent_scopes import get_company_context

        company = get_company_context()
        user = frappe.session.user if frappe else "Administrator"

        try:
            outcome = self.gateway.run(
                message=message,
                history=history,
                allowed_tools=allowed_tool_ids,
                company=company,
                user=user,
                page=str(context.get("page") or ""),
                request_id=str(context.get("request_id") or ""),
                tier=str(context.get("model_tier") or "") or None,
            )
            return OnyxChatResult(
                onyx_message_id=f"gw-{frappe.generate_hash(length=10)}" if frappe else "gw",
                text=outcome.text,
                blocks=outcome.blocks,
                model_provider=outcome.provider,
                model_name=outcome.model,
                routing_reason="Passerelle Cortex : outils sous les droits de la personne connectée",
                input_tokens=outcome.input_tokens,
                output_tokens=outcome.output_tokens,
                tool_calls=outcome.tool_calls,
            )
        except AIConfigurationError:
            # Aucune clé de modèle : mode démonstration honnête (vraies données, étiquette « démonstration »).
            return self._demo_response(message)
        except (AIProviderError, BudgetExceeded) as exc:
            if frappe:
                # Les jetons déjà consommés restent comptés : on valide l'usage avant que l'erreur n'annule la requête.
                frappe.db.commit()  # noqa: PLW0108
                frappe.throw(str(exc), frappe.ValidationError)
            raise

    def _demo_response(self, message: str) -> OnyxChatResult:
        from cortex_rental.services.ai import demo

        outcome = demo.answer(message)
        return OnyxChatResult(
            onyx_message_id=f"demo-{frappe.generate_hash(length=10)}" if frappe else "demo",
            text=outcome["text"],
            blocks=outcome["blocks"],
            model_provider=demo.PROVIDER,
            model_name=demo.MODEL,
            routing_reason="Mode démonstration : aucun modèle d'IA configuré",
            input_tokens=0,
            output_tokens=0,
            tool_calls=outcome["tool_calls"],
        )
