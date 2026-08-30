# Workflow d'Ingénierie Multi-Modèles : Gemini → Claude

Ce document formalise le workflow de développement obligatoire utilisé en permanence sur **Cortex ERP AI-Native**. Il combine la vitesse de génération et le typage strict de **Gemini** avec la capacité d'analyse en profondeur, d'arbitrage et de revue de sécurité de **Claude**, sous la supervision souveraine de l'**Opérateur Humain**.

---

## 1. Répartition des Rôles

| Acteur | Responsabilité Principale | Périmètre & Attentes |
|---|---|---|
| **Gemini (Implémentation & Génération)** | Génération de code rapide, migrations, services de domaine, tests Pest, composants Filament et interfaces TypeScript MCP. | Travaille sur un ticket atomique borné, respecte les 7 règles non négociables, ne touche jamais au core Aureus. |
| **Claude (Revue & Arbitrage Stricte)** | Revue de diff Git, détection des régressions multi-tenant (`company_id`), failles de sécurité, cohérence ACID, omissions d'événements `audit_events` et analyse statique. | Analyse le diff complet, propose des corrections chirurgicales et justifiées sans refactorings superflus. |
| **Opérateur Humain (Arbitre Souverain)** | Pilotage du cycle, arbitrage des suggestions de Claude, validation fonctionnelle et fusion des Pull Requests. | Décide des suggestions de Claude à retenir, teste l'UI et valide les approbations. |

---

## 2. Le Cycle de Développement en 10 Étapes

```
1. Issue avec ID PRD
       │
       ▼
2. Branche Git (feat/PRD-XXX-...)
       │
       ▼
3. Ticket atomique pour Gemini
       │
       ▼
4. Validation locale (bin/pre-claude-check.sh)
       │
       ▼
5. Commit Gemini isolé
       │
       ▼
6. Prompt de revue pour Claude (avec git diff)
       │
       ▼
7. Arbitrage humain des suggestions Claude
       │
       ▼
8. Relance CI locale (bin/pre-claude-check.sh)
       │
       ▼
9. Validation du flux UI dans Cortex
       │
       ▼
10. Ouverture de la Pull Request standardisée
```

---

## 3. Détail des 10 Étapes

### Étape 1 : Créer une issue avec un ID PRD
Chaque tâche est rattachée à un PRD ID obligatoire :
- `PRD-ARCH` : Architecture API-first, policies communes, journal d'audit.
- `PRD-CON` : Consignation et calculs de split propriétaires.
- `PRD-INV` : Inventaire, verrous atomiques et disponibilité.
- `PRD-TRX` : Transactions de location et facturation.
- `PRD-CLI` : Gestion des clients et onboarding.
- `PRD-RET` : Retours et check-in matériel.
- `PRD-AI` : Agents intelligents et façade MCP.
- `PRD-MIG` : Migration et normalisation legacy.
- `PRD-NFR` : Exigences non fonctionnelles, multi-tenancy, performance, FR/EN.

### Étape 2 : Créer une branche Git dédiée
```bash
git checkout -b feat/PRD-XXX-nom-de-la-tache
# Exemple: git checkout -b feat/PRD-CON-commission-calculation
```

### Étape 3 : Donner à Gemini un ticket atomique
Utiliser le template de ticket atomique (voir Section 5) en spécifiant le PRD ID, les fichiers autorisés et les tests attendus.

### Étape 4 : Exécuter la validation locale avant Claude
Lancer le script de vérification :
```bash
./bin/pre-claude-check.sh
```
Ce script exécute la suite complète :
```bash
git status
git diff --stat
git diff --check
php artisan test
./vendor/bin/pint --test
./vendor/bin/phpstan analyse
npm run lint
npm run build
```

### Étape 5 : Committer les changements Gemini séparément
```bash
git add .
git commit -m "feat(PRD-XXX): [Gemini] implémentation initiale du composant"
```

### Étape 6 : Transmettre à Claude le prompt de revue
Générer le diff Git et exécuter le prompt de revue Claude (voir Section 6).
```bash
# Obtenir le diff par rapport à la branche principale
git diff origin/main...HEAD > /tmp/cortex-gemini-diff.patch
```

### Étape 7 : Appliquer les corrections arbitrées
L'opérateur humain examine les points soulevés par Claude et applique les ajustements jugés pertinents.

### Étape 8 : Relancer toute la CI
```bash
./bin/pre-claude-check.sh
```
Tout doit être au vert (0 erreur Pint, 0 erreur PHPStan niveau 8+, 100% tests Pest passants, 0 erreur ESLint/Vite).

### Étape 9 : Tester le flux UI dans Cortex
- Exécuter les tests Livewire/Filament : `php artisan test --filter=RentalTransactionResourceTest`
- Vérifier manuellement le flux sur l'interface locale (`http://localhost:8080`).

### Étape 10 : Ouvrir la Pull Request
Remplir le template standardisé `.github/PULL_REQUEST_TEMPLATE.md`.

---

## 4. Script d'Automatisation : `bin/pre-claude-check.sh`

