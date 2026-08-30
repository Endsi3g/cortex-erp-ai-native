# Stratégie Multi-Modèles & Routage Intelligent : Gemini 3.7 Flash & Claude Sonnet 5

Ce document définit la stratégie d'allocation des modèles d'IA dans l'architecture ERP AI-Native **Cortex**. Il formalise la répartition des rôles entre **Gemini 3.7 Flash** (moteur opérationnel à haut volume) et **Claude Sonnet 5** (expert de raisonnement et d'escalade), ainsi que l'implémentation du routeur dynamique (`ModelRouter`) dans Laravel.

---

## 1. Vision & Répartition des Rôles

Pour garantir une performance optimale, une réactivité maximale et une maîtrise stricte des coûts, le système applique le principe du **Routage par Complexité** :

- **Gemini 3.7 Flash (Moteur Opérationnel par Défaut)** : Absorbe 85% à 95% du volume quotidien — extraction multimodale (courriels, PDF, photos d'équipement, notes vocales), classification, questions/réponses sur la disponibilité, génération de brouillons de devis et normalisation des imports.
- **Claude Sonnet 5 (Agent Expert d'Escalade & Ingénierie)** : Intervient sur les dossiers complexes — arbitrage d'ambiguïtés contractuelles, litiges de consignation, analyse de code/architecture, débogage de concurrence et pilotage d'agents Playwright pour interfaces legacy.

```
                  +---------------------------------------------------+
                  |                 DEMANDE ENTRANTE                  |
                  |     (Courriel, Document, Chat, Action Métier)     |
                  +-------------------------+-------------------------+
                                            |
                                            v
                  +---------------------------------------------------+
                  |               LARAVEL AGENT ROUTER                |
                  |     (Classification Risque, Complexité, Coût)     |
                  +-------------------------+-------------------------+
                                            |
                       +--------------------+--------------------+
                       |                                         |
     [ Volume / Standard / Multimodal ]               [ Complexité / Escalade / Code ]
                       |                                         |
                       v                                         v
        +-----------------------------+           +-----------------------------+
        |      GEMINI 3.7 FLASH       |           |       CLAUDE SONNET 5       |
        |  - Extraction & Parsing     |           |  - Raisonnement profond     |
        |  - Multimodalité riche      |           |  - Exceptions & Litiges     |
        |  - Brouillons de soumission |           |  - Revue de code & SRE      |
        |  - Q&R Disponibilité        |           |  - Analyse contractuelle    |
        +--------------+--------------+           +--------------+--------------+
                       |                                         |
                       +--------------------+--------------------+
                                            |
                                            v
                  +---------------------------------------------------+
                  |                OUTILS MCP & OPENAPI               |
                  |            (rental-mcp / Laravel API)             |
                  +-------------------------+-------------------------+
                                            |
                                            v
                  +---------------------------------------------------+
                  |             POLICIES & DOMAIN SERVICES            |
                  |          (Contrôle des règles en PHP/SQL)         |
                  +-------------------------+-------------------------+
                                            |
                                            v
                  +---------------------------------------------------+
                  |        AUDIT LOG + FILE D'APPROBATION SI REQUIS   |
                  +---------------------------------------------------+
```

> **Règle fondamentale d'isolation** : Le routeur de modèles sélectionne *quelle intelligence propose une action*, mais **ne décide jamais des permissions**. Les droits et les validations de sécurité restent sous le contrôle exclusif de Laravel.

---

## 2. Tableau Comparatif Pratique

| Critère | Gemini 3.7 Flash | Claude Sonnet 5 | Choix Stratégique pour l'ERP |
|---|---|---|---|
| **Rôle Optimal** | Agent rapide, économique, haut débit | Agent expert pour tâches complexes & code | **Routage dynamique** selon le contexte |
| **Fenêtre de Contexte** | Jusqu'à 1M tokens | Jusqu'à 1M tokens | Égalité pratique |
| **Sortie Maximale** | Jusqu'à 64K tokens | Jusqu'à 128K tokens | Sonnet pour les synthèses et dossiers volumineux |
| **Capacités Multimodales** | Texte, Image, Audio, Vidéo, PDF | Texte et Images haute résolution | **Gemini** en première ligne pour l'intake omnicanal |
| **Structured Output** | Natif & déterministe (JSON Schema) | Support outillé rigoureux | Les deux pour produire du JSON métier typé |
| **Function Calling / MCP** | Support complet | Support complet & chaînage précis | Les deux via le serveur `rental-mcp` |
| **Exécution de Code** | Intégrée (Python / sandbox) | Interprétation & terminal outillé | Gemini pour micro-calculs, Sonnet pour debug complexe |
| **Computer Use** | Preview disponible | Hautement documenté / mature | Sonnet pour scripts Playwright et ERP legacy |
| **Vitesse & Coût** | Extrêmement rapide et économique | Plus coûteux, raisonnement profond | **Gemini par défaut**, Sonnet sur escalade |
| **Raisonnement Codebase** | Bon à très bon | Exceptionnel sur refactors cross-files | **Sonnet** pour l'ingénierie et la sécurité |
| **Documents Entrants** | Formats riches et hétérogènes | Lecture juridique ciblée | Gemini d'abord, Sonnet si litige |
| **Décisions Métier Critiques**| Jamais autonome | Jamais autonome | **Validation Laravel + Approbation humaine** |

---

## 3. Rôles et Cas d'Usage Spécifiques

---

### A. Tâches Assignées à Gemini 3.7 Flash

#### 1. Ingestion Multimodale (Courriels, PDF, Photos & Notes Vocales)
Transformation instantanée de données non structurées en objets typés prêts pour l'API Laravel :
```json
{
  "customer": {
    "name": "Production Nord",
    "email": "location@productionnord.ca",
    "confidence": 0.98
  },
  "rental_period": {
    "starts_at": "2026-09-08T09:00:00-04:00",
    "ends_at": "2026-09-18T19:00:00-04:00",
    "confidence": 0.93
  },
  "requested_items": [
    {
      "raw_description": "12 tubes Astera de 4 pieds",
      "quantity": 12,
      "confidence": 0.89
    }
  ],
  "missing_information": [
    "Adresse exacte de livraison sur le plateau"
  ],
  "evidence": [
    {
      "source_id": "email_123",
      "quote": "Nous aurions besoin de 12 tubes du 8 au 18 septembre."
    }
  ]
}
```

#### 2. Classification et Triage Rapide
- Typage des messages entrants : `demande_soumission`, `ouverture_compte`, `prolongation`, `retour_partiel`, `sinistre`, `facturation`, `support`, `spam`.
- Détection des attributs clés : urgence, dates, équipements demandés, client existant, police d'assurance jointe.

#### 3. Q&R Disponibilité à Haut Débit
- Consultation directe du calendrier de stock via l'outil `check_inventory_availability`.
- Formulation de réponses claires et immédiates pour les opérateurs de comptoir.

#### 4. Génération de Brouillons Sans Impact Inventaire
- Préparation de `QuoteDraft` et `CustomerDraft`.
- Rédaction de courriels de clarification en français et en anglais.

#### 5. Normalisation et Migration de Données Legacy
- Traitement de fichiers CSV/Excel hétérogènes.
- Détection de doublons, normalisation des désignations et préparation des tables de staging.

---

### B. Tâches Assignées à Claude Sonnet 5

#### 1. Architecture, Codebase & Ingénierie
- Analyse approfondie des modèles, migrations PostgreSQL et invariants d'inventaire.
- Refactoring du `AvailabilityService` et des règles de calcul de consignation.
- Revue de sécurité cross-files (ex. : s'assurer qu'aucun chemin de code ne permet de passer une soumission en contrat sans validation des conditions de paiement et d'assurance).
- Génération de tests d'intégration complets avec Pest PHP.

#### 2. Arbitrage des Exceptions Métier Complexes
Intervention lorsque les règles métier entrent en conflit :
- Plages de dates contradictoires dans un bon de commande client.
- Factures mixtes combinant équipements en propriété interne et équipements consignés par plusieurs propriétaires distincts.
- Prolongation de contrat créant un conflit partiel avec plusieurs réservations futures.
- Contestation d'un rapport de consignation par un propriétaire tiers.

```json
{
  "case_type": "complex_rental_exception",
  "facts": [
    "Contrat #1042 en cours jusqu'au 15 sept",
    "Demande de prolongation au 22 sept",
    "Réservation #1088 planifiée le 18 sept sur 4 unités identiques"
  ],
  "conflicts": [
    "Manque de 2 unités entre le 18 et le 22 sept si prolongation acceptée"
  ],
  "possible_resolutions": [
    {
      "option": "substitute_equipment",
      "description": "Remplacer 2 unités par le modèle supérieur disponible en stock interne",
      "additional_cost": 0
    },
    {
      "option": "sub_rental",
      "description": "Sous-louer 2 unités auprès d'un partenaire externe",
      "estimated_cost": 180.00
    }
  ],
  "recommended_resolution": {
    "action": "propose_substitution",
    "target_transaction": "tx_1042"
  },
  "required_human_approval": true
}
```

#### 3. Analyse Juridique & Conformité Assurantielle
- Comparaison point par point d'une attestation d'assurance reçue avec les exigences contractuelles (montants de garantie, clauses de responsabilité civile, franchises).
- Détection des clauses d'exclusion préjudiciables à la location d'équipement de valeur.

#### 4. Débogage Approfondi SRE & Base de Données
- Analyse des logs d'erreurs Laravel et des jobs Redis en échec.
- Résolution des situations de *deadlock* SQL ou de concurrence transactionnelle sur les numéros de série.

#### 5. Pilotage d'Agents Playwright pour l'Extraction d'ERP Legacy
- Analyse visuelle et structurelle des écrans d'anciennes applications de gestion.
- Adaptation dynamique des sélecteurs Playwright face aux variations de mise en page.

---

## 4. Implémentation du Routeur de Modèles (`ModelRouter.php`)

Le routeur analyse les caractéristiques de chaque tâche pour sélectionner dynamiquement le modèle le plus adapté :

```php
namespace Webkul\Rental\Services\AI;

use Webkul\Rental\ValueObjects\AgentTask;
use Webkul\Rental\ValueObjects\ModelSelection;

final class ModelRouter
{
    public function select(AgentTask $task): ModelSelection
    {
        // 1. Escalade vers Sonnet 5 pour les tâches d'ingénierie et de code
        if ($task->requiresCodebaseReasoning()) {
            return ModelSelection::sonnet5('codebase_reasoning');
        }

        // 2. Escalade pour les analyses juridiques ou de politiques complexes
        if ($task->requiresComplexPolicyAnalysis()) {
            return ModelSelection::sonnet5('complex_policy_analysis');
        }

        // 3. Escalade pour le pilotage d'interface / Computer Use
        if ($task->requiresComputerUse()) {
            return ModelSelection::sonnet5('computer_use_playwright');
        }

        // 4. Escalade basée sur les seuils d'incertitude ou de risque financier
        if ($task->confidenceScore() < 0.80) {
            return ModelSelection::sonnet5('low_confidence_fallback');
        }

        if ($task->hasContradictorySources()) {
            return ModelSelection::sonnet5('contradictory_sources_detected');
        }

        if ($task->financialAmount() > config('rental.ai.sonnet_threshold_amount', 5000.00)) {
            return ModelSelection::sonnet5('high_value_transaction');
        }

        if ($task->isConsignmentDispute()) {
            return ModelSelection::sonnet5('consignment_dispute');
        }

        if ($task->consecutiveToolFailures() >= 2) {
            return ModelSelection::sonnet5('tool_failure_escalation');
        }

        // 5. Moteur par défaut : Gemini 3.7 Flash pour l'opérationnel
        return ModelSelection::gemini37Flash('standard_operational_task');
    }
}
```

---

## 5. Schéma de Télémétrie & Traçabilité (`agent_runs`)

Chaque exécution d'agent est enregistrée avec les métriques précises d'utilisation des modèles :

```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    task_type VARCHAR(80) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,       -- 'google', 'anthropic'
    model_name VARCHAR(80) NOT NULL,           -- 'gemini-3.7-flash', 'claude-sonnet-5'
    model_version VARCHAR(50) NOT NULL,
    routing_reason VARCHAR(120) NOT NULL,
    escalated_from VARCHAR(80) NULL,           -- Si escaladé depuis Gemini
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_estimate NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    confidence NUMERIC(4, 3) NULL,
    tool_calls JSONB NOT NULL DEFAULT '[]',
    approval_request_id UUID NULL,
    execution_time_ms INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,               -- 'completed', 'escalated', 'failed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_company ON agent_runs(company_id);
CREATE INDEX idx_agent_runs_model ON agent_runs(model_name);
CREATE INDEX idx_agent_runs_created ON agent_runs(created_at);
```

---

## 6. Analyse des Coûts & Tableau de Pilotage Opérationnel

Sur la base d'un volume standard de **200 demandes mensuelles** pour une entreprise de location :

| Type de Tâche | Modèle par Défaut | Modèle d'Escalade | Objectif Opérationnel |
|---|---|---|---|
| **200 demandes email/PDF/mois** | Gemini 3.7 Flash | Claude Sonnet 5 si score < 0.80 | Éliminer 90% de la saisie manuelle |
| **Q&R Disponibilité de stock** | Gemini 3.7 Flash | Aucune (sauf erreur technique API) | Réponse instantanée au comptoir (< 1.5s) |
| **Création de devis brouillon** | Gemini 3.7 Flash | Claude Sonnet 5 si multi-contrats | Préparation sécurisée des devis |
| **Calcul & Rapport consignation**| Laravel calcule, Gemini rédige | Claude Sonnet 5 si litige | Précision mathématique déterministe |
| **Validation attestation assurance**| Gemini extrait les dates/montants | Claude Sonnet 5 analyse les clauses | Réduction du risque de sinistre non couvert |
| **Migration données legacy** | Gemini pour lots standards | Claude Sonnet 5 pour schémas obscurs | Importation fluide et vérifiée |
| **Revue de PR & Sécurité** | Claude Sonnet 5 | Modèle supérieur si refactor majeur | Zéro faille de politique métier en prod |

---

## 7. Métriques de Suivi Hebdomadaires (KPIs)

Chaque semaine, l'équipe d'ingénierie et d'exploitation surveille :

1. **Taux de brouillons acceptés sans modification** (Cible : > 80%).
2. **Taux de correction humaine requise** (Cible : < 15%).
3. **Taux d'escalade Gemini → Sonnet** (Cible : 5% à 12%).
4. **Coût moyen d'IA par soumission traitée** (Cible : < 0,05 $ / dossier).
5. **Temps moyen de réponse de l'assistant** (Cible : < 2 secondes sur Gemini).
6. **Taux d'erreur sur les appels d'outils MCP** (Cible : < 1%).
7. **Taux de blocage par les Policies Laravel** (Mesure de conformité des prompts).
