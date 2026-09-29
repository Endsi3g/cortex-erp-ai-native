# Plan de reconstruction UI — pages Desk ERPNext + Frappe UI

**Statut :** plan d'implémentation, à valider. Aucun code applicatif n'est modifié par ce document.
**Date :** 2026-09-28 · **Auteur de la demande :** Kael Belceus
**Contrat parent :** [`CORTEX_UI_HANDOFF_V2.md`](CORTEX_UI_HANDOFF_V2.md) (prime sur ce plan en cas de conflit)
**Principe :** *Cortex suggère, l'humain décide.* ERPNext/Frappe reste le système de référence.

---

## 1. Décisions prises

| Sujet | Décision |
|---|---|
| Architecture | **Garder les Pages Desk** (`/app/cortex-*`) et y utiliser Frappe UI. La SPA Vite autonome n'est plus une cible de déploiement : elle devient un réservoir de code (contrats API, stores, i18n, composants) migré vers le package partagé. |
| Couche IA | **Tout dans `cortex_rental`** (DocTypes `Cortex Chat Session/Message`, `Cortex Agent Run`, `Approval Request`, client Onyx existants). Pas de 2e app `cortex_ai` à ce stade. |
| Séquençage | Fondation + sidebar d'abord, puis écrans P0, puis IA, puis P1/P2. |
| Contenu de la sidebar | Modules Cortex, raccourcis ERPNext natifs, Raven (si installé), badges live et écrans récents. |

## 2. Constats vérifiés dans le code

Chaque point a été relu dans le dépôt le 2026-09-28. Aucun bench Frappe ni `node_modules` n'est disponible dans cet environnement : rien n'a été construit ni exécuté.

### 2.1 Deux frontends parallèles
- **Pages Desk :** 8 pages (`availability`, `transaction_composer`, `checkin`, `customers`, `fleet`, `supervision`, `accounting_pnl`, `assistant`), environ 10 700 lignes de Vue dans `public/js/`. Elles montent Vue via `frappe.require("*.bundle.js")`.
- **Aucune ne consomme Frappe UI** : `grep frappe-ui public/js` ne retourne rien. Le commit `bffa6f3` n'a intégré Frappe UI que dans la SPA Vite.
- **SPA Vite** (`public/frontend`) : environ 40 routes, dont **17 vues placeholder** de 17 lignes (`ScreenPlaceholderCard`). Elle n'est servie par aucun hook Frappe (seulement Vite sur `:5173`).
- Ses routes `/app/cortex-*` **entrent en collision** avec les routes du Desk.

### 2.2 Sidebar : pourquoi elle n'est pas utilisable
1. `CortexSidebar.vue` (Desk) pointe vers `cortex-operations`, `cortex-rentals`, `cortex-approvals`, `cortex-consignment` et `cortex-team`. **Aucune Page Desk n'existe pour ces routes.** Le composant a été retiré de `CortexShell` (double chrome), c'est donc du code mort.
2. `AppSidebar.vue` (SPA) a des liens codés en dur vers `DEMO-TRX-2026-006`, `DEMO-TRX-2026-001` et `DEMO-SN-ALX-001`, et un **badge « 3 » fictif**. Cela viole la règle « pas de données inventées ». Les groupes sont aussi étiquetés en 10 px en majuscules, sous le minimum de 12 px.
3. `setup.setup_cortex_sidebar()` exécute un `UPDATE tabWorkspace SET is_hidden=1 WHERE name != 'Cortex Rental'`, et il est appelé depuis **`boot_session`, donc à chaque ouverture de session**. Conséquences :
   - une écriture en base à chaque boot ;
   - tous les workspaces ERPNext sont cachés, ce qui contredit le choix « raccourcis ERPNext natifs » ;
   - l'erreur est avalée par `except Exception: pass`.
4. `CORTEX_WORKSPACE_ORDER` liste 8 noms, dont un seul existe (`Cortex Rental`). Le filtre de `get_cortex_workspace_sidebar_items` et celui de `boot_session` ne conservent donc qu'une entrée.
5. Le workspace est **dupliqué** dans deux dossiers (`workspace/cortex-rental/` et `workspace/cortex_rental/`), avec le même `name`. Un seul survit à la synchronisation.
6. Les liens du workspace ouvrent des **listes DocType brutes** pour Locations, Approbations, Demandes entrantes et Audit, faute d'écrans Cortex.

