# Règle Projet Permanente : Workflow Gemini → Claude

Cette règle définit le protocole opérationnel obligatoire à appliquer pour tout développement, refactoring, correction de bug ou ajout de fonctionnalité sur **Cortex ERP AI-Native**.

---

## 1. Principes Fondateurs

1. **Gemini (Génération & Implémentation Atomique)** : Produit le code, les migrations, les services de domaine, les tests Pest et les composants Filament de manière rapide, typée et bornée.
2. **Claude (Revue Stricte, Arbitrage & Sécurité)** : Analyse le diff Git réel, vérifie l'absence de régression multi-tenant (`company_id`), l'audit append-only, la conformité ACID et la solidité des Policies.
3. **Humain (Arbitrage Souverain)** : L'opérateur valide et arbitre les retours de Claude au cas par cas avant de finaliser la branche.

---

## 2. Le Workflow en 10 Étapes Obligatoires

```
1. Issue (PRD ID) ──> 2. Branche (feat/PRD-XXX-desc) ──> 3. Ticket Gemini
                                                                 │
                                                                 ▼
6. Revue Claude <── 5. Commit Gemini <── 4. bin/pre-claude-check.sh
      │
      ▼
7. Arbitrage Humain ──> 8. Relance CI ──> 9. Test UI Cortex ──> 10. Pull Request
```

### Étape 1 — Créer une issue avec un ID PRD
Chaque tâche doit être rattachée à l'un des PRD IDs officiels :
- `PRD-ARCH` : API-first, policies communes, journal d'audit append-only.
- `PRD-CON` : Consignation et calcul de commission par numéro de série.
- `PRD-INV` : Inventaire, verrous et disponibilité calendaire.
- `PRD-TRX` : Transactions de location et facturation.
- `PRD-CLI` : Gestion des clients et ouverture de compte.
- `PRD-RET` : Retours d'équipements et check-in.
- `PRD-AI` : Agents intelligents, actions et intégrations Onyx/MCP.
- `PRD-MIG` : Scripts de migration et normalisation legacy.
- `PRD-NFR` : Exigences non fonctionnelles, multi-tenancy, performance, i18n FR/EN.

### Étape 2 — Créer une branche Git dédiée
Format de nommage obligatoire :
```bash
git checkout -b feat/PRD-XXX-description-courte
# ou fix/PRD-XXX-description-courte
```

### Étape 3 — Donner à Gemini un ticket atomique
Fournir à Gemini le contexte borné, le PRD ID, les fichiers autorisés et les contraintes non négociables.

### Étape 4 — Exécuter la suite de validation locale
Lancer le script de vérification :
```bash
./bin/pre-claude-check.sh
```
Ce script exécute successivement :
1. `git status`
2. `git diff --stat`
3. `git diff --check`
4. `php artisan test` (Pest)
5. `./vendor/bin/pint --test`
6. `./vendor/bin/phpstan analyse`
7. `npm run lint`
8. `npm run build`

### Étape 5 — Committer les changements Gemini
```bash
git add .
git commit -m "feat(PRD-XXX): [Gemini] description de l'implémentation initiale"
```

### Étape 6 — Transmettre à Claude pour revue
Fournir à Claude le prompt de revue standardisé avec le diff Git réel (`git diff origin/main...HEAD` ou `git diff HEAD~1`).

### Étape 7 — Appliquer les corrections validées par l'Humain
L'opérateur humain arbitre souverainement les retours de Claude et applique les ajustements requis.

### Étape 8 — Relancer toute la CI locale
```bash
./bin/pre-claude-check.sh
```

### Étape 9 — Tester le flux UI dans Cortex
- Exécuter les tests de composants Filament/Livewire (`Livewire::test(...)`).
- Vérifier manuellement le rendu et le parcours utilisateur dans le panel Filament (`localhost:8080`).

### Étape 10 — Ouvrir la Pull Request
Remplir obligatoirement le template `.github/PULL_REQUEST_TEMPLATE.md` avec :
- PRD ID et lien de l'issue
- Endpoints API créés/modifiés
- Policies Laravel appliquées
- Événements `audit_events` enregistrés
- Résultats des tests Pest
- Checklist de sécurité multi-tenant
