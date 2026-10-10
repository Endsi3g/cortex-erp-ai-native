"""Passerelle IA : boucle « le modèle demande un outil → exécution sous les droits de la personne → réponse ».

Règles (voir docs/architecture/AI_ENGINE_DECISION.md) : aucun outil n'écrit ni n'approuve ; chaque appel est compté
(jetons, coût) et refusé au plafond du mois ; aucune clé n'atteint le navigateur ; en cas de panne, le message est clair
et rien n'est présenté comme réussi.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.services.ai import budget, settings as ai_settings, tools
from cortex_rental.services.ai.providers import (
    AIConfigurationError,
    AIProviderError,
    LLMProvider,
    ProviderResult,
    provider_for,
)

SYSTEM_PROMPT = """Tu es l'assistant Cortex d'une société de location de matériel au Québec.
Tu écris en français du Québec, avec calme, clarté et concision, sans jargon ni exagération. Tu vouvoies la personne.
Règles :
- Pour toute quantité, tout prix, toute disponibilité ou tout statut, tu utilises les outils. Tu ne devines jamais : si l'outil ne donne pas l'information, dis-le.
- Tu ne peux ni confirmer, ni approuver, ni modifier quoi que ce soit toi-même. Tu proposes avec les outils « propose_… » (jamais de formulation « c'est fait » avant l'approbation de la personne); elle voit un aperçu et décide. Chaque proposition porte une raison (« reason ») claire et honnête. Un contrat exige l'approbation d'un humain.
- Pour retrouver un enregistrement (client, équipement, location, facture…), utilise find_records puis get_record. Pour modifier une seule valeur, utilise propose_update_field avec l'identifiant exact : la carte montre l'avant et l'après, et la personne peut annuler après coup. Tu ne modifies ni statut ni montant calculé. La structure (nouvelle catégorie, nouveau champ) passe seulement par propose_add_category et propose_add_custom_field, réservés au propriétaire.
- Si une information manque (client, dates, équipement), pose une seule question courte.
- Les cartes (aperçus, graphiques, vérifications) s'affichent SOUS ton message : écris « ci-dessous », jamais « ci-dessus ». Ne répète pas dans ton texte les chiffres déjà présents dans une carte.
- Les montants sont en dollars canadiens, taxes TPS/TVQ précisées quand elles sont données par l'outil.
- N'invente jamais de numéro de location, de facture ou de client.
Société : {company}. Date du jour : {today}. Écran actuel : {page}.
{rules}"""


def company_rules(company: str) -> str:
    """Les règles de la société que l'assistant doit connaître (taxes, acompte, retenue, approbation), lues dans ses
    réglages. Lecture seule : l'assistant ne les modifie pas et ne remplace pas les outils pour un prix ou un statut.
    Vide si rien n'est lisible (jamais de règle inventée)."""
    if not frappe or not company:
        return ""
    try:
        row = frappe.db.get_value(
            "Cortex Finance Settings",
            company,
            [
                "apply_taxes",
                "tps_rate",
                "tvq_rate",
                "deposit_percent",
                "quote_hold_enabled",
                "quote_hold_hours",
                "allow_sole_approver_self_approval",
            ],
            as_dict=True,
        )
    except Exception:
        return ""
    if not row:
        return ""
    lines = ["Règles de la société (réglages, à citer telles quelles; les prix et les statuts viennent des outils) :"]
    if row.get("apply_taxes"):
        lines.append(f"- Taxes : TPS {row['tps_rate']} %, TVQ {row['tvq_rate']} %.")
    else:
        lines.append("- Les taxes ne sont pas appliquées par cette société.")
    lines.append(f"- Acompte : {row['deposit_percent']} % à la réservation.")
    if row.get("quote_hold_enabled"):
        lines.append(f"- Un devis retient le matériel {row['quote_hold_hours']} h; la retenue n'est pas une garantie.")
    lines.append(
        "- Un contrat est toujours approuvé par une personne; "
        + (
            "le seul approbateur de la société peut décider de sa propre demande."
            if row.get("allow_sole_approver_self_approval")
            else "personne ne décide de sa propre demande."
        )
    )
    return "\n".join(lines) + "\n"