### 2.3 API disponible (`cortex_rental/api/v1`)
- **Présent :** `session.get_session_context`, `availability.get_matrix / get_alternatives / check_for_staff`, `rentals.list_rentals / get_rental / search_rental_customers / search_rental_catalog / preview_pricing / create_quote_draft / update_quote_draft / request_reservation / request_contract / get_rental_audit`, `checkin.*` (4), `checkout.*` (2), `approval_queue.list_approval_requests / get_approval_request / decide_approval`, `chat.*` (create, send, get, list, pin/clear context), `accounting.get_profit_and_loss`, `customers.search_customers / create_customer_draft`, `items.search_items`, `intake.register_evidence_api / record_extraction`, `consignment.prepare_owner_statement`.
- **Absent (à créer côté serveur avant de câbler l'écran) :** KPI de l'aperçu Opérations, liste/détail des suggestions IA (Inbox et Workspace), liste filtrée de l'audit IA, tableau de bord consignation, liste des propriétaires, liste et détail du catalogue, séries, kits, compteurs de navigation, streaming du chat.

### 2.4 Contexte technique
- Stack : **Frappe/ERPNext v15** (`version-15`, non épinglée à un patch, voir `compatibility-matrix.md`). Raven n'est pas dans le bench de dev.
- **Risque connu (gate de ce plan)** : `HANDOFF.md` et `CHANGELOG.md` documentent un bug amont où **esbuild échoue quand `frappe-ui` est importé dans un bundle de Desk Page**. Frappe UI publie des `.vue`/`.ts` bruts, des icônes virtuelles (plugin Vite) et un preset Tailwind, que l'esbuild de `bench build` ne gère pas nativement. Ce risque n'a jamais été testé sur un vrai bench.

## 3. Architecture cible

```
ERPNext site (v15)
├── Desk (chrome ERPNext : navbar, sidebar workspaces, awesomebar)
│   └── Page cortex-<écran>      ← coquille mince (.js + .json), route /app/cortex-<écran>
│        └── monte une app Vue 3 + FrappeUIProvider dans .layout-main-section
├── cortex_rental (app Frappe)
│   ├── api/v1/*                 ← seule voie d'écriture, permissions Frappe
│   ├── public/frontend/         ← source UNIQUE : composants, stores, contrats, i18n
│   └── workspace/*              ← navigation
└── ERPNext / Raven (natifs)
```

Règles :
- **Un seul chrome** : celui du Desk. Pas de shell Vue imbriqué (leçon du commit `bffa6f3`).
- **Une seule base de code UI** dans `public/frontend/src` ; les dossiers `public/js/cortex_*` deviennent de fines coquilles d'entrée, puis les `.vue` dupliqués sont supprimés.
- Le client API reste typé (`CortexApiClient`) avec l'adaptateur HTTP `frappe.call`/`createResource`. Le `MockCortexApiClient` ne s'active que par configuration explicite et l'écran affiche alors un bandeau « données de démonstration ».
- L'IA reste côté serveur (Onyx/MCP) ; aucun secret ni appel LLM dans le navigateur.

### 3.1 Stratégie de build : décidée par le spike (Phase 0)

| | Plan A — esbuild de `bench build` | Plan B — micro-frontends Vite (fallback probable) |
|---|---|---|
| Principe | Les `*.bundle.js` importent `frappe-ui` directement | Un build Vite multi-entrées produit des modules ESM dans `public/frontend/dist/` ; chaque Page Desk fait `import()` de son entrée depuis `/assets/cortex_rental/frontend/dist/…` |
| Pour | Aucun outil supplémentaire ; hot reload Desk | Frappe UI, icônes et Tailwind fonctionnent tels que conçus ; TypeScript strict ; tests Vitest existants réutilisables |
| Contre | Bug esbuild connu ; icônes Lucide virtuelles et CSS Tailwind à reconstituer | Artefacts `dist` à builder et versionner ou générer en CI ; `bench build` doit déclencher `npm run build` |
| CSS | Tailwind à intégrer au pipeline Frappe | Tailwind **scopé** (voir 3.2) |

### 3.2 Coexistence CSS avec le Desk
Le preflight Tailwind et les styles Frappe UI ne doivent pas casser le Desk. Exigences : tout le CSS Cortex est confiné sous une racine `.cortex-root` (option `important` de Tailwind ou préfixe), preflight désactivé ou scopé, tokens `--cortex-*` conservés dans `public/css/cortex-tokens.css`, aucun style qui touche `.navbar`, `.sidebar` ou `.page-head` en dehors du masquage déjà en place.

## 4. Sidebar (Desk v15)

La sidebar est celle du Desk : la liste des **Workspaces**. On la rend correcte plutôt que d'en construire une deuxième.

### 4.1 Structure cible
1. **Cortex — Opérations** : Aperçu, Disponibilité, Locations, Nouveau devis
2. **Cortex — Entrepôt** : Check-out, Check-in
3. **Cortex — Finance et consignation** : P&L, Consignation, Propriétaires
4. **Cortex — IA** : AI Inbox, AI Workspace, AI Audit, Assistant
5. **Cortex — Catalogue et parc** : Équipements, Séries, Kits, Clients, Parc
6. **Cortex — Administration** : Politiques de location, Équipe et rôles, Import, Journal d'audit
7. **ERPNext** : Comptabilité, Stock, Ventes, Achats, Projets, Paramétrage (workspaces standard, rendus visibles)
8. **Messagerie** : Raven (lien `/raven` **seulement si l'app est installée**)

### 4.2 Travaux
- **Supprimer** `setup_cortex_sidebar()` et tout SQL exécuté depuis `boot_session`. Remplacer par des fixtures Workspace idempotentes (ordre, parent, rôles), appliquées uniquement par `after_migrate`.
- **Dédoublonner** les workspaces (un seul dossier) et créer les groupes ci-dessus avec `parent_page` et `sequence_id`. **À vérifier sur un vrai bench v15** : le rendu des sous-pages de workspace dans la sidebar.
- **Ne plus cacher ERPNext.** Réduire `get_cortex_workspace_sidebar_items` à un simple tri (Cortex d'abord), ou le retirer si les fixtures suffisent.
- **Visibilité par rôle** via la table de rôles du Workspace (`Cortex *`), jamais par masquage côté client. Le serveur reste la source de vérité des droits.
- **Cibles valides uniquement** : chaque entrée pointe vers une Page ou un DocType qui existe. Les écrans pas encore livrés pointent vers la liste DocType native, jamais vers une route morte ni un placeholder.
- **Badges live** : compteurs natifs des raccourcis de workspace (`stats_filter`), calculés avec les permissions de l'utilisateur : approbations `Pending` et demandes entrantes `Received`. Aucun endpoint `get_nav_counts` n'est nécessaire à ce stade. Un enrichissement de la sidebar par JS n'est envisagé qu'après le spike et reste facultatif : modifier le DOM du Desk est fragile entre versions.
- **Écrans récents** : liste par utilisateur en `localStorage` (confort par visiteur, avec try/catch), jamais un état métier.
- **Supprimer** `CortexSidebar.vue` (mort), les liens `DEMO-*` et le badge fictif de `AppSidebar.vue`.

### 4.3 Critères d'acceptation
- Un test automatisé parcourt tous les liens de tous les workspaces et vérifie que chaque cible existe.
- Aucun `DEMO-` ni compteur fictif dans la navigation.
- Un utilisateur sans rôle Cortex ne voit pas les groupes Cortex ; un rôle limité ne voit que ses groupes.
- Aucune écriture en base pendant `boot_session`.
- Navigation entière au clavier, focus visible, cibles d'au moins 44 px.

### 4.4 État d'avancement (2026-09-28)
Livré et testé par `tests/test_workspace_navigation.py` (statique, sans bench) : hub `Cortex Rental` + 6 groupes enfants (`Cortex Operations`, `Warehouse`, `Finance`, `AI`, `Catalog`, `Admin`) avec rôles et compteurs ; doublon de workspace supprimé ; SQL de masquage et hook `boot_session` retirés ; patch `restore_erpnext_workspaces` ; traductions `fr.csv` ; `CortexSidebar.vue` mort supprimé ; liens `DEMO-*` et badge fictif retirés de `AppSidebar.vue`.
**Vérifié sur bench réel le 2026-09-28** (Frappe/ERPNext 15.121.1, MariaDB 10.11, site neuf + démo) : le hub et ses 6 groupes s'affichent en sous-pages dans la sidebar du Desk, à côté des modules ERPNext restaurés (Accounting, Buying, Selling, Stock…) ; les compteurs de raccourcis sont réels (« Transactions 3 ») ; les patches s'appliquent à `bench migrate`. Reste non vérifié : Raven (non installé), traductions `fr.csv` sur un utilisateur en français, application du patch sur une base existante avec workspaces masqués.

### 4.5 Hébergement Desk : ce qui a été retenu et validé (2026-09-28)
- **Plan B retenu** : les écrans Vue 3 + Frappe UI sont compilés par Vite (`npm run build:desk` → `public/frontend/dist-desk/cortex-desk.js`) et chargés par `public/js/cortex_host/cortex_host.js` via `import()`. Le build esbuild de `bench build` n'est pas utilisé pour Frappe UI. `dist-desk` n'est pas versionné : l'entrypoint Docker et `make build-desk` le produisent.
- **Mise à jour du 2026-09-29** : les mêmes écrans sont aussi servis par une application autonome sur `/cortex` (`npm run build:spa`, plugin Vite frappe-ui, `www/cortex.py`). Le plan B ci-dessus reste en place tant que la suppression des Pages Desk n'est pas validée ; voir le handoff V2 pour la décision.
- **Isolation CSS** : tout est sous `.cortex-root` ; les accents bleus de Frappe UI sont remplacés par la palette Cortex ; Inter est conservée ; `desk.css` neutralise les règles Desk qui fuient (`dt` gras, `font-variation-settings`, espacement des lettres).
- **Collision Workspace / Page** : un Workspace gagne toujours sur une Page du même slug. Les écrans `cortex-operations` et `cortex-rental` vivent donc dans les Pages `cortex-ops-overview` et `cortex-rental-detail` ; `cortex_host.js` traduit les chemins SPA (`PAGE_ALIASES`), le patch `remove_shadowed_pages` supprime les anciennes Pages et un test interdit toute nouvelle collision.
- **Validé avec Chromium sur un vrai Desk** : 13 Pages montées (opérations, locations, détail, équipements, série, kits, consignation, propriétaire, relevé, AI Inbox/Workspace/Audit, check-out), données réelles issues des endpoints `cortex_rental.api.v1.*` (12 endpoints de lecture répondent 200), lien de navigation via `frappe.set_route`.
- **Défauts trouvés uniquement grâce au bench et corrigés** : `frappe.ready` n'existe pas dans le Desk (le lanceur Copilot ne se montait jamais → événement `startup`) ; la racine flottante du Copilot masquait toute la page (fond `#fafafa` plein écran) ; la société par défaut côté serveur et côté session pouvaient diverger ; la fixture de démo ne respectait plus `Cortex Rental Item Profile` (société et valeur de remplacement obligatoires) ; dates brutes dans l'onglet Aperçu.
- **Pages historiques (2026-09-29)** : `cortex-availability`, `cortex-checkin`, `cortex-transaction-composer`, `cortex-customers`, `cortex-fleet`, `cortex-supervision` et `cortex-accounting-pnl` sont maintenant des coquilles qui montent le même bundle Vite ; leurs anciens bundles esbuild (10 000 lignes) sont supprimés. `cortex-customers`, `cortex-fleet` et `cortex-supervision` affichaient des données statiques fabriquées : elles sont remplacées par la liste clients réelle (`customers.list_customers`), la liste d'équipements et la file d'approbation de l'AI Inbox. L'état des résultats lit le rapport ERPNext `Profit and Loss Statement` et affiche une erreur explicite (plus jamais des zéros) quand le rapport échoue. Seule `cortex-assistant` garde son bundle (panneau Copilot).
- **Portail sans style (`/login`, `/me`)** : cause trouvée sur bench, indépendante de Desk et de Vite. `bench build --app cortex_rental` ne compile pas `website.bundle.css`, `frappe-web.bundle.js` ni `desk.bundle.*` de Frappe : 404 sur ces fichiers, donc HTML sans CSS. L'entrypoint lance maintenant `bench build` complet quand ces bundles manquent (test statique `test_entrypoint_builds_frappe_bundles_when_missing`). Sur un bench existant : `bench build`.
- **Limites connues** : pas de mode sombre dans le build Desk ; jetons de couleur légèrement différents entre le Desk (`#047857`) et la SPA (`#066336`) ; exports, téléversements et actions de consignation restent affichés comme indisponibles ; le test de flux d'écriture (approbations, check-out) n'a pas été rejoué sur le bench.

## 5. Matrice des écrans

| Écran | Route Desk | Aujourd'hui | API | Action |
|---|---|---|---|---|
| Aperçu opérations | `cortex-operations` | Absent (page SPA) | **Manquante** (KPI) | Créer endpoint + page |
| Disponibilité | `cortex-availability` | Page Desk | `get_matrix` ✓ | Porter vers Frappe UI |
| Locations (liste) | `cortex-rentals` | Liste DocType brute | `list_rentals` ✓ | Nouvelle Page |
| Nouveau devis | `cortex-transaction-composer` | Page Desk (883 l.) | `preview_pricing`, `create/update_quote_draft` ✓ | Porter |
| Détail location | `cortex-rental/:name` | Absent | `get_rental`, `request_*`, `get_rental_audit` ✓ | Nouvelle Page |
| Check-out | `cortex-checkout/:rental` | Absent | `record_checkout_scan`, `complete_checkout` ✓ | Nouvelle Page |
| Check-in | `cortex-checkin` | Page Desk | ✓ | Porter |
| AI Inbox | `cortex-ai-inbox` | Vue SPA | Approbations ✓ ; suggestions/documents **manquants** | Endpoint liste + page ; approbations d'abord |
| AI Workspace | `cortex-ai-workspace/:itemId?` | Vue SPA | **Manquante** (détail, versions) | Endpoint + page ; fonctions sans API marquées « indisponible » |
| AI Audit | `cortex-ai-audit` | Vue SPA | **Manquante** (liste filtrée, export) | Endpoint sur `Audit Event` + page |
| Assistant (chat) | `cortex-assistant` | Page Desk | `chat.*` ✓ ; streaming **manquant** | Porter, puis Socket.IO |
| Clients | `cortex-customers` | Page Desk | `search_customers` ✓ | Porter |
| Parc | `cortex-fleet` | Page Desk | Partielle | Porter |
| Supervision | `cortex-supervision` | Page Desk | À auditer | Porter |
| P&L | `cortex-accounting-pnl` | Page Desk | `get_profit_and_loss` ✓ | Porter (référence visuelle) |
| Équipements, série, kits | `cortex-equipment`… | Placeholders | `search_items` seulement | P2 : endpoints puis pages |
| Consignation, relevé propriétaire | `cortex-consignment`… | Vues SPA partielles | `prepare_owner_statement` seul | P2 : endpoints ; relevé via `OwnerStatementSafe` |
| Administration (4) | — | Placeholders | DocTypes natifs | **Ne pas reconstruire** : liens vers les vues natives (Rental Pricing Rule, Role Permission Manager, Data Import, Audit Event) |

Les anciennes routes `approvals`, `incoming` et `drafts` redirigent vers l'AI Inbox avec leur filtre (contrat v2).

## 6. Phases

### Phase 0 — Spike de faisabilité (bloquant)
- Sur un vrai bench v15 (Docker `infra/docker/docker-compose.dev.yml`), monter **un** composant Frappe UI (`Button`, `ListView`, `Dialog`, une icône Lucide) dans la Page `cortex-availability` selon Plan A, puis selon Plan B.
- **Critères :** `bench build --app cortex_rental` passe ; le composant s'affiche avec ses styles et ses icônes ; le Desk (navbar, sidebar, modales natives) ne change pas visuellement ; poids du bundle mesuré ; rechargement de page et navigation entre deux Pages Cortex sans fuite (démontage de l'app Vue).
- **Sortie :** choix A ou B consigné dans ce document et dans `CORTEX_UI_HANDOFF_V2.md`. Taille : **S**.

### Phase 1 — Fondation et sidebar
- Package partagé dans `public/frontend/src` : `CortexPageMount` (montage/démontage et `FrappeUIProvider`), en-tête de page, KPI, table, états (chargement, vide, erreur, permission refusée, obsolète), badges d'état IA.
- Client API HTTP branché sur `session.get_session_context` ; garde de session (Guest → login Frappe).
- Sidebar selon la section 4. Endpoint `get_nav_counts`.
- Tests : liens de workspace, permissions de navigation, démontage des apps. Taille : **M**.

### Phase 2 — Écrans P0
Ordre : Disponibilité → Locations (liste) → Détail → Nouveau devis → Check-in → Check-out → Aperçu opérations.
- Chaque écran : contrat TypeScript, adaptateur HTTP, états complets, revalidation serveur (prix, taxes, disponibilité, transitions), erreurs de concurrence (version/ETag) et idempotence sur toute mutation.
- Suppression des `.vue` Desk dupliqués une fois l'écran porté et recetté. Taille : **L**.

### Phase 3 — IA
- AI Inbox (approbations réelles d'abord, puis suggestions et documents entrants), AI Workspace, AI Audit.
- Chat : historique, sélection d'agent, tool calls visibles avec approbation, contexte ERPNext, citations, puis streaming Socket.IO (`frappe.publish_realtime`) ; rendu Markdown assaini.
- Notification Raven des demandes d'approbation **seulement si Raven est installé** ; sinon repli sur les notifications Frappe.
- Confiance : afficher « confiance non évaluée » tant que le backend ne fournit pas un score calibré.
- Recette bout en bout Cortex→Onyx→MCP→Frappe, à distinguer des mocks. Taille : **L**.

### Phase 4 — P1/P2 et décommissionnement
- Catalogue, consignation, propriétaires : endpoints d'abord, pages ensuite.
- Retrait de la SPA Vite comme cible de déploiement, du `CortexSidebar` mort et des placeholders. Mise à jour de `HANDOFF.md`, `route-map.md`, `file-ownership.md`. Taille : **L**.

### Phase 5 — Recette
Accessibilité (axe, clavier, zoom 200 %), comparaison visuelle avec la capture P&L, tests live (pas des mocks), revue de sécurité (`bench` avec rôles réels), pin des versions Frappe/ERPNext. Taille : **M**.

## 7. Règles de design et d'UX appliquées

Les tokens du projet et le contrat v2 priment. Le tableau indique comment les règles générales fournies s'appliquent ici.

| Règle | Application dans Cortex |
|---|---|
| Un seul accent | Vert ERP (`--cortex-emerald-*`, `cortex-tokens.css`) pour l'action principale et l'état actif. Ambre et rouge réservés au statut ; aucun violet « copilote » (le violet des exemples de chat est écarté). |
| Tokens uniquement | Aucune valeur hex dans les composants ; nouveau token d'abord si une valeur manque. Thèmes clair/sombre par tokens. |
| Échelle typographique | 12 / 14 / 16 / 20 / 25. **Exception assumée** : le contrat v2 demande une interface ERP dense, donc tables et formulaires à 14 px ; le texte de lecture (chat, résumés IA) à 16 px. Aucun texte sous 12 px. Titres de groupes en 12–13 px, majuscules, espacement ≥ 0,05 em (corrige les 10 px actuels). |
| Espacement | Échelle 4 / 8 / 16 / 24 / 32 / 48 / 64 ; tout écart hors échelle est corrigé. Regrouper par espace avant d'ajouter une bordure. |
| Largeurs | Applications 1280 px de contenu maximum sauf tables et graphiques pleine largeur (contrat v2) ; texte de lecture 65–75 caractères. Breakpoints 640 / 768 / 1024 / 1280. |
| Une action principale par vue | Un seul bouton plein vert par écran ; secondaires en contour ; destructifs en rouge et séparés. Libellés verbes (« Soumettre pour approbation », pas « OK »). Le bouton de validation nomme exactement le prochain événement (contrat v2). |
| Cartes | Une carte = un élément répété (suggestion, KPI). Pas de carte dans une carte ; sections séparées par l'espace. |
| Tables | Chiffres alignés à droite en chiffres tabulaires, lignes 40 px (compact) ou 48 px, pas de bordures verticales, texte tronqué avec valeur complète au survol/focus. |
| Cibles et boutons | Hauteur 40 px (32 px en table dense), zone cliquable ≥ 44 px, jamais d'icône seule sans `aria-label`. |
| États | Survol, focus visible 2 px, actif, désactivé pour chaque contrôle ; chargement (squelette à hauteur fixe), vide (une phrase + une action), erreur, succès pour chaque zone asynchrone. |
| Mouvement | 100–200 ms pour les retours, ≤ 300 ms pour la mise en page, jamais > 400 ms ; `prefers-reduced-motion` respecté ; pas d'animation au chargement. |
| Formulaires | Libellés visibles au-dessus, une colonne, validation en ligne après sortie du champ, message qui dit comment corriger, travail préservé après erreur. |
| Un but par écran, progression | Composer découpé en étapes avec progression visible et brouillon sauvegardé ; fin de parcours avec confirmation et prochaine étape. |
| Prévention et récupération | Actions impossibles désactivées avec raison ; confirmation avant toute action risquée ; réessai, annulation ou restauration quand le serveur le permet ; jamais de nouvelle tentative aveugle d'une mutation externe. |
| Accessibilité | Sémantique HTML, ordre de tabulation logique, contraste AA, test à 375 px et 200 % de zoom. |

**Passe finale obligatoire par écran :** un seul accent, ≤ 5 tailles de texte, un seul bouton principal, espacements sur l'échelle, cartes justifiées, états d'interaction et états asynchrones complets, parcours clavier, rendu à 375 px.

## 8. Vérité, sécurité et permissions
- Toute écriture passe par `api/v1` et les permissions Frappe ; masquer un bouton n'est pas un contrôle d'accès.
- Isolation par société vérifiée par le serveur à chaque requête.
- Mock, fixture, API réelle et service IA sont affichés comme des modes distincts. Une fonction sans API réelle est marquée « indisponible » et ne simule jamais une sauvegarde.
- URL Onyx, jeton et modèle restent côté serveur. Aucun `VITE_*` sensible.
- Contenu des documents entrants traité comme non fiable (injection de prompt) ; rendu Markdown assaini contre le XSS.

## 9. Tests et livraison
- Frontend : `vue-tsc`, Vitest (contrats, stores, garde de session, privacy `OwnerStatementSafe`), axe. La suite complète ne doit pas être présentée comme verte tant que le test d'import de toutes les vues (délai de 180 s) n'est pas stabilisé.
- Backend : `ruff`, tests de permissions par rôle, test des liens de workspace, test de non-écriture au boot.
- Live : parcours P0 sur bench réel, identifiés comme tels.
- Un PR par phase, avec la case « preuves d'exécution » remplie de captures réelles.

## 10. Risques et questions ouvertes

| Risque / question | Traitement |
|---|---|
| Frappe UI incompatible avec l'esbuild de `bench build` | Résolu : Plan B (bundle Vite chargé par `cortex_host.js`), validé sur bench réel. |
| Rendu des sous-pages de workspace en v15 | Validé sur bench 15.121.1 (section 4.5). |
| Version Frappe/ERPNext non épinglée | Épingler après la première recette réelle. |
| Raven absent du bench de dev | Lien conditionnel ; installer Raven pour la recette Phase 3. |
| Comparaison visuelle P&L jamais validée | Élément de recette Phase 5. |
| Le modèle de PR du dépôt (Laravel/Filament) est obsolète | À mettre à jour hors de ce chantier. |
| Le test d'import complet des vues dépasse 180 s | À stabiliser avant de compter sur la suite complète. |
