# Handoff — Cortex ERP AI-Native

**Date** : 2026-08-30
**Repo** : https://github.com/Endsi3g/cortex-erp-ai-native
**Branches** : [PR #1](https://github.com/Endsi3g/cortex-erp-ai-native/pull/1) (remédiation sécurité + décision Onyx) fusionné dans `main` — `main` est désormais la branche à jour. Travail en cours sur le frontend (cinquième vague, voir `CHANGELOG.md`) fait directement sur `main`.
**Détail complet** : `CHANGELOG.md` (quoi, pourquoi, preuves). Ce document est le point d'entrée opérationnel pour la suite — pas une redite du changelog.

---

## 1. État actuel en une phrase

Le code est corrigé et testé en mode mock (44 tests passent dans ce sandbox, sans Frappe réel). **Un vrai bench tourne désormais sur une seconde machine (la tour) côté utilisateur** — première preuve concrète que le déploiement fonctionne (capture d'écran de l'espace de travail `Users` par défaut) — mais ce sandbox n'y a pas d'accès direct (pas de SSH exposé) : voir §3 pour le mode de travail "relais" utilisé pour tout ce qui suit.

## 2. Ce qui bloque un vrai bench — et comment le débloquer

Tenté trois fois dans cette session, bloqué par l'environnement du sandbox à chaque fois, pas par le code :

1. **Tag Docker halluciné (corrigé)** : `infra/docker/Dockerfile.bench` référençait `frappe/bench:v15.0.0`, un tag qui n'a jamais existé sur Docker Hub. Corrigé vers `frappe/bench:latest` (commit `0aee7dc`) — vérifié contre la vraie liste de tags Docker Hub.
2. **Disque plein** : le pull MariaDB+Valkey seul a rempli le disque du sandbox à 99%, faisant planter Docker Desktop. Nettoyé une première fois (remonté à 9,6 Go libres), mais **le disque a continué à se vider tout seul ensuite (9,6 → 5,6 Go en quelques minutes, sans qu'aucun pull ne soit en cours)** — signe d'une pression disque générale sur cette machine sandbox, pas seulement liée à mes actions.
3. **Docker Desktop ne s'est pas relancé correctement** : après le premier crash, `docker info` ne répondait plus. J'ai tenté un `quit`+`relaunch` (`osascript`/`open -a "Docker Desktop"`) : l'app GUI principale ne s'est pas relancée (aucun process `Docker Desktop.app/.../Docker Desktop` visible ensuite), seuls des process backend orphelins (`com.docker.backend`, `docker-agent`, `vmnetd`) sont restés actifs, sans coordinateur — `docker info` restait indéfiniment bloqué. Je n'ai pas insisté avec des mesures plus agressives (kill forcé des process backend, relance répétée) sur une machine dont je ne contrôle pas l'état complet.

**Action requise côté humain avant de retenter** : relancer Docker Desktop manuellement (double-clic sur l'app, ou `killall Docker Desktop` puis relancer depuis le Launchpad) et vérifier `docker info` répond, **et** libérer plus d'espace disque que ce que voit ce sandbox (idéalement 20+ Go, sur une machine qui n'a pas cette fuite/pression disque inexpliquée). Une fois ces deux points confirmés sains, la séquence ci-dessous reste valide.

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

## 3. Frontend — premier écran réel (Workspace + Disponibilité) : commandes pour la tour

Mode de travail confirmé avec l'utilisateur : ce sandbox n'a pas d'accès
réseau direct à la tour (pas de SSH exposé) — je prépare le code ici,
push sur `main`, et **c'est à toi (ou à moi via les commandes que tu
colles avec le préfixe `!`) de les exécuter sur la tour**, puis de me
rapporter la sortie/les erreurs pour que j'itère.

Ajouté dans cette passe (voir `CHANGELOG.md`, cinquième vague, pour le
détail complet) :
- `cortex_rental/api/v1/availability.py::get_matrix` — nouvel endpoint
  humain (pas d'outil MCP) pour la grille de disponibilité.
- `cortex_rental/cortex_rental/page/cortex_availability/` — Page Frappe
  native `/app/cortex-availability`.
- `cortex_rental/public/js/cortex_availability/` — Vue 3 (sans
  `frappe-ui` pour l'instant, voir raison dans le changelog).
- `cortex_rental/cortex_rental/workspace/cortex-rental/` — le Workspace
  `Cortex Rental`, ne pointe que vers ce qui existe réellement.

**Sur la tour, une fois `git pull` fait sur `main`** :

```bash
cd ~/frappe-bench   # ou le chemin réel du bench sur la tour
git -C apps/cortex_rental pull origin main   # si cortex_rental est son propre clone/submodule
# sinon, si le bench pointe directement sur ce repo monorepo :
# cd /chemin/vers/Cortex-ERP-AI-Native && git pull origin main

bench --site <ton-site> migrate      # sync la nouvelle Page + le nouveau Workspace + le nouveau champ/API
bench build --app cortex_rental      # compile cortex_availability.bundle.js
bench restart                        # ou redémarre le process bench start / supervisor selon ton setup
```

Puis dans le navigateur : recharger `/app`, le Workspace **Cortex
Rental** doit apparaître dans la barre latérale native (celle-là même
visible dans ta capture d'écran), et son raccourci "Disponibilité" doit
ouvrir `/app/cortex-availability`.

**Ce que j'ai besoin que tu me rapportes** (capture ou texte, peu
importe — mais idéalement le texte exact des erreurs si `bench migrate`
ou `bench build` échoue) :
1. Le Workspace apparaît-il dans la sidebar ?
2. La page Disponibilité s'ouvre-t-elle sans erreur JS (F12 → Console) ?
3. Y a-t-il des équipements réels (`Cortex Rental Item Profile`) et des
   transactions dans ce site pour que la grille affiche quelque chose,
   ou est-ce vide parce qu'il n'y a pas encore de données de démo sur
   cette instance ? Si c'est vide faute de données, dis-le-moi — je peux
   préparer un jeu de données de démo (fixtures) pour rendre l'écran
   visuellement dense dès le premier chargement.
4. Toute erreur Python (traceback) si `get_matrix` échoue côté serveur.

Non vérifié dans cette passe (pas de bench accessible ici pour le
tester moi-même) : que `import { createApp } from "vue"` se résout bien
dans le pipeline `bench build` de cette instance précise — le pattern
est documenté et vérifié contre `docs.frappe.io`, mais chaque bench a sa
propre configuration Node/esbuild. Si `bench build` échoue sur cet
import spécifiquement, c'est la première chose à me rapporter.

## 4. Onyx — décision actée et implémentée : self-hosted + widget intégré

**Décision (2026-08-30)** : Onyx est déployé **self-hosted** (pas Onyx
Cloud), Gemini configuré comme fournisseur LLM par défaut, et le chat
est intégré visuellement dans Cortex via le widget officiel. Détail
complet, config requise et limites connues : `infra/onyx/README.md`.

- **Le backend Onyx tourne comme service séparé**, self-hosted (leur propre `docker-compose.yml`/installeur officiel, pas vendorisé dans ce repo — trop de pièces mobiles, `relational_db`/`index`/`opensearch`/`cache`/`inference_model_server`/`minio` qui leur sont propres). Aucun moyen de le faire tourner "dans" le process Frappe/Cortex — confirme le PRD ("Onyx Standard : service indépendant").
- **Widget intégré** : `apps/cortex_rental/cortex_rental/www/onyx-assistant.html` (+ `.py`) rend `<onyx-chat-widget>` (web component léger, Shadow DOM — pas de conflit CSS avec Frappe Desk), accessible à `/onyx-assistant` pour tout utilisateur authentifié. Config via `site_config.json` (`onyx_backend_url`, `onyx_widget_api_key`, `onyx_widget_script_url`) — jamais committée.
- **Non vérifié** : le chemin exact du bundle JS du widget sur un déploiement self-hosted (la doc publique ne montre que l'exemple cloud). La page a un défaut raisonnable mais surchargeable — à confirmer contre un vrai déploiement.
- **Gemini par défaut** : configuré dans le panneau admin Onyx (Settings → LLM Providers), pas via une variable d'environnement — je n'ai trouvé aucun nom de variable fiable pour l'automatiser sans risquer d'inventer une config inexistante. Étapes manuelles documentées dans `infra/onyx/README.md` §3.
- **Sécurité inchangée** : que le widget soit embarqué ou qu'on ouvre Onyx séparément, tout appel d'outil agent réel passe toujours par Onyx backend → Cortex MCP → API Frappe whitelisted, avec les mêmes vérifications de scope/tenant/state-machine déjà corrigées dans ce repo. Le widget est une question d'UX, pas de sécurité.
- **Toujours pas fait** : la clé `onyx_widget_api_key` doit être une clé Onyx à portée **limitée (chat uniquement)** — sa création dépend du panneau admin Onyx une fois déployé, donc pas testable dans ce sandbox.

Sources : [Website Widget — Onyx Documentation](https://docs.onyx.app/deployment/configuration/website_widget), [onyx/widget/README.md](https://github.com/onyx-dot-app/onyx/blob/main/widget/README.md), [onyx-dot-app/onyx docker-compose](https://github.com/onyx-dot-app/onyx/blob/main/deployment/docker_compose/docker-compose.yml)

## 5. Clé Gemini utilisée dans cette session

Une vraie clé `GEMINI_API_KEY` a été collée en clair dans le chat par l'utilisateur pour tester le prompt Onyx (voir `docs/evals/2026-08-30-onyx-intake-gemini-3.7-flash.md`). Elle a été écrite dans `apps/cortex-mcp/.env` (gitignored, jamais commitée) mais **elle a transité par la conversation** — recommandation : la faire tourner (révoquer + régénérer côté Google AI Studio) avant tout usage en dehors de ce test ponctuel.

## 6. Ce qui reste ouvert (par priorité probable)

| Item | Pourquoi ce n'est pas fait | Effort estimé |
|---|---|---|
| **Confirmer que la page Disponibilité s'ouvre réellement sur la tour** | Écrit et testé en unitaire ici, jamais ouvert dans un navigateur — voir §3 pour les commandes et ce qu'il faut me rapporter | Quelques minutes une fois `bench build` fait |
| Jeu de données de démo (fixtures) pour que la grille Disponibilité soit dense dès le premier chargement | Pas demandé explicitement pour cette passe ; à faire si la tour n'a pas encore de `Cortex Rental Item Profile`/transactions réels | 0.5 jour |
| Écrans Composer de transaction / Check-in / Approbations / Assistant | Portée de cette passe volontairement limitée à Workspace + Disponibilité (choix confirmé avec l'utilisateur) | Composer : 1-2 jours, Check-in : 1 jour, Approbations : 1 jour, Assistant : dépend d'Onyx (§4) |
| Adopter `frappe-ui` (composants) sur les prochains écrans | Un problème connu (issue GitHub ouverte sur `doppio`) casse le build esbuild quand `frappe-ui` est importé dans ce pattern de Desk Page ; pas de bench ici pour le reproduire/déboguer | À réévaluer une fois §3 confirmé fonctionnel |
| Validation sur bench réel (isolation tenant, concurrence, télémétrie agent, check-in) | Bloqué par l'environnement sandbox, pas le code — voir §2. Un bench existe maintenant sur la tour (§3), donc ces suites (`test_multitenant_isolation.py` etc., listées en §2) peuvent enfin tourner pour de vrai — à lancer | Quelques heures sur la tour |
| Upload Intent (S3/MinIO pré-signé) | Aucun endpoint d'upload n'existe dans ce repo pour partir de quelque chose ; feature d'infra à part entière | 1-2 jours |
| Scan antivirus (ClamAV) | Le champ `scanned_clean` existe et bloque déjà l'usage, mais rien ne le positionne automatiquement | 0.5-1 jour (intégration ClamAV) |
| Vérifier `onyx_widget_script_url` contre un vrai déploiement self-hosted | Page/décision implémentées (§3), mais le chemin exact du bundle JS n'est pas confirmé — supposition raisonnable non testée | 15 min une fois Onyx déployé |
| `docs/07-frappe-erpnext-implementation-guide.md` | Documente une conception antérieure obsolète ; juste flaggé, pas réécrit | 0.5-1 jour |
| Décision 1 site/client vs multi-Company partagé | Phase 1 a rendu le modèle partagé sûr, mais la recommandation initiale (1 site = 1 client pour le pilote) reste le choix le plus prudent | Décision, pas du code |
| **PRD-ARCH-AUD-001** — durcir l'immutabilité de `Cortex Audit Event` au-delà de `before_save`/`on_trash` | Ces hooks protègent le chemin DocType normal, pas `frappe.db.set_value()`/`frappe.db.sql()` direct, la console bench, ni un accès `System Manager`. Retirer write/delete de tous les rôles applicatifs, bloquer les routes génériques pour ce DocType, journaliser les exports, tester les chemins de contournement, définir un accès break-glass documenté, définir archivage/rétention | 1-2 jours + tests sur bench réel |
| Lien `Cortex Rental Transaction` → `Sales Invoice`/`Payment Entry` ERPNext | `Closed` est un état opérationnel sans lien vers la facture réelle aujourd'hui — pas de champ `erpnext_sales_invoice` | 0.5-1 jour |
| `docs/tenant-isolation.md`, `docs/agent-permission-matrix.md` | Suggérés par la revue README — pas créés dans cette passe pour ne pas gonfler le scope au-delà de ce qui était demandé (corriger le README) ; le contenu existe déjà dispersé dans `agent_scopes.py`, `permissions/__init__.py` et ce handoff | 0.5 jour pour les consolider |

## 7. Comment reprendre ce travail

1. Lire `CHANGELOG.md` pour le détail complet de chaque correctif (cinq vagues, un ou plusieurs commits par sujet).
2. Lire les 4 ADR dans `docs/adr/` pour les décisions d'architecture actées.
3. `./bin/pre-claude-check.sh` doit passer avant tout nouveau commit (lint, format, tests, schémas DocType).
4. Suivre §3 pour valider la Page/Workspace Disponibilité sur la tour, puis §2 pour le premier vrai `bench run-tests` complet (isolation tenant, concurrence, télémétrie agent, check-in).
5. La CI GitHub Actions tourne sur chaque push vers `test/**`/`feat/**`/`fix/**`/`main` — tous les runs de cette session sont verts : https://github.com/Endsi3g/cortex-erp-ai-native/actions
