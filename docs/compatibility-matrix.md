# Matrice de compatibilité

Valeurs tirées directement des fichiers de config du dépôt à la date
ci-dessous — rien d'inventé. Là où une version n'est pas réellement
épinglée dans le code, c'est marqué explicitement plutôt que deviné.

**Dernière vérification** : 2026-08-30, contre `infra/docker/docker-compose.dev.yml`,
`infra/docker/Dockerfile.bench`, `apps/cortex_rental/pyproject.toml`,
`apps/cortex-mcp/pyproject.toml`, `apps/cortex-mcp/Dockerfile`,
`.github/workflows/ci.yml`.

| Composant | Version épinglée dans ce dépôt | Source | Politique upgrade |
|---|---|---|---|
| Frappe Framework | **Non épinglée** — `bench init --frappe-branch version-15` sélectionne la branche `version-15`, pas un patch précis | `HANDOFF.md` §2 (séquence non testée) | À définir une fois un premier bench réel exécuté |
| ERPNext | **Non épinglée** — `bench get-app erpnext --branch version-15`, même remarque | idem | idem |
| Python (`cortex_rental`) | `>=3.10` (pas de plafond) | `apps/cortex_rental/pyproject.toml` | — |
| Python (`cortex-mcp`) | `>=3.10` en pyproject, mais **image Docker `python:3.12-slim`** et `ruff target-version = py311` — trois références non alignées, pas une incohérence bloquante (3.12 satisfait `>=3.10`) mais à clarifier | `apps/cortex-mcp/pyproject.toml`, `Dockerfile`, `docker-compose.dev.yml` | Choisir une seule version cible et l'aligner partout |
| Python (CI / dev local) | `3.11` | `.github/workflows/ci.yml`, `ruff.toml` (`target-version = py310`, donc CI plus stricte que la cible ruff) | — |
| MariaDB | `10.11` | `infra/docker/docker-compose.dev.yml` | Patches sécurité |
| Valkey (Redis-compatible) | `8.0.2-alpine` | `infra/docker/docker-compose.dev.yml` | Patches sécurité, testée par `services/locking.py` en usage réel |
| MinIO | `RELEASE.2025-02-18T16-25-55Z` | `infra/docker/docker-compose.dev.yml` | — |
| Mailpit | `v1.22.4` | `infra/docker/docker-compose.dev.yml` | — |
| `frappe/bench` (image CLI) | `latest` (corrigé depuis `v15.0.0`, qui n'a jamais existé sur Docker Hub) | `infra/docker/Dockerfile.bench` | Envisager d'épingler un digest une fois le premier bench validé, pour la reproductibilité |
| FastMCP (`mcp` package) | `>=1.0.0` (pas de plafond) | `apps/cortex-mcp/pyproject.toml` | — |
| Onyx | **Non épinglée** — décision self-hosted actée (`infra/onyx/README.md`), mais aucun tag/version précis choisi | `infra/onyx/README.md` | À fixer avant tout déploiement staging |
| Gemini | `gemini-3.7-flash` confirmé exister via `GET /v1beta/models` et testé réellement (`docs/evals/`) | `.env.example` (`DEFAULT_MODEL`) | Modèle réévalué régulièrement par le fournisseur (Google) — surveiller les dépréciations |
| Node.js / Yarn/pnpm | **Non spécifiés dans ce dépôt** — nécessaires pour builder les assets Frappe/ERPNext, mais aucune version n'est fixée nulle part | — | À définir au premier build de bench réel |

## Pourquoi ce document existe

Le README affichait des badges génériques (« ERPNext v15+ », « MariaDB
10.11+ ») qui suggéraient une matrice de compatibilité validée. Ce
n'est pas encore le cas pour Frappe/ERPNext/Node — seuls MariaDB,
Valkey, MinIO et Mailpit sont réellement épinglés par version exacte
dans `docker-compose.dev.yml`. Ce document distingue les deux plutôt
que de laisser le README impliquer une précision qui n'existe pas.