# Libellés lisibles des outils consultés (affichés après coup : seulement ce qui a vraiment été appelé).
TOOL_LABELS = {
    "search_rental_items": "Recherche dans le catalogue",
    "check_inventory_availability": "Vérification de la disponibilité",
    "search_customers": "Recherche de clients",
    "list_rentals": "Consultation des locations",
    "list_pending_approvals": "Consultation des approbations",
    "finance_summary": "Résumé financier",
    "finance_trend": "Évolution du facturé",
    "list_invoices": "Consultation des factures",
    "rentals_by_state": "Locations par état",
    "customer_summary": "Résumé du client",
    "late_returns": "Recherche des retours en retard",
    "find_records": "Recherche d'enregistrements",
    "get_record": "Lecture d'un enregistrement",
    "create_quote_draft": "Calcul du devis proposé",
    "propose_create_customer": "Préparation de la création du client",
    "propose_create_quote": "Préparation du devis",
    "propose_release_hold": "Préparation de la libération de la retenue",
    "propose_renew_hold": "Préparation du renouvellement de la retenue",
    "propose_request_reservation": "Préparation de la réservation",
    "propose_record_payment": "Préparation du paiement",
    "propose_decide_approval": "Préparation de la décision",
    "propose_update_field": "Préparation de la modification",
    "propose_apply_sector_template": "Préparation du modèle de secteur",
    "propose_add_category": "Préparation de la catégorie",
    "propose_add_custom_field": "Préparation du champ",
}


def tool_progress_blocks(names: List[str]) -> List[Dict[str, Any]]:
    seen, blocks = set(), []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        blocks.append(
            {"type": "tool_progress", "tool_name": TOOL_LABELS.get(name, name), "state": "success", "message": ""}
        )
    return blocks


EMPTY_ANSWER = "Je n'ai pas pu formuler de réponse. Reformulez votre demande ou précisez l'équipement et les dates."
STEPS_EXHAUSTED = "Je n'ai pas pu terminer la vérification en un nombre raisonnable d'étapes. Précisez votre demande."


@dataclass
class GatewayResult:
    text: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[str] = field(default_factory=list)
    model: str = ""
    provider: str = ""


def build_provider(settings: Dict[str, Any], model: Optional[str] = None) -> LLMProvider:
    if not settings.get("enabled"):
        raise AIConfigurationError("L'assistant IA est désactivé dans les réglages.")
    chosen = (model or settings["model"]).strip()
    api_key = ai_settings.provider_key_for(chosen, settings)
    if not api_key:
        raise AIConfigurationError(
            "L'assistant IA n'est pas encore configuré : un administrateur doit saisir la clé API dans les réglages de l'IA."
        )
    return provider_for(
        chosen,
        api_key,
        timeout=settings.get("timeout_seconds"),
        temperature=float(settings.get("temperature") or 0.2),
        max_output_tokens=int(settings.get("max_output_tokens") or 1024),
    )


class TierUnavailable(AIProviderError):
    """Le niveau demandé n'est pas offert (désactivé ou sans clé) alors que d'autres le sont : on le dit, on ne change pas en silence."""


def resolve_tier(settings: Dict[str, Any], requested: Optional[str], company: Optional[str] = None) -> Dict[str, Any]:
    """Le niveau Cortex à utiliser. Sans demande : le niveau par défaut. Aucun niveau disponible : IA non configurée (démo)."""
    rows = {r["key"]: r for r in ai_settings.tiers(settings)}
    available = [r for r in rows.values() if r["configured"]]
    if not available:
        raise AIConfigurationError(
            "L'assistant IA n'est pas encore configuré : un administrateur doit saisir la clé API dans les réglages de l'IA."
        )
    key = requested or ai_settings.default_tier(settings)
    row = rows.get(key)
    if company and row and row["configured"]:
        # Abonnement : seuls les niveaux acquis sont offerts (sans effet tant que la facturation n'est pas activée).
        from cortex_rental.services import subscriptions

        if not subscriptions.allows_tier(company, key):
            raise TierUnavailable(
                f"Le modèle « {row['label']} » n'est pas inclus dans l'abonnement de votre société. "
                "Le propriétaire peut l'ajouter dans Société et rôles."
            )
    if not row or not row["configured"]:
        raise TierUnavailable(
            f"Le modèle « {row['label'] if row else key} » n'est pas disponible pour le moment. Choisissez-en un autre."
        )
    return row


