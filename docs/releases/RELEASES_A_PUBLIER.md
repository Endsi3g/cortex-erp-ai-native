# Versions à publier sur GitHub (v0.8.0 à v0.15.x)

Les versions ont été préparées une par phase, chacune dans son commit (branche `claude/handoff-phases`, PR #14).
**Les étiquettes (tags) et les « Releases » GitHub n'ont pas pu être créées depuis l'environnement de travail** (le dépôt
refuse les poussées d'étiquettes et l'outil GitHub disponible ne sait que lire les releases). Pour publier, après fusion
(ou directement sur ces commits) :

```bash
git tag -a v0.8.0 8b10e9a -m "v0.8.0 — Phases 1 et 2"
git tag -a v0.9.0 32517cf -m "v0.9.0 — Phase 3"
git tag -a v0.10.0 2d9de3d -m "v0.10.0 — Phase 4"
git tag -a v0.11.0 4bb4c4b -m "v0.11.0 — Phase 5"
git tag -a v0.12.0 9b5826c -m "v0.12.0 — Phase 6"
git tag -a v0.13.0 85a09c8 -m "v0.13.0 — Phase 7"   # 85a09c8 = a38e207 + correction du test de secrets (suite verte)
git tag -a v0.14.0 <tête de la branche> -m "v0.14.0 — Phase 8"
git push origin --tags
```

Puis créer une Release par étiquette avec le texte de la section correspondante de `CHANGELOG.md`.

Remarques :
- La `v0.7.0` du CHANGELOG (commit `a78e686`) n'a jamais été publiée : le dernier tag GitHub est `v0.6.0`.
- Si la PR est fusionnée par « squash », les tags ci-dessus resteront sur les commits de la branche, pas sur `main` : préférer une fusion
  classique ou étiqueter après fusion.
- Rien de ceci n'est « mis en production » : voir les limites de chaque phase dans `docs/frontend/CORTEX_UI_HANDOFF_V2.md`.
