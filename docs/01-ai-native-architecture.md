# Architecture AI-Native & Principes Fondateurs

Ce document définit les principes directeurs, les règles non négociables et les contrats de données garantissant que l'ERP est **AI-Native First** dès le premier commit, et non un ERP traditionnel avec une couche IA greffée après coup (*AI bolted-on*).

---

## 1. Ce que signifie « AI-Native First »

Dans notre système, « AI-Native » ne signifie pas :
```
ERP traditionnel
+ bouton "Demander à l'IA"
+ chat qui lit quelques PDF
```

Cela signifie une architecture pensée de bout en bout pour l'autonomie supervisée :
```
Entrées structurées (Structure at the door)
  → Système métier canonique (Domain Driven Design)
  → APIs / Outils versionnés (OpenAPI & MCP)
  → Humain et Agent utilisent les mêmes règles (Policies & Domain Services)
  → Audit et provenance systématiques (Append-only Event Log)
  → Approbation quand le risque l'exige (Human-in-the-loop / Approval Queue)
  → Autonomie élargie de façon mesurable (Progressive Autonomy Levels 0-7)
```

---

## 2. Les 4 Règles Non Négociables

| # | Règle | Description |
|---|---|---|
| **1** | **Structure at the door** | Tout courriel, PDF, appel ou formulaire entrant est immédiatement transformé en objets métier typés. L'agent ne raisonne jamais directement sur des captures d'écran ou du texte brut non structuré. |
| **2** | **One source of truth** | Les humains et les agents lisent et écrivent dans le même store métier (PostgreSQL). Il n'existe **aucune base IA parallèle** avec ses propres statuts ou inventaires désynchronisés. |
| **3** | **Same rules for both** | Les politiques de tarification, de contrat, de dépôt, d'assurance, de consignation et de permissions vivent dans le code (Services & Policies Laravel), **jamais uniquement dans le prompt de l'agent**. |
| **4** | **Provenance before autonomy** | Toute action doit être traçable (qui/quoi/quand/pourquoi), explicable et munie d'une preuve d'audit avant d'accorder de l'autonomie à l'agent. Les actions critiques restent soumises à une file d'approbation humaine. |

---

## 3. Matrice de Conformité d'Architecture

| Élément | Conforme au PRD ? | Rationale & Justification |
|---|:---:|---|
| **Onyx connecté à Laravel par API métier** |  Oui | Chaque capacité métier devient un endpoint versionné et restreint. |
| **Agents avec permissions / scopes propres** |  Oui | Chaque agent agit comme un employé virtuel avec un rôle RBAC strict. |
| **API unique pour Filament & Agents** |  Oui | L'interface Filament n'est qu'un client parmi d'autres au-dessus des services de domaine. |
| **PostgreSQL comme source métier** |  Oui | Unique source de vérité transactionnelle, indexée et relationnelle. |
| **`audit_events` append-only** |  Oui | Capture immuable : acteur, état avant, état après, preuves et décisions de policy. |
| **File d'approbation native** |  Oui | Contrats, modifications de prix, factures et envois clients requièrent une validation humaine. |
| **Brouillons IA avant mutation définitive** |  Oui | L'agent prépare les devis/demandes (`draft`), l'humain valide et active. |
| **Onyx séparé du core Laravel** |  Oui | Séparation d'infrastructure physique/conteneurs, sans divergence de données. |
| **MCP avec outils limités** |  Oui | Capacités exposées de façon explicite, documentée et contrôlée. |
| **Onyx sans accès SQL direct** |  Oui | Impossibilité pour l'IA de contourner les invariants métier et les triggers d'audit. |
| **Consignation dans le domaine core** |  Oui | Premier module implémenté, différenciateur fort du produit. |
| **Disponibilité calculée par API réelle** |  Oui | L'agent répond toujours depuis l'état réel et vérifiable du calendrier d'inventaire. |

---

## 4. Comparatif d'Approche : Éviter le piège du "AI Bolted-On"

```
[Legacy ERP]
└── L'agent n'existe nulle part dans le système.

[AI Bolted-On]
├── L'agent lit des exports batch et écrit des suggestions dans un silo séparé.
├── Pas de contexte partagé en temps réel.
├── Pas de contrôles communs de politiques métier.
└── Audit trail qui s'arrête à l'appel d'API générique.

[Agent-Native (Notre Architecture)]
├── L'agent agit directement dans le système de référence via des outils métier.
├── Mêmes politiques de validation appliquées aux humains et aux agents.
├── Toute action est consignée dans un log d'audit append-only avec preuve.
└── L'humain approuve les actions à risque via une file d'attente native.
```