def _fact(name: str, output: Dict[str, Any], now: str) -> Optional[Dict[str, Any]]:
    if output.get("error"):
        return None
    if name == "check_inventory_availability":
        from cortex_rental.services.ai.stats import fr_number

        items = [
            f"{r.get('item_id')} : {fr_number(r.get('available_quantity'))} libre(s) sur "
            f"{fr_number(r.get('total_fleet_quantity'))} ({'disponible' if r.get('is_available') else 'insuffisant'})"
            for r in output.get("results", [])
        ]
        return {
            "type": "verified_fact",
            "title": "Disponibilité vérifiée",
            "items": items,
            "source_ids": [],
            "checked_at": now,
        }
    if name == "finance_summary" and not output.get("stat_block"):
        # Repli sans carte de statistiques (l'outil la fournit normalement) : le même contenu, en liste vérifiée.
        items = [
            f"Facturé : {output['facture']:.2f} $ · Encaissé : {output['encaisse']:.2f} $",
            f"Solde à recevoir : {output['solde_a_recevoir']:.2f} $ ({output['factures_ouvertes']} facture(s))",
            f"Factures en retard : {output['factures_en_retard']}",
        ]
        return {
            "type": "verified_fact",
            "title": f"Finance — {output['mois']}",
            "items": items,
            "source_ids": [],
            "checked_at": now,
        }
    return None


