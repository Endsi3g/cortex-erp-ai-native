# Handoff — Cortex ERP AI-Native

**Date** : 2026-08-30
**Repo** : https://github.com/Endsi3g/cortex-erp-ai-native
**Branches** : `main` (baseline scaffold Gemini, commit `9b86a84`) ← `test/PRD-demo-scenario` (13 commits de remédiation Claude) via [PR #1](https://github.com/Endsi3g/cortex-erp-ai-native/pull/1)
**Détail complet** : `CHANGELOG.md` (quoi, pourquoi, preuves). Ce document est le point d'entrée opérationnel pour la suite — pas une redite du changelog.

---

## 1. État actuel en une phrase

Le code est corrigé et testé en mode mock (23-35 tests passent selon la branche, sans Frappe réel) ; **rien n'a encore tourné contre un vrai bench Frappe/MariaDB**. C'est le principal risque restant avant tout pilote.

## 2. Ce qui bloque un vrai bench — et comment le débloquer

Tenté deux fois dans cette session, bloqué par l'environnement du sandbox, pas par le code :

1. **Tag Docker halluciné (corrigé)** : `infra/docker/Dockerfile.bench` référençait `frappe/bench:v15.0.0`, un tag qui n'a jamais existé sur Docker Hub. Corrigé vers `frappe/bench:latest` (commit `0aee7dc`) — vérifié contre la vraie liste de tags Docker Hub.
2. **Disque plein** : le pull MariaDB+Valkey seul a rempli le disque du sandbox à 99%, faisant planter Docker Desktop. Nettoyé, mais le disque est resté trop juste (6-9 Go libres) pour un bench complet (frappe + erpnext + node_modules + venv demandent facilement plusieurs Go).
3. **Docker Desktop instable après le crash** : au moment d'écrire ceci, `docker info` ne répond même plus après 20s.

**Pour la suite, sur une machine avec plus de ressources (recommandé : 20+ Go libres, Docker Desktop sain) :**

```bash
cd infra/docker
docker compose -f docker-compose.dev.yml up -d mariadb valkey
docker compose -f docker-compose.dev.yml build bench   # utilise maintenant frappe/bench:latest, corrigé
docker compose -f docker-compose.dev.yml run --rm bench bash
# Dans le conteneur :
bench init --frappe-branch version-15 --skip-assets /home/frappe/frappe-bench
cd /home/frappe/frappe-bench
bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://valkey:6379/0
bench set-config -g redis_queue redis://valkey:6379/1
bench get-app erpnext --branch version-15
# cortex_rental est déjà monté dans apps/cortex_rental (volume docker-compose.dev.yml)
bench new-site cortex.localhost --db-host mariadb --admin-password admin
bench --site cortex.localhost install-app erpnext
bench --site cortex.localhost install-app cortex_rental
bench --site cortex.localhost run-tests --app cortex_rental
```

Aucune de ces commandes n'a été exécutée réellement — c'est la séquence logique dérivée de la structure du `docker-compose.dev.yml` et des noms de service Frappe standards, **pas une transcription d'un run réussi**. À valider pas à pas, en particulier `bench get-app erpnext` (gros clone git, peut être lent) et l'enregistrement de `cortex_rental` comme app locale (le volume le place déjà au bon endroit, mais `sites/apps.txt` doit le lister — vérifier après `bench new-site`).

Une fois ça tourne, exécuter en priorité les tests gated-Frappe déjà écrits et prêts (actuellement `skipped` partout ailleurs) :
- `test_multitenant_isolation.py` — preuve que l'isolation tenant tient réellement
- `test_availability_concurrency.py` — quarantaine, non-sérialisé, double-réservation concurrente
- `test_agent_telemetry_live.py` — Cortex Agent Run/Tool Call
- `test_checkin_live.py` — retour partiel vs complet, mise à jour Serial No

## 3. Onyx — déploiement séparé obligatoire, mais les écrans peuvent s'intégrer

Vérifié contre la doc Onyx réelle (docs.onyx.app, repo GitHub onyx-dot-app/onyx) :

- **Le backend Onyx doit tourner comme service séparé**, self-hosted (Docker/Kubernetes/Terraform, son propre docker-compose) ou Onyx Cloud. Il n'y a aucun moyen de le faire tourner "dans" le process Frappe/Cortex — confirme ce que dit déjà le PRD ("Onyx Standard : service indépendant").
- **Mais l'écran de chat peut s'intégrer visuellement dans Cortex** via le widget officiel : un web component léger (~100-150 Ko gzippé, Lit + Shadow DOM, donc pas de conflit CSS avec Frappe Desk) :
  ```html
  <script type="module" src=".../onyx-widget.js"></script>
  <onyx-chat-widget backend-url="https://onyx.<votredomaine>" api-key="..."></onyx-chat-widget>
  ```
  Le `api-key` doit être une clé à portée limitée (chat uniquement) — la doc Onyx prévient explicitement qu'elle est visible côté client.
- **Comment l'intégrer dans Cortex concrètement** : ajouter le script/tag dans une page Frappe UI/Vue dédiée (pas dans `app_include_js` global de `hooks.py`, pour ne pas charger le widget sur tous les écrans Desk) — ou dans une Workspace/Page personnalisée. Reste à faire, pas commencé dans cette session.
- **Important — ça ne change rien à la sécurité déjà en place** : que le widget soit embarqué ou qu'on ouvre Onyx dans un onglet séparé, le vrai appel d'outil agent passe toujours par Onyx backend → Cortex MCP → API Frappe whitelisted, avec les mêmes vérifications de scope/tenant/state-machine déjà corrigées dans ce repo. Le widget est une question d'UX, pas de sécurité.

Sources : [Website Widget — Onyx Documentation](https://docs.onyx.app/deployment/configuration/website_widget), [onyx/widget/README.md](https://github.com/onyx-dot-app/onyx/blob/main/widget/README.md)

## 4. Clé Gemini utilisée dans cette session

Une vraie clé `GEMINI_API_KEY` a été collée en clair dans le chat par l'utilisateur pour tester le prompt Onyx (voir `docs/evals/2026-08-30-onyx-intake-gemini-3.7-flash.md`). Elle a été écrite dans `apps/cortex-mcp/.env` (gitignored, jamais commitée) mais **elle a transité par la conversation** — recommandation : la faire tourner (révoquer + régénérer côté Google AI Studio) avant tout usage en dehors de ce test ponctuel.

## 5. Ce qui reste ouvert (par priorité probable)

| Item | Pourquoi ce n'est pas fait | Effort estimé |
|---|---|---|
| Validation sur bench réel | Bloqué par l'environnement sandbox, pas le code — voir §2 | Quelques heures sur une machine correcte |
| Upload Intent (S3/MinIO pré-signé) | Aucun endpoint d'upload n'existe dans ce repo pour partir de quelque chose ; feature d'infra à part entière | 1-2 jours |
| Scan antivirus (ClamAV) | Le champ `scanned_clean` existe et bloque déjà l'usage, mais rien ne le positionne automatiquement | 0.5-1 jour (intégration ClamAV) |
| Widget Onyx dans Cortex Desk | Voir §3 — pas commencé | 0.5 jour |
| `docs/07-frappe-erpnext-implementation-guide.md` | Documente une conception antérieure obsolète ; juste flaggé, pas réécrit | 0.5-1 jour |
| Décision 1 site/client vs multi-Company partagé | Phase 1 a rendu le modèle partagé sûr, mais la recommandation initiale (1 site = 1 client pour le pilote) reste le choix le plus prudent | Décision, pas du code |

## 6. Comment reprendre ce travail

1. Lire `CHANGELOG.md` pour le détail complet de chaque correctif (14 commits, un par sujet).
2. Lire les 4 ADR dans `docs/adr/` pour les décisions d'architecture actées.
3. `./bin/pre-claude-check.sh` doit passer avant tout nouveau commit (lint, format, tests, schémas DocType).
4. Suivre §2 ci-dessus pour le premier vrai `bench run-tests`.
5. La CI GitHub Actions tourne sur chaque push vers `test/**`/`feat/**`/`fix/**`/`main` — tous les runs de cette session sont verts : https://github.com/Endsi3g/cortex-erp-ai-native/actions