---

## 5. Règle des 3 Clients & Démarche de Livraison

Toute fonctionnalité développée doit être conçue simultanément pour **trois clients** :
1. **L'interface humaine** (Filament / Aureus UI).
2. **L'agent IA** (Onyx via OpenAPI / MCP).
3. **Les intégrations tierces et futures** (API publique / webhooks).

### Cycle de livraison par module (7 livrables simultanés) :
1. **Une UI humaine Aureus** (Ressource / Page Filament réactive).
2. **Une Action / API versionnée** (`/api/v1/agent/...`).
3. **Un outil Onyx / MCP** (Tool TypeScript / JSON Schema).
4. **Une Policy Laravel** (`ContractReadinessPolicy`, etc.).
5. **Un Audit Event** (Trace immuable avec preuve et acteur).
6. **Un test humain** (Feature test simulant un opérateur).
7. **Un test agent** (Feature test simulant le Service Account IA).

---

## 6. Modèle Métier Agent-Ready & Contrats Structurés

Chaque entité du domaine doit être modélisée pour être lue et manipulée de façon déterministe par un agent, sans scraping HTML :

- `Customer`
- `Item`
- `SerialNumber`
- `Owner`
- `Transaction` & `TransactionLine`
- `Invoice` & `ConsignmentPayout`
- `CheckIn`
- `ApprovalRequest`
- `AuditEvent`
- `Evidence`

### Format standard de ressource exposée :
```json
{
  "id": "tx_1024",
  "type": "rental_transaction",
  "state": "reservation",
  "company_id": "cmp_123",
  "created_by": {
    "type": "agent",
    "id": "agent:intake-email"
  },
  "updated_at": "2026-08-29T16:00:00-04:00",
  "links": {
    "self": "/api/v1/transactions/tx_1024",
    "approve": "/api/v1/approval-requests/apr_456"
  }
}
```

---

## 7. Journal d'Audit Append-Only (`audit_events`)

Chaque mutation du système doit émettre un événement structuré.

### Schéma de la table `audit_events` :
```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    actor_type VARCHAR(30) NOT NULL,    -- 'agent', 'human', 'system'
    actor_id UUID NULL,
    action VARCHAR(120) NOT NULL,        -- 'quote.draft_created', 'transaction.transitioned', etc.
    entity_type VARCHAR(120) NOT NULL,
    entity_id UUID NOT NULL,
    before_state JSONB NULL,
    after_state JSONB NULL,
    evidence JSONB NOT NULL DEFAULT '[]',
    policy_decision JSONB NULL,
    request_id VARCHAR(120) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Règle RBAC PostgreSQL en production :
-- SELECT, INSERT autorisés
-- UPDATE, DELETE strictement INTERDITS
```

### Exemple de payload d'audit complet :
```json
{
  "id": "evt_019",
  "company_id": "cmp_123",
  "occurred_at": "2026-08-29T17:02:11-04:00",
  "actor": {
    "type": "agent",
    "id": "agent:intake-email",
    "name": "Intake Location"
  },
  "action": "quote.draft_created",
  "entity": {
    "type": "rental_transaction",
    "id": "tx_1024"
  },
  "before_state": null,
  "after_state": {
    "state": "quote",
    "inventory_blocked": false
  },
  "evidence": [
    {
      "type": "email",
      "id": "msg_721",
      "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "policy": {
    "name": "agent.quote_draft.create",
    "version": "2026-08-01",
    "decision": "allow"
  },
  "request_id": "req_874"
}
```

---

## 8. Pipeline d'Ingestion Structurée (L'ingestion comme produit)

L'agent d'ingestion ne produit pas de texte libre non audité ; il alimente un pipeline d'entités canoniques :

```
Courriel ou Document entrant
  ↓
InboundMessage (Stockage brut sécurisé)
  ↓
Attachment / Evidence (Indexation & hachage sha256)
  ↓
Extraction Structurée (JSON Schema)
  ↓
ExtractionCandidate (Champs extraits avec niveau de confiance et preuve)
  ↓
QuoteDraft ou CustomerDraft (Brouillon non bloquant)
  ↓
ApprovalRequest (Validation humaine si score d'incertitude ou criticité)
  ↓
RentalTransaction / Customer final validé
```

