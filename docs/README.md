# Cortex — ERP AI-Native de Location d'Équipement (Documentation)

Bienvenue dans la documentation d'ingénierie et d'architecture de **Cortex**, l'ERP de location d'équipement conçu selon le paradigme **AI-Native First**.

Le projet repose sur le socle **Frappe Framework / ERPNext (v15+)**, l'application métier propriétaire `cortex_rental`, la base de données relationnelle **MariaDB 10.11+**, la plateforme d'agents **Onyx**, orchestrés via une passerelle privée **Python FastMCP**, un **Routeur Multi-Modèles (Gemini 3.7 Flash & Claude 3.7 Sonnet)** et une interface opérateur Desk + **Frappe UI (Vue 3)**.

---

## 📚 Sommaire de la Documentation

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
