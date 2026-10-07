# Cortex — Documentation

Documentation d'ingénierie et d'exploitation de **Cortex**, l'ERP de location d'équipement natif ERPNext (Frappe v15, application `cortex_rental`) assisté par IA. Le code et le [contrat de l'interface](frontend/CORTEX_UI_HANDOFF_V2.md) font foi : en cas de désaccord avec un document plus ancien, le plus récent l'emporte.

## Par où commencer

| Je veux… | Lire |
|---|---|
| Savoir ce qui est réellement construit (écrans, assistant IA, limites) | [`frontend/CORTEX_UI_HANDOFF_V2.md`](frontend/CORTEX_UI_HANDOFF_V2.md) — **document canonique** |
| Installer, mettre à jour, mettre en production, sauvegarder | [`ops/DEPLOIEMENT.md`](ops/DEPLOIEMENT.md), [`ops/COURRIEL_SES.md`](ops/COURRIEL_SES.md) |
| Comprendre une décision | [`adr/`](adr/) (système de référence, disponibilité, migration Frappe, facturation, passerelle IA, portail de devis, retenue par devis) |
| Connaître les coûts de l'IA, du courriel et des paiements | [`architecture/COUTS_API.md`](architecture/COUTS_API.md), [`architecture/AI_ENGINE_DECISION.md`](architecture/AI_ENGINE_DECISION.md) |
| Voir ce qui a été testé | [`audit/STRESS_TEST_2026-10-06.md`](audit/STRESS_TEST_2026-10-06.md), [`audit/AUDIT_SIMULATION_90_JOURS.md`](audit/AUDIT_SIMULATION_90_JOURS.md) |
| Voir les écrans | [`review/REVUE_ECRANS_2026-10-06.md`](review/REVUE_ECRANS_2026-10-06.md) et les captures de [`review/captures/`](review/captures/) |
| Voir l'historique | [`../CHANGELOG.md`](../CHANGELOG.md), [releases GitHub](https://github.com/Endsi3g/cortex-erp-ai-native/releases) |

## Documents d'architecture et de processus

Les documents numérotés ci-dessous décrivent l'architecture initiale (agents Onyx, façade FastMCP, routage de modèles). Depuis, l'interface est **100 % native ERPNext** (Vite, Frappe UI et l'application autonome ont été retirés) et l'assistant IA passe par une **passerelle interne** (`services/ai/`, ADR-006) avec les niveaux Cortex Rapide, Équilibré et Avancé. Les passages qui parlent de Vite, de Frappe UI ou de « Gemini 3.7 / Claude 3.7 » sont **historiques**.

### Sommaire (historique)

La documentation technique est structurée en 6 piliers :

### 1. [Principes d'Architecture AI-Native & Contrats Métier](01-ai-native-architecture.md)
*Ce document formalise les fondations théoriques et les invariants de sécurité.*
- **Les 7 Règles Non Négociables** : Ingestion structurée, source unique de vérité, sécurité dans le code, audit append-only, supervision humaine, multi-tenant strict, autonomie supervisée.
- **Règle des 3 Clients** : Interface Desk / Frappe UI, Agent Onyx via FastMCP, Intégrations API.
- **Journal d'Audit Append-Only** : Schéma strict de `Audit Event`, types d'acteurs et immutabilité totale (`before_save`, `on_trash`).
- **Politiques de Validation** : Exécution dans le code Python (`TransactionStateService`), jamais uniquement dans les prompts.

### 2. [Intégration Onyx, Façade FastMCP et APIs Métier Frappe](02-onyx-mcp-frappe-integration.md)
*Ce document détaille les protocoles techniques et le code d'interconnexion.*
- **Architecture de Communication** : Flux Onyx → FastMCP Python → Frappe REST API → MariaDB.
- **Passerelle FastMCP (`apps/cortex-mcp`)** : Outils agent-safe validés par Pydantic (`search_rental_items`, `check_inventory_availability`, `create_quote_draft`, `submit_approval_request`, `prepare_owner_statement`).
- **Isolation Multi-Tenant** : Header obligatoire `X-Company-ID` et validation de contexte côté serveur.
- **Barrière d'Approbation** : Interdiction absolue d'auto-approbation pour tout compte de service agent.

### 3. [Guide d'Implémentation Frappe Framework & ERPNext](07-frappe-erpnext-implementation-guide.md)
*Ce document fournit le guide technique pas à pas pour déployer et configurer le Bench Frappe et `cortex_rental`.*
- Initialisation du Frappe Bench & MariaDB 10.11+.
- Arborescence de l'application `cortex_rental`.
- Spécifications des DocTypes clés : `Cortex Rental Transaction`, `Consignment Owner`, `Consignment Payout`, `Approval Request`, `Audit Event`.
- Moteur tarifaire canonique (7 jours calendaires = 3 jours facturables).
- Suite de tests d'acceptation Python (`pytest`).

### 4. [Stratégie Multi-Modèles & Routage Intelligent (Gemini 3.7 & Sonnet 3.7)](04-model-routing-gemini-sonnet.md)
*Ce document formalise la synergie entre Gemini 3.7 Flash et Claude 3.7 Sonnet.*
- **Gemini 3.7 Flash (Moteur Opérationnel à Haut Débit)** : Intake omnicanal (courriels, PDF, photos), extraction structurée, vérifications de disponibilité en direct, génération de brouillons.
- **Claude 3.7 Sonnet (Expert d'Escalade & Ingénierie)** : Raisonnement cross-files sur le codebase, arbitrage d'exceptions métier complexes, conformité juridique des assurances, validation des audits.

### 5. [Workflow d'Ingénierie Multi-Modèles : Gemini → Claude](05-workflow-gemini-claude.md)
*Ce document formalise le workflow de développement obligatoire en 10 étapes.*
- Cycle en 10 étapes : Issue PRD → Branche → Ticket Gemini → Validation locale (`./bin/pre-claude-check.sh`) → Commit → Revue Claude → Arbitrage Humain → CI → Test UI → PR.

### 6. [Bibliothèque de Prompts Gemini & Claude](06-prompt-library-gemini-claude.md)
*Prompts standardisés pour les scénarios d'ingénierie, de refactorisation et d'arbitrage.*

### 7. Frontend & Design System
- **[Contrat UI AI-native v2](frontend/CORTEX_UI_HANDOFF_V2.md)** : source de référence pour tous les agents, shell ERPNext, Inbox, Workspace, Audit, confiance, validations et intégration Onyx/Ollama.
- **[Design System Global Cortex](design-system.md)** : Principes, tokens, typographie, élévation et composants réutilisables.
- **[Contrats des Composants](design-system-component-contracts.md)** : Spécifications et APIs des composants partagés Vue 3.
- **[Design System Accounting & P&L](design-system-accounting-pnl.md)** : Spécifications complètes de l'interface comptable, reporting financier, KPI, graphiques et hiérarchie de comptes.
