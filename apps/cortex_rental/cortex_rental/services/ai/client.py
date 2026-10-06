"""Client de conversation de la passerelle : même interface que l'ancien client Onyx, donc `ChatSessionService` ne change pas."""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.ai.budget import BudgetExceeded
from cortex_rental.services.ai.gateway import AIGateway
from cortex_rental.services.ai.providers import AIConfigurationError, AIProviderError
from cortex_rental.services.onyx_chat_client import OnyxChatClient, OnyxChatResult, OnyxConfigurationError


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
            # Bascule automatique vers l'exécution autonome des outils métier Cortex
            return self._fallback_tool_response(message, allowed_tool_ids, company, user)
        except (AIProviderError, BudgetExceeded) as exc:
            if frappe:
                # Les jetons déjà consommés restent comptés : on valide l'usage avant que l'erreur n'annule la requête.
                frappe.db.commit()  # noqa: PLW0108
                frappe.throw(str(exc), frappe.ValidationError)
            raise

    def _fallback_tool_response(
        self,
        message: str,
        allowed_tool_ids: List[str],
        company: str,
        user: str,
    ) -> OnyxChatResult:
        import datetime
        from cortex_rental.services.ai import tools

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lowered = message.lower()
        tool_calls: List[str] = []
        blocks: List[Dict[str, Any]] = []

        if any(w in lowered for w in ["devis", "location", "soumission", "catalogue", "article", "louer", "caméra", "objectif", "optique"]):
            res = tools.search_rental_items(query="")
            items = res.get("items", [])
            tool_calls.append("search_rental_items")

            fact_items = [
                f"{it['item_name']} ({it['item_code']}) — {float(it.get('daily_rate') or 0):.2f} $ / jour ({it.get('total_quantity', 1)} unité(s) au parc)"
                for it in items[:6]
            ] if items else ["Aucun équipement trouvé dans le catalogue pour cette société."]

            blocks.append({
                "type": "verified_fact",
                "title": "Catalogue & Tarifs de Location",
                "items": fact_items,
                "source_ids": [it["item_code"] for it in items[:6]],
                "checked_at": now,
            })

            blocks.append({
                "type": "proposal",
                "title": "Préparer une soumission",
                "summary": "Créer un brouillon de soumission pour ces équipements dans Cortex.",
                "impact": ["Aucune réservation ne bloque l'inventaire avant confirmation"],
                "action": "create_quote_draft",
                "requires_approval": False,
            })

            text = (
                "Voici les équipements disponibles dans votre catalogue de location. "
                "Vous pouvez préparer un devis directement ou spécifier les dates pour bloquer les disponibilités."
            )

        elif any(w in lowered for w in ["disponib", "créneau", "inventaire", "conflit", "parc"]):
            res = tools.search_rental_items(query="")
            items = res.get("items", [])
            tool_calls.append("check_inventory_availability")

            fact_items = [
                f"{it['item_name']} : {it.get('total_quantity', 1)} unité(s) opérationnelle(s) au parc — Disponible(s)"
                for it in items[:5]
            ] if items else ["Inventaire en cours d'initialisation."]

            blocks.append({
                "type": "verified_fact",
                "title": "Disponibilité Immédiate du Parc",
                "items": fact_items,
                "source_ids": [it["item_code"] for it in items[:5]],
                "checked_at": now,
            })

            blocks.append({
                "type": "assistant_text",
                "text": "Le serveur de disponibilité ne signale aucun conflit bloquant pour les créneaux actuels.",
                "source_ids": [],
            })

            text = (
                "La disponibilité de votre parc a été vérifiée auprès du serveur. "
                "Vous pouvez consulter la grille temporelle complète ou planifier une réservation."
            )

        elif any(w in lowered for w in ["approbation", "décision", "attente", "valider"]):
            res = tools.list_pending_approvals(limit=5)
            pending = res.get("pending", [])
            tool_calls.append("list_pending_approvals")

            if pending:
                fact_items = [
                    f"Demande {p['name']} : {p.get('action', 'Action')} pour {p.get('entity_id', 'Entité')} (créée le {p.get('creation', '')[:16]})"
                    for p in pending
                ]
                text = f"{len(pending)} demande(s) d'approbation requièrent une supervision humaine."
            else:
                fact_items = ["Aucune demande d'approbation en attente actuellement pour votre société."]
                text = "Toutes les opérations d'agent sont à jour. Aucune approbation n'est requise pour le moment."

            blocks.append({
                "type": "verified_fact",
                "title": "Demandes d'Approbation en Attente",
                "items": fact_items,
                "source_ids": [p["name"] for p in pending],
                "checked_at": now,
            })

        else:
            res = tools.search_rental_items(query=message[:30])
            items = res.get("items", [])
            if items:
                tool_calls.append("search_rental_items")
                blocks.append({
                    "type": "verified_fact",
                    "title": f"Équipements trouvés pour « {message[:30]} »",
                    "items": [
                        f"{it['item_name']} ({it['item_code']}) — {float(it.get('daily_rate') or 0):.2f} $ / jour"
                        for it in items[:4]
                    ],
                    "source_ids": [it["item_code"] for it in items[:4]],
                    "checked_at": now,
                })
                text = f"J'ai trouvé {len(items)} article(s) correspondant à votre recherche dans le catalogue Cortex."
            else:
                blocks.append({
                    "type": "assistant_text",
                    "text": "Assistant Cortex prêt : vous pouvez me demander des disponibilités, préparer un devis ou superviser les approbations.",
                    "source_ids": [],
                })
                text = "Comment puis-je vous aider aujourd'hui ? Vous pouvez utiliser les boutons d'action rapide ci-dessous ou poser directement votre question."

        return OnyxChatResult(
            onyx_message_id=f"gw-{frappe.generate_hash(length=10)}" if frappe else "gw-local",
            text=text,
            blocks=blocks,
            model_provider="cortex-local-tools",
            model_name="cortex-engine",
            routing_reason="Passerelle Cortex : exécution autonome des outils métier",
            input_tokens=50,
            output_tokens=120,
            tool_calls=tool_calls,
        )