Le script est situé à la racine du dépôt dans `bin/pre-claude-check.sh` :
```bash
#!/usr/bin/env bash
set -e

echo "=== [1/8] Git Status & Diff Summary ==="
git status --short
git diff --stat

echo "=== [2/8] Git Whitespace & Conflict Check ==="
git diff --check

echo "=== [3/8] PHP Code Style (Laravel Pint) ==="
if [ -f "./apps/cortex-core/vendor/bin/pint" ]; then
    ./apps/cortex-core/vendor/bin/pint --test
elif [ -f "./vendor/bin/pint" ]; then
    ./vendor/bin/pint --test
fi

echo "=== [4/8] PHP Static Analysis (PHPStan) ==="
if [ -f "./apps/cortex-core/vendor/bin/phpstan" ]; then
    ./apps/cortex-core/vendor/bin/phpstan analyse
elif [ -f "./vendor/bin/phpstan" ]; then
    ./vendor/bin/phpstan analyse
fi

echo "=== [5/8] Backend Tests (Pest PHP) ==="
if [ -f "./apps/cortex-core/vendor/bin/pest" ]; then
    ./apps/cortex-core/vendor/bin/pest
elif [ -f "./vendor/bin/pest" ]; then
    ./vendor/bin/pest
elif command -v php &> /dev/null && [ -f "artisan" ]; then
    php artisan test
fi

echo "=== [6/8] Frontend Linting (ESLint / Biome) ==="
if [ -f "package.json" ]; then
    npm run lint --if-present
fi

echo "=== [7/8] Frontend & MCP Build Check ==="
if [ -f "package.json" ]; then
    npm run build --if-present
fi

echo "=== [8/8] Vérifications terminées avec succès ! Prêt pour la revue Claude. ==="
```

---

## 5. Template de Ticket Atomique pour Gemini

```markdown
### Ticket de Développement Gemini
- **ID PRD** : [ex: PRD-CON-001]
- **Titre** : [ex: Calcul de commission de consignation par numéro de série]
- **Fichiers autorisés** :
  - `plugins/Webkul/CortexRental/src/...`
  - `plugins/Webkul/CortexRental/tests/...`
- **Interdictions strictes** :
  - Ne pas modifier le core Aureus (`apps/cortex-core/app/...`).
  - Ne pas mettre de logique dans un Controller ou Resource Filament.
  - Ne pas omettre le scope `company_id`.
- **Livrables attendus** :
  1. Service métier transactionnel (`ConsignmentCalculationService`).
  2. Policy Laravel associée.
  3. Enregistrement de l'événement dans `audit_events`.
  4. Tests Pest unitaires et d'intégration avec couverture des cas d'erreur.
```

---

## 6. Template de Prompt de Revue pour Claude

```markdown
Tu es Claude, expert en architecture ERP critique, sécurité multi-tenant et revue de code Laravel/Filament.

Examine le diff Git ci-dessous produit par Gemini pour la tâche **[ID PRD] - [Titre de la tâche]**.

### Grille d'évaluation obligatoire :
1. **Multi-Tenancy & Isolation** : Vérifier que CHAQUE requête et relation est strictement scopée par `company_id`.
2. **Audit Append-Only** : Vérifier que TOUTE mutation produit un enregistrement immuable dans `audit_events` avec preuve et état avant/après.
3. **Séparation des Responsabilités** : Vérifier qu'aucune logique métier ne se trouve dans un Controller, une Filament Resource ou un Job.
4. **Transactions ACID** : Vérifier l'usage de `DB::transaction()` et le verrouillage pessimiste (`lockForUpdate()`) sur l'inventaire.
5. **Couverture de Tests** : Vérifier la présence de tests Pest testant les cas passants ET les cas de rejet de sécurité/policy.
6. **Pas de régression Aureus** : Vérifier que le core Aureus n'a pas été modifié.

### Diff Git Réel :
```diff
[INSERER LE DIFF GIT ICI]
```

### Format de réponse attendu :
- **Verdict global** : [APPROUVÉ / AJUSTEMENTS REQUIS / REJETÉ]
- **Points bloquants (Sécurité / Tenancy / ACID)** : liste concise avec fichier et numéro de ligne.
- **Améliorations suggérées** : corrections chirurgicales recommandées.
```

---

## 7. Template de Pull Request GitHub (`.github/PULL_REQUEST_TEMPLATE.md`)

```markdown
## Description & Contexte
**PRD ID** : `PRD-XXX`
**Issue liée** : #

## Contrats d'Architecture & Sécurité
- [ ] Multi-tenant : Tous les modèles et requêtes sont scopés par `company_id`.
- [ ] Audit : Toute mutation génère un événement `audit_events` append-only.
- [ ] Domaine : Toute la logique réside dans `plugins/Webkul/CortexRental` (zéro modif core Aureus).
- [ ] Transactions : Toutes les écritures utilisent `DB::transaction()` et des verrous adaptés.
- [ ] Policies : Les autorisations sont vérifiées via les Policies Laravel.

## Endpoints & Capacités Outils
- **Endpoints API** :
- **Outils MCP / Onyx** :

## Tests & Validation
- [ ] Tests Pest exécutés avec succès (`php artisan test`).
- [ ] Analyse statique PHPStan sans erreur (Niveau 8+).
- [ ] Formatage Pint validé (`./vendor/bin/pint --test`).
- [ ] Flux UI vérifié sur l'interface Filament (`localhost:8080`).

## Captures d'écran / Preuves d'exécution
*(Insérer captures UI Filament ou logs d'audit)*
```
