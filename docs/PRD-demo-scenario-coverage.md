# Matrice de Couverture des Tests d'Acceptation — Scénario de Démo Cortex

Ce document détaille la couverture des exigences produit (PRD) pour le scénario de démo de bout en bout de **Cortex ERP AI-Native** et ses barrières de sécurité obligatoires.

---

## 📋 Scénario de Démo — 9 Étapes

| Étape | Description Métier | ID PRD | Fichier de Test | Méthode / Nom de Test | Statut |
|---|---|---|---|---|---|
| **1 & 2** | Ingestion email de demande & création brouillon de soumission avec preuves par l'agent | `PRD-AI-001`<br>`PRD-TRX-001` | `DemoEndToEndScenarioTest.php` | `Step 1 & 2: Intake agent ingests email request and creates quote draft with audit evidence` | ✅ Implémenté & Passant |
| **3** | Approbation humaine du brouillon & transition vers réservation | `PRD-AI-002`<br>`PRD-TRX-001` | `DemoEndToEndScenarioTest.php` | `Step 3: Human supervisor approves quote draft and converts transaction to reservation` | ✅ Implémenté & Passant |
| **4** | Mise à jour de la disponibilité en temps réel (réservation bloque le stock) | `PRD-INV-001`<br>`PRD-INV-002` | `DemoEndToEndScenarioTest.php` | `Step 4: Real-time availability service reflects inventory blocked by reservation` | ✅ Implémenté & Passant |
| **5** | Prérequis de passage à contrat (compte, assurance, paiement) | `PRD-CLI-001`<br>`PRD-TRX-002` | `DemoEndToEndScenarioTest.php` | `Step 5: Transition to contract strictly validates account, insurance, and payment readiness` | ✅ Implémenté & Passant |
| **5.1** | Service d'activation de contrat & verrouillage des numéros de série | `PRD-TRX-002` | `DemoEndToEndScenarioTest.php` | `Step 5.1: Contract activation service transitions reservation to contract and locks serial allocations` | ⏳ Skipped (TODO PRD-TRX-002) |
| **6** | Règle tarifaire : 7 jours calendaires = 3 jours facturables | `PRD-TRX-001` | `DemoEndToEndScenarioTest.php` | `Step 6: Pricing rule of 7 calendar days equals 3 billable days is correctly applied to financial totals` | ✅ Implémenté & Passant |
| **7** | Retour scanné de 2 items sur 3 lors du check-in | `PRD-RET-001` | `DemoEndToEndScenarioTest.php` | `Step 7: Return scan checks in 2 out of 3 serialized units and updates their status to available` | ⏳ Skipped (TODO PRD-RET-001) |
| **8** | Un item marqué `missing` & reste (2 items) facturable | `PRD-RET-002`<br>`PRD-TRX-001` | `DemoEndToEndScenarioTest.php` | `Step 8: Missing serial unit is marked missing and remaining 2 units are finalized for billing` | ✅ Implémenté & Passant |
| **9** | Rapport propriétaire de consignation sans identité locataire | `PRD-CON-001`<br>`PRD-CON-003` | `DemoEndToEndScenarioTest.php` | `Step 9: Consignment owner payout is computed and report contains zero tenant/renter identity` | ✅ Implémenté & Passant |

---

## 🔒 4 Barrières de Sécurité Obligatoires

| Invariant de Sécurité | ID PRD | Fichier de Test | Méthode / Nom de Test | Statut |
|---|---|---|---|---|
| **Gate 1 : Anti auto-approbation Agent** | `PRD-AI-002`<br>`PRD-ARCH-003` | `DemoScenarioSecurityTest.php` | `Security Gate 1: Agent is strictly forbidden from approving requests or activating contracts alone` | ✅ Implémenté & Passant |
| **Gate 2 : Isolation multi-tenant stricte** | `PRD-NFR-001`<br>`PRD-ARCH-001` | `DemoScenarioSecurityTest.php` | `Security Gate 2: Tenant A agent and user cannot view, query, or mutate Tenant B records` | ✅ Implémenté & Passant |
| **Gate 3 : Audit trail append-only et immuable** | `PRD-ARCH-003`<br>`PRD-NFR-001` | `DemoScenarioSecurityTest.php` | `Security Gate 3: Every state mutation produces an audit event and audit records cannot be altered or deleted` | ✅ Implémenté & Passant |
| **Gate 4 : Confidentialité stricte du relevé propriétaire** | `PRD-CON-003`<br>`PRD-NFR-001` | `DemoScenarioSecurityTest.php` | `Security Gate 4: Owner statements and calculation snapshots strictly redact customer and renter identity` | ✅ Implémenté & Passant |

---

## 🛠️ Helpers et Fixtures Réutilisables

- **`AssertsAuditEvents`** (`plugins/Webkul/CortexRental/tests/Traits/AssertsAuditEvents.php`) :
  - `assertAuditEventLogged($companyId, $action, $entityType, $entityId, ?ActorType $actorType, ?callable $callback)`
  - `assertNoAuditEventLogged($companyId, $action, ?string $entityId)`
  - `assertAuditEventImmutable(AuditEvent $event)`
- **`AssertsTenantIsolation`** (`plugins/Webkul/CortexRental/tests/Traits/AssertsTenantIsolation.php`) :
  - `assertTenantCannotAccessItem($userA, $itemB)`
  - `assertTenantCannotAccessTransaction($userA, $trxB)`
  - `assertOwnerStatementContainsNoRenterIdentity($statementData, array $forbiddenIdentities)`
- **`DemoScenarioFixtureBuilder`** (`plugins/Webkul/CortexRental/tests/Helpers/DemoScenarioFixtureBuilder.php`) :
  - Génère Company A, Company B, Agent Intake, Superviseur, Propriétaire consignateur (Roger Deakins 70/30), Caméra ARRI Alexa 35 (3 numéros de série), règle tarifaire 7j=3j, et client (Dune 3 Productions).
- **Extensions Pest `expect()`** (`plugins/Webkul/CortexRental/tests/Pest.php`) :
  - `expect($trx)->toHaveAuditEvent('rental.quote.draft_created')`
  - `expect($data)->toNotExposeRenterIdentity(['Dune 3', 'contact@dune3prod.com'])`
  - `expect($event)->toBeImmutable()`

---

## 🚀 Commandes d'Exécution des Tests

### Exécution locale (si vendor/bin/pest est configuré) :
```bash
# Exécuter l'ensemble de la suite du scénario de démo et de sécurité
./apps/cortex-core/vendor/bin/pest plugins/Webkul/CortexRental/tests/Feature/Scenario

# Exécuter uniquement le scénario de démo de bout en bout (étapes 1 à 9)
./apps/cortex-core/vendor/bin/pest plugins/Webkul/CortexRental/tests/Feature/Scenario/DemoEndToEndScenarioTest.php

# Exécuter uniquement les 4 barrières de sécurité
./apps/cortex-core/vendor/bin/pest plugins/Webkul/CortexRental/tests/Feature/Scenario/DemoScenarioSecurityTest.php
```

### Exécution via Docker (Makefile) :
```bash
# Exécuter les tests dans le conteneur app
make test

# Lancer la validation complète pre-claude
make check-all
```
