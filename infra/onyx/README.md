# Onyx — déploiement self-hosted

> Déploiement local réellement installé et validé (Onyx Lite + Ollama `qwen3:8b`) : [`LOCAL_DEV.md`](LOCAL_DEV.md). Contrat produit/frontend commun : [`../../docs/frontend/CORTEX_UI_HANDOFF_V2.md`](../../docs/frontend/CORTEX_UI_HANDOFF_V2.md).

**Décision (2026-08-30)** : Onyx est déployé **self-hosted**, en service
séparé de Cortex — jamais dans le process Frappe/bench. C'est une
exigence de leur propre architecture (backend + Postgres/OpenSearch/
Redis/MinIO/inference model server), pas seulement une préférence
Cortex. Voir `CHANGELOG.md` et `HANDOFF.md` §3 pour le contexte complet.

Ce document ne vendorise pas leur `docker-compose.yml` (trop de pièces
mobiles pour le maintenir en synchro à la main ici, et risque de dérive
vs. leurs mises à jour) — il documente comment déployer via leurs
outils officiels et comment connecter le résultat à Cortex.

## 1. Déployer Onyx

Utiliser l'installeur officiel (vérifié contre la doc réelle
docs.onyx.app, pas deviné) :

```bash
curl -fsSL https://raw.githubusercontent.com/onyx-dot-app/onyx/main/deployment/docker_compose/install.sh > install.sh
chmod +x install.sh
./install.sh
```

Ou directement via leur `docker-compose.yml`
(`deployment/docker_compose/` dans
[onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx)) si un contrôle
plus fin est nécessaire. Services principaux (d'après leur repo) :
`relational_db`, `index`, `opensearch`, `cache`, `inference_model_server`,
`minio` — c'est leur pile complète, indépendante de MariaDB/Valkey/MinIO
de Cortex (`infra/docker/docker-compose.dev.yml`). Ne pas les fusionner.

## 2. Connecter Onyx à Cortex

Onyx (agents) parle à Cortex exclusivement via **Cortex MCP**
(`apps/cortex-mcp`), jamais en direct à Frappe/MariaDB :

```
Onyx (self-hosted, réseau séparé)
    │  HTTPS
    ▼
Cortex MCP (apps/cortex-mcp) — Streamable HTTP en prod
    │
    ▼
API métier Frappe whitelisted (/api/method/cortex_rental.api.v1.*)
```

- En dev local, exposer le port `apps/cortex-mcp` (`PORT=3100` par
  défaut, voir `apps/cortex-mcp/.env.example`) sur un réseau Docker
  accessible depuis le déploiement Onyx (réseau `internal` de
  `docker-compose.dev.yml`, ou un réseau `external:` partagé si Onyx
  tourne dans sa propre stack Docker).
- En production, MCP est privé (`mcp.cortex.internal` ou équivalent,
  jamais exposé publiquement) — Onyx doit l'atteindre via un réseau
  privé/VPN, pas Internet public. Voir la topologie complète dans le
  system prompt racine (`docs/02-onyx-mcp-frappe-integration.md`).

## 3. Fournisseur local Ollama

Le modèle local retenu est `qwen3:8b` : 8,2B paramètres, quantification
Q4_K_M, environ 5,2 Go de poids, 40K de contexte annoncé et capacités outils.
Le candidat vision `qwen3.5:9b` a été essayé puis retiré : l'appel d'outil
court a pris 2 min 45 s sur le CPU seul visible dans cet environnement.
Onyx Lite reste dans le budget Docker local; l'indexation complète et les
connecteurs sont désactivés. Commence à 16K de contexte effectif pour
préserver la mémoire pendant que Cortex et Onyx tournent ensemble.

L'ajout du fournisseur et le choix du modèle se font dans le panneau admin
Onyx → **Configuration → Language Models**. Pour les détails vérifiés sur
cette machine, les étapes initiales et les limites, voir [`LOCAL_DEV.md`](LOCAL_DEV.md).
Ne configure pas une clé Ollama fictive et ne publie jamais le jeton Onyx
dans le frontend.

## 4. Widget d'intégration visuelle dans Cortex

Le chat Onyx est embarqué visuellement dans Cortex via
`apps/cortex_rental/cortex_rental/www/onyx-assistant.html` (+ son
contrôleur `.py`), qui rend le web component officiel
`<onyx-chat-widget>` (léger, Shadow DOM — pas de conflit CSS avec
Frappe Desk). Ça n'affaiblit rien de la sécurité déjà en place : le
widget est purement visuel côté client, tout appel d'outil agent réel
repasse toujours par Cortex MCP → API Frappe whitelisted avec les mêmes
vérifications de scope/tenant.

Configuration requise dans `site_config.json` du site Frappe
(**jamais committé** — c'est un fichier local par site) :

```json
{
  "onyx_backend_url": "https://onyx.<votredomaine>",
  "onyx_widget_api_key": "<clé Onyx à portée limitée, chat uniquement>",
  "onyx_widget_script_url": "https://onyx.<votredomaine>/widget/onyx-widget.js",
  "onyx_default_model_label": "Gemini 3.7 Flash (défaut)"
}
```

**`onyx_widget_api_key` DOIT être une clé à portée limitée (chat
uniquement)** — la doc Onyx est explicite : cette clé est visible dans
le code source de la page côté client. Ne jamais y mettre une clé à
accès complet.

`onyx_widget_script_url` : le chemin exact du bundle JS du widget sur
un déploiement self-hosted **n'a pas été vérifié dans cette session**
(la doc publique ne montre que l'exemple cloud
`https://your-cdn.com/onyx-widget.js`). La valeur par défaut
(`{backend_url}/widget/onyx-widget.js`) est une supposition raisonnable
à confirmer contre votre déploiement réel — surcharger cette clé si
elle diffère.

Page accessible à `/onyx-assistant` une fois le site Frappe démarré,
réservée aux utilisateurs authentifiés (pas `Guest`).