def _proposal(output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = output.get("proposal")
    if not data:
        return None
    impact = [f"{l['item']} × {l['quantity']:g} — {l['amount']:.2f} $" for l in data["lines"]]
    impact.append(f"Sous-total {data['subtotal']:.2f} $ · TPS {data['tps']:.2f} $ · TVQ {data['tvq']:.2f} $")
    impact.append("Rien n'est créé tant que vous ne confirmez pas.")
    return {
        "type": "proposal",
        "title": f"Devis proposé — {data['customer']}",
        "summary": f"{data['starts_at'][:16]} → {data['ends_at'][:16]} · total {data['total']:.2f} $ (taxes incluses)",
        "impact": impact,
        "action": "open_quote_composer",
        "requires_approval": False,
    }


class AIGateway:
    def __init__(self, provider: Optional[LLMProvider] = None, settings: Optional[Dict[str, Any]] = None):
        self.settings = settings if settings is not None else ai_settings.load()
        self._provider = provider
        self.tier: Dict[str, Any] = {}

    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = build_provider(self.settings)
        return self._provider

    def _generate(self, system: str, messages: List[Any], declarations: List[Dict[str, Any]]) -> ProviderResult:
        """Un appel au modèle ; si le modèle principal n'existe pas chez le fournisseur, on essaie le modèle de repli."""
        provider = self.provider()
        try:
            return provider.generate(system, messages, declarations)
        except AIProviderError as exc:
            fallback = (self.settings.get("fallback_model") or "").strip()
            if exc.status == 404 and fallback and fallback != provider.model:
                self._provider = build_provider(self.settings, model=fallback)
                return self._provider.generate(system, messages, declarations)
            raise

    def run(
        self,
        message: str,
        history: Optional[List[Dict[str, Any]]],
        allowed_tools: List[str],
        company: str,
        user: str,
        page: str = "",
        request_id: str = "",
        tier: Optional[str] = None,
    ) -> GatewayResult:
        budget.check(company, self.settings)
        # Plafond mensuel atteint : on continue avec le modèle économique et on le dit à la personne.
        economy = bool(budget.status(company, self.settings).get("economy"))
        prices = None
        if self._provider is None and not economy:
            # Niveau Cortex choisi : son modèle et ses prix (le budget compte le vrai coût du niveau utilisé).
            self.tier = resolve_tier(self.settings, tier, company)
            self._provider = build_provider(self.settings, model=self.tier["model"])
            prices = {
                "price_input_per_mtok": self.tier["price_input_per_mtok"],
                "price_output_per_mtok": self.tier["price_output_per_mtok"],
            }
        if economy:
            self._provider = build_provider(self.settings, model=self.settings["economy_model"].strip())
            prices = {
                "price_input_per_mtok": self.settings.get("economy_price_input_per_mtok"),
                "price_output_per_mtok": self.settings.get("economy_price_output_per_mtok"),
            }
        provider = self.provider()
        exposed = tools.exposed(allowed_tools)
        exposed_names = {t.name for t in exposed}
        declarations = [t.declaration() for t in exposed]
        system = SYSTEM_PROMPT.format(
            company=company,
            today=frappe.utils.today() if frappe else "",
            page=page or "tableau de bord",
            rules=company_rules(company),
        )
        messages: List[Any] = [
            provider.history_message(h["role"], h["text"]) for h in (history or [])[-10:] if h.get("text")
        ]
        messages.append(provider.user_message(message))
        max_steps = max(1, min(int(self.settings.get("max_tool_steps") or 5), 8))
        now = str(frappe.utils.now_datetime()) if frappe else ""
        result_blocks: List[Dict[str, Any]] = []
        used_tools: List[str] = []
        consulted: List[str] = []
        tools.CONSULTED.set(consulted)  # lu par les outils « propose_* » pour « Pourquoi cette proposition »
        total_in = total_out = 0
        text = ""
        for step in range(max_steps + 1):
            result = self._generate(system, messages, declarations if step < max_steps else [])
            total_in += result.input_tokens
            total_out += result.output_tokens
            budget.record(
                company,
                user,
                self.provider().name,
                self.provider().model,
                result.input_tokens,
                result.output_tokens,
                self.settings,
                request_id=request_id,
                tool_calls=len(result.tool_calls),
                prices=prices,
            )
            if result.tool_calls and step < max_steps:
                messages.append(self.provider().assistant_message(result))
                outputs = []
                for call in result.tool_calls[:4]:
                    if call.name not in exposed_names:
                        output = {"error": "Cet outil n'est pas autorisé pour cet assistant."}
                    else:
                        output = tools.execute(call.name, call.args)
                        used_tools.append(call.name)
                        if call.name not in tools.PROPOSING_TOOLS:
                            consulted.append(TOOL_LABELS.get(call.name, call.name))
                        self._audit(company, call.name)
                        fact, proposal = _fact(call.name, output, now), _proposal(output)
                        if fact:
                            result_blocks.append(fact)
                        if proposal:
                            result_blocks.append(proposal)
                        if output.get("action_block"):
                            result_blocks.append(output["action_block"])
                        if output.get("stat_block"):
                            result_blocks.append(output["stat_block"])
                    outputs.append({"name": call.name, "id": call.id, "result": output})
                tool_message = self.provider().tool_results_message(outputs)
                # Certains fournisseurs (OpenAI) veulent un message par résultat d'outil.
                if isinstance(tool_message, list):
                    messages.extend(tool_message)
                else:
                    messages.append(tool_message)
                continue
            text = result.text or (STEPS_EXHAUSTED if result.tool_calls else "")
            break
        text = text or EMPTY_ANSWER
        status = budget.status(company, self.settings)
        blocks = (
            tool_progress_blocks(used_tools)
            + [{"type": "assistant_text", "text": text, "source_ids": []}]
            + result_blocks
        )
        if economy:
            blocks.append(
                {
                    "type": "risk",
                    "severity": "warning",
                    "title": "Plafond d'intelligence artificielle atteint",
                    "explanation": (
                        "Votre société a atteint son plafond mensuel d'IA : l'assistant répond maintenant avec un modèle "
                        "plus économique, un peu moins puissant. Le plafond se renouvelle au début du mois; un "
                        "administrateur peut aussi l'ajuster."
                    ),
                    "source_ids": [],
                }
            )
        elif status["warning"]:
            blocks.append(
                {
                    "type": "risk",
                    "severity": "warning",
                    "title": "Budget de l'assistant presque atteint",
                    "explanation": f"{status['percent']:.0f} % du budget mensuel de votre société est utilisé.",
                    "source_ids": [],
                }
            )
        return GatewayResult(
            text=text,
            blocks=blocks,
            input_tokens=total_in,
            output_tokens=total_out,
            tool_calls=used_tools,
            model=self.provider().model,
            provider=self.provider().name,
        )

    @staticmethod
    def _audit(company: str, tool_name: str) -> None:
        try:
            from cortex_rental.services.audit import AuditService

            AuditService.record_read(action="cortex.assistant.tool_used", metadata={"tool": tool_name}, company=company)
        except Exception:
            pass
