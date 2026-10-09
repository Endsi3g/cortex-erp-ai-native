# Releases et historique de publication

## v0.15.2 — 2026-10-09

Release ERPNext native : profil Mon compte réorganisé, grille Disponibilité reliée au Catalogue de la société et état vide avec action contextuelle, contrôle de repli de la navigation remonté et masquage visuel de la scrollbar, isolation des sessions IA par propriétaire et société. La grille est limitée à 200 profils. Vérifications : 576 tests réussis, 15 ignorés; Ruff, Node et build Frappe réussis. Pas de validation Stripe/IA avec des clés réelles ni de déploiement production.

L'état actuel de publication de v0.15.2 se vérifie dans GitHub; le tableau qui suit conserve le plan historique v0.8.0–v0.15.1.

## Plan historique — versions antérieures (v0.8.0 à v0.15.1)

Les versions ont été préparées une par phase, chacune dans son commit (branche `claude/handoff-phases`, PR #14).
**À l'époque, les étiquettes (tags) et les « Releases » GitHub n'avaient pas pu être créées depuis l'environnement de travail** (le dépôt
refuse les poussées d'étiquettes et l'outil GitHub disponible ne sait que lire les releases). Pour publier, après fusion
(ou directement sur ces commits) :

```bash
git tag -a v0.8.0 8b10e9a -m "v0.8.0 — Phases 1 et 2"
git tag -a v0.9.0 32517cf -m "v0.9.0 — Phase 3"
git tag -a v0.10.0 2d9de3d -m "v0.10.0 — Phase 4"
git tag -a v0.11.0 4bb4c4b -m "v0.11.0 — Phase 5"
git tag -a v0.12.0 9b5826c -m "v0.12.0 — Phase 6"
git tag -a v0.13.0 85a09c8 -m "v0.13.0 — Phase 7"   # 85a09c8 = a38e207 + correction du test de secrets (suite verte)
git tag -a v0.14.0 <commit « Phase 8 » de la branche> -m "v0.14.0 — Phase 8"
git tag -a v0.15.0 d9a9026 -m "v0.15.0 — Phase 9 (première partie)"   # local : à vérifier avec `git log` si le SHA a changé
git tag -a v0.15.1 <tête de la branche> -m "v0.15.1 — Phase 9.6 et 9.7"
git push origin --tags
```

Puis créer une Release par étiquette avec le texte de la section correspondante de `CHANGELOG.md`.

Remarques :
- La `v0.7.0` du CHANGELOG (commit `a78e686`) n'a jamais été publiée : le dernier tag GitHub est `v0.6.0`.
- Si la PR est fusionnée par « squash », les tags ci-dessus resteront sur les commits de la branche, pas sur `main` : préférer une fusion
  classique ou étiqueter après fusion.
- Rien de ceci n'est « mis en production » : voir les limites de chaque phase dans `docs/frontend/CORTEX_UI_HANDOFF_V2.md`.