### Tables du sous-système d'ingestion :
- `inbound_messages`
- `inbound_attachments`
- `extraction_runs`
- `extraction_candidates`
- `evidence_references`
- `agent_runs`
- `agent_tool_calls`

### Format d'un `ExtractionCandidate` :
```json
{
  "field": "rental_start_date",
  "value": "2026-09-08T09:00:00-04:00",
  "confidence": 0.94,
  "evidence": {
    "document_id": "doc_235",
    "page": 1,
    "quote": "Nous avons besoin des tubes du 8 au 18 septembre."
  },
  "requires_review": false
}
```

---

## 9. Les Politiques : Code et Données, Jamais de Prompt

> **Principe de sécurité fondamental** : Les invites de commandes (*prompts*) orientent le comportement de l'IA mais ne constituent **en aucun cas** une frontière de sécurité ou de validation métier.

```php
namespace Webkul\Rental\Policies;

use Webkul\Rental\Models\RentalTransaction;
use Webkul\Rental\Exceptions\AccountNotReadyException;
use Webkul\Rental\Exceptions\InsuranceNotReadyException;
use Webkul\Rental\Exceptions\PaymentNotReadyException;

final class ContractReadinessPolicy
{
    public function assertCanActivate(RentalTransaction $transaction): void
    {
        throw_unless(
            $transaction->customer_account_ready,
            AccountNotReadyException::class,
            'Le compte client n’est pas vérifié.'
        );

        throw_unless(
            $transaction->insurance_ready,
            InsuranceNotReadyException::class,
            'L’attestation d’assurance valide est requise avant le passage en contrat.'
        );

        throw_unless(
            $transaction->payment_ready,
            PaymentNotReadyException::class,
            'Le mode de paiement ou le dépôt de garantie n’est pas validé.'
        );
    }
}
```

---

## 10. Matrice de Progression de l'Autonomie (Niveaux 0 à 7)

L'autonomie est débloquée graduellement en fonction de la traçabilité éprouvée :

| Niveau | Exemple d'Action | Agent Autonome ? | Approbation Requise |
|:---:|---|:---:|---|
| **0** | Recherche équipement, client ou disponibilité |  **Oui** | Aucune (Lecture seule) |
| **1** | Extraction courriel / PDF |  **Oui** | Non, mais référence de preuve obligatoire |
| **2** | Création de brouillon (`QuoteDraft`, `CustomerDraft`) |  **Oui** | Non (n'impacte pas l'inventaire) |
| **3** | Proposition de réservation |  **Oui** (comme suggestion) | **Oui** avant réservation ferme |
| **4** | Passage en contrat (`contract`) |  **Non** | **Oui** + vérification stricte de readiness |
| **5** | Facturation, émission d'avoir, encaissement |  **Non** | **Oui** (Manager / Finance) |
| **6** | Envoi de documents officiels au client |  **Non** | **Oui** (Opérateur comptoir) |
| **7** | Réservation automatique à faible risque |  *Plus tard* | Selon politique configurable par compagnie |

---

## 11. Définition Pratique & Critères de Réussite AI-Native

Le système est certifié **AI-Native** lorsque l'ensemble des affirmations suivantes sont vraies :

1. Un agent peut exécuter les mêmes requêtes de recherche qu'un employé en invoquant les mêmes services Laravel de référence.
2. Un agent peut créer un brouillon de soumission complet à partir d'un courriel sans double saisie humaine.
3. L'agent sait expliquer précisément la cause d'un conflit de disponibilité en se basant sur les réservations et maintenances réelles.
4. L'agent est techniquement incapable d'outrepasser une règle de prix, d'assurance, de dépôt ou de statut.
5. Toute proposition d'un agent peut être inspectée, éditée, acceptée ou rejetée directement dans l'interface Filament/Aureus.
6. Chaque action IA est reliée à un identifiant d'agent, aux documents sources de preuve et aux états avant/après.
7. Les agents respectent l'isolation multi-tenant stricte via le `CompanyContext`.
8. Ajouter un nouveau cas d'usage consiste à créer un outil versionné, des permissions et une policy — et non à redévelopper une intégration ad-hoc.
9. L'utilisateur effectue l'intégralité de son travail sans quitter son ERP pour consulter un chatbot externe.
10. La file d'approbation humaine est une primitive native du produit au cœur de l'application.
