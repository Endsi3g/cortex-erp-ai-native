# ADR-001 : Laravel & PostgreSQL comme Système d'Enregistrement Unique (System of Record)

- **Statut** : Accepté
- **Date** : 2026-08-29
- **Auteurs** : Équipe d'Architecture Cortex
- **PRD IDs** : `PRD-ARCH-001`, `PRD-NFR-001`
- **Cadre de Référence** : *Agent Harness Architecture* (Sources → System of Record → Agent Layer → Control)

---

## 1. Contexte & Problématique

Dans les architectures ERP traditionnelles avec IA (« *AI bolted-on* »), les agents IA lisent des exports par lots et écrivent des suggestions dans une base séparée. Cela provoque :
1. Une perte de contexte en temps réel.
2. Une divergence fatale entre les règles humaines et les règles des agents.
3. Une rupture de la chaîne d'audit dès le franchissement de l'API.

Cortex adopte une approche **Agent-Native** où les agents opèrent **à l'intérieur du grand livre métier**, sous les mêmes politiques de validation et permissions que les opérateurs humains.

```
+-----------------------------------------------------------------------------------+
| SOURCES       | Courriels, PDF, Devis scannés, Appels, Formulaires, Webhooks      |
|               | -> Ingestion structurée immédiate ("Structure at the door")      |
+---------------+-------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| SYSTEM OF     | PostgreSQL 17 + Services Domaine & Policies Laravel 11            |
| RECORD        | - Source unique et immuable de vérité transactionnelle            |
|               | - Règles métier & Policies système (prix, caution, consignation)  |
|               | - Multi-tenant absolu (scopé par company_id)                      |
+---------------+-------------------------------------------------------------------+
                                   ▲          │
                    Écritures via  │          │ Lectures
                    API & Services │          │ typées
                                   │          ▼
+-----------------------------------------------------------------------------------+
| AGENT LAYER   | Onyx Headless / Serveur MCP (rental-mcp)                          |
|               | - Rapprochement & classification                                  |
|               | - Vérification de disponibilité & préparation de brouillons       |
|               | - Zéro accès SQL direct / Zéro base de données parallèle          |
+---------------+-------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| CONTROL       | 1. Journal d'audit append-only (audit_events) sur toute action    |
| & GATE        | 2. File d'approbation humaine (approval_requests)                 |
|               |    -> L'humain approuve avant écriture définitive en grand livre  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Décision d'Architecture

1. **PostgreSQL / Laravel est la source unique de vérité** :
   - Toutes les entités métier (transactions de location, inventaire, consignation, clients, factures) sont gérées exclusivement dans la base PostgreSQL via les Services et Policies de `apps/cortex-core` et `plugins/Webkul/CortexRental`.
   - Il n'existe **aucune base de données parallèle** ou cache persistant non synchronisé pour les agents IA.

2. **Interdiction formelle d'accès direct à la base pour les agents** :
   - Les agents Onyx et la façade `apps/cortex-mcp` ne disposent d'aucun identifiant de connexion SQL directe à PostgreSQL.
   - Toute interaction passe obligatoirement par l'API Laravel versionnée (`/api/v1/agent/...`) authentifiée par jetons Sanctum et scopée par `company_id`.

3. **Application des 4 Lois Fondamentales (*What Transfers*)** :
   - **Structure at the door** : Toute donnée entrante est immédiatement normalisée et typée. Aucun agent ne raisonne sur du texte non structuré.
   - **One source of truth** : Humains et agents lisent et écrivent dans le même store transactionnel.
   - **Same rules for both** : Les politiques métier sont codées en PHP (`ContractReadinessPolicy`, `ConsignmentPolicy`), jamais déléguées au prompt.
   - **Provenance before autonomy** : Toute mutation produit un enregistrement immuable dans `audit_events` (acteur, action, avant/après, preuve, policy, request_id, timestamp).

4. **Porte d'Approbation Humaine Invariable (*The Gate That Never Moves*)** :
   - Les agents peuvent lire l'état, vérifier la disponibilité et créer des **brouillons** (`quote`, `draft_customer`).
   - Les actions sensibles (confirmation de contrat, blocage définitif d'inventaire, émission de facture, sortie de matériel `checked_out`, remboursement) requièrent obligatoirement une validation humaine via la file `approval_requests`.

---

## 3. Conséquences

### Positives
- **Zéro divergence de données** : Impossible pour l'agent de promettre du matériel déjà réservé ou d'appliquer un tarif non conforme.
- **Auditabilité totale** : Chaque modification, qu'elle émane d'un employé ou d'un agent IA, est traçable jusqu'à sa source avec preuve et politique appliquée.
- **Sécurité multi-tenant garantie** : L'injection de `CompanyContext` dans chaque requête Laravel empêche tout accès cross-tenant, même via un outil MCP.
- **Gouvernance sans friction** : L'opérateur humain conserve le contrôle total sur les engagements légaux et financiers.

### Négatives / Contraintes
- Nécessite d'exposer chaque capacité d'agent sous forme d'endpoint d'API Laravel typé et testé.
- Interdiction des raccourcis de développement (scripts directs en DB).
