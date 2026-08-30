## Description & Objectif de la PR
- **ID PRD** : `PRD-XXX` *(ex: PRD-ARCH-001, PRD-CON-001, PRD-INV-001)*
- **Issue liee** : #
- **Modele d'implementation** : Gemini 3.7 Flash
- **Modele de revue & arbitrage** : Claude Sonnet 5
- **Type de changement** : [ ] Feature  [ ] Fix  [ ] Refactoring  [ ] Migration  [ ] Securite

---

## Invariants d'Architecture & Securite
- [ ] **Multi-Tenancy** : Toutes les requetes, relations et jobs sont strictement scopes par `company_id`.
- [ ] **Systeme d'Enregistrement** : Conforme a ADR-001 (PostgreSQL/Laravel unique source de verite, zero SQL Onyx).
- [ ] **Isolement du Domaine** : Toute la logique reside dans `plugins/Webkul/CortexRental` (aucun hack du core Aureus).
- [ ] **Transactions ACID** : Ecritures enveloppees dans `DB::transaction()` avec verrous pessimistes d'inventaire.

---

## Base de Donnees & Migrations
- **Migrations ajoutees / modifiees** :
  - `database/migrations/YYYY_MM_DD_HHMMSS_*.php`
- **Impact sur les index & performances** :
- **Contrainte de cle etrangere & cascading** :

---

## Endpoints API & Outils MCP
- **Endpoints Laravel crees / modifies** :
  - `METHOD /api/v1/agent/...`
- **Policies Laravel appliquees** :
  - `PolicyName::class`
- **Evenements d'Audit (`audit_events`) emis** :
  - Action, entite, preuve et etat avant/apres.
- **Outils MCP / Onyx Actions modifies** :
  - `tool_name` (schema Zod / OpenAPI)

---

## Tests & Analyse Statique
- [ ] **Validation Globale** : `./bin/pre-claude-check.sh` passe avec succes (100% vert).
- [ ] **Tests Pest** : 100% passants (`vendor/bin/pest`).
- [ ] **PHPStan** : Niveau 8+ sans erreur (`./vendor/bin/phpstan analyse`).
- [ ] **Laravel Pint** : Conforme (`./vendor/bin/pint --test`).
- [ ] **Tests UI Filament / Livewire** : `Livewire::test(...)` executes avec succes.
- [ ] **Acceptance Tests (Gherkin)** : Scenarios valides.

---

## Evaluation des Risques & Plan de Rollback
- **Niveau de risque** : [ ] Faible  [ ] Moyen  [ ] Critique (Financier / Inventaire)
- **Scenario d'echec identifie** :
- **Procedure de Rollback** :
  ```bash
  php artisan migrate:rollback --step=1
  ```

---

## Preuves d'Execution & Captures UI
*(Inserer captures UI Filament, logs d'audit ou sorties de tests)*
