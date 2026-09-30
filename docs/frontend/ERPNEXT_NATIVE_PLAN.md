# Plan d'implémentation : Cortex 100 % ERPNext natif

**Décision du 2026-09-30 (Kael Belceus)** : Vite, Frappe UI, la SPA `/cortex` et les Pages Desk qui montent un bundle Vite sont **retirés complètement**. Cortex se construit dans ERPNext/Frappe (v15) avec ses propres constructions natives. Cette décision remplace celles du 2026-09-28 et du 2026-09-29 dans `CORTEX_UI_HANDOFF_V2.md`.

## 1. Cible visuelle et principes

- **Modèle à suivre** : le workspace *Accounting* d'ERPNext : bloc d'intégration (onboarding), graphique principal, rangée de cartes de nombres, raccourcis avec compteurs, cartes de liens « Rapports et maîtres ». Les workspaces Cortex actuels (liste de liens « Modules Métiers ») sont **refusés**.
- **AI-native d'abord** : la première page après connexion est l'**Accueil Cortex**, un écran conversationnel type Claude (« Que puis-je faire pour vous ? », zone de saisie, suggestions, conversations récentes). Les workspaces sont l'étape suivante, le Desk ERPNext reste complet.
- **ERPNext reste le système de référence** : aucune donnée inventée, aucune écriture hors des API permissionnées (`cortex_rental.api.v1.*` et vues natives). Les valeurs affichées viennent de la base ; l'IA propose, une personne décide.
- **Pas de build tiers** : aucun Vite, Tailwind ou Frappe UI. Seuls outils permis : constructions natives de Frappe (workspaces, cartes, graphiques, vues, rapports, formulaires) et le bundler intégré (`*.bundle.js`, compilé par `bench build`) pour l'accueil IA, la grille de disponibilité et le scan.
- **Langue** : tout ce que Cortex ajoute est en français (Québec). Les écrans ERPNext non traduits restent tels quels.
- **Fluidité** : transitions courtes (150–250 ms) entre états (chargement → contenu, ouverture de panneaux, arrivée de messages), toujours désactivées avec `prefers-reduced-motion`.

## 2. Ce qui est retiré

| Retrait | Détail |
| --- | --- |
| Projet Vite/Vue | `apps/cortex_rental/cortex_rental/public/frontend/` (sources, `dist-desk`, `dist-spa`, `package.json`, configs, tests Vitest) |
| Application autonome `/cortex` | `www/cortex.py`, `www/cortex.html`, `website_route_rules`, `add_to_apps_screen` vers `/cortex`, réglage `default_app` |
| Hôte des écrans | `public/js/cortex_host/`, entrées `app_include_js`, alias de pages |
| Pages Desk « coquilles » | les 26 Pages dont le JS ne fait que `cortex_rental.host.mount` (remplacées par workspaces et vues natives) |
| Outillage | étapes `npm` de l'entrypoint Docker, cibles `make build-desk/build-spa`, entrées `.gitignore` |
| Écrans de connexion Vue | conservés : les pages Jinja `/login`, `/cortex-verify`, `/update-password` |

L'historique Git garde tout le code retiré. Les API Python (`api/v1/*`, services, DocTypes) ne changent pas : les écrans natifs les réutilisent.

## 3. Inventaire des écrans → construction native

| Écran actuel | Construction native |
| --- | --- |
| Accueil / aperçu des opérations | **Accueil Cortex** (Page + bundle) puis workspace *Opérations* : cartes (départs du jour, retours attendus, en retard, approbations), graphiques (locations par état, revenus par mois), liste rapide des prochains départs |
| Liste des locations | Vue **Liste** de *Cortex Rental Transaction* (indicateurs de couleur par état, filtres enregistrés, champs de liste), **Kanban** par `rental_state`, **Calendrier** et **Gantt** (début/fin), **Rapport** |
| Détail d'une location | **Formulaire** natif : tableau de bord des liens, barre d'état, boutons *Sortie*, *Retour*, *Facturer*, aperçu de prix serveur, historique (`track_changes`) |
| Compositeur de location | Formulaire *nouvelle location* + script client (disponibilité et prix calculés par le serveur) |
| Matrice de disponibilité | **Rapport à script** *Disponibilité du parc* (filtre de dates) ; grille interactive en Page + bundle (P4) |
| Sortie / retour (scanners) | Formulaire *Cortex Check-In* et dialogue de scan avec champ **Code-barres** natif ; validation serveur (`api/v1/checkout|checkin`) |
| Clients | Liste native *Customer* + rapport d'activité de location |
| Catalogue, séries, kits | Listes/formulaires natifs *Cortex Rental Item Profile*, *Item*, *Serial No*, *Product Bundle* + rapport de disponibilité |
| Consignation | Workspace *Consignation* + rapports *Relevé propriétaire* et *Versements* |
| Approbations, demandes entrantes, brouillons IA | Workspace *IA* : listes rapides + **Liste** *Approval Request*, *Cortex Inbound Request*, *Cortex Extraction Run* avec actions de décision côté serveur |
| Audit | **Rapport** *Journal d'audit* (lecture seule) |
| États financiers | Rapports natifs ERPNext (*Profit and Loss Statement*, *General Ledger*…) dans le workspace *Finance* |
| Règles, équipe, import | **Formulaires/listes natifs** *Rental Pricing Rule*, *User* (profils Cortex), *Data Import* ; bloc d'intégration pour guider |
| Mise en route entreprise | **Module Onboarding** natif (étapes réelles) + page *Configuration* |

## 4. Workspaces (structure type *Accounting*)

Chaque workspace = **bloc d'intégration** (si utile) → **graphique principal** → **4 cartes de nombres** → **Raccourcis** (avec compteurs) → **cartes de liens** (rapports, maîtres, paramètres). Documents natifs à créer : *Number Card*, *Dashboard Chart*, *Module Onboarding* + *Onboarding Step*, *Workspace*.

| Workspace | Cartes de nombres | Graphique(s) | Raccourcis principaux |
| --- | --- | --- | --- |
| **Cortex** (accueil du module) | Locations en cours · Départs aujourd'hui · Retours attendus · Approbations en attente | Locations par état | Nouvelle location, Disponibilité, Sorties/retours, IA |
| **Opérations** | Départs 7 j · Retours 7 j · En retard · À préparer | Locations par mois | Locations, Calendrier, Gantt, Kanban |
| **Entrepôt** | Sorties du jour · Retours du jour · Mis en quarantaine · Dommages ouverts | Retours par état | Sortie, Retour, Séries |
| **Catalogue** | Équipements · Séries actives · Kits · Valeur de remplacement | Équipements par catégorie | Profils, Articles, Séries, Kits |
| **Finance** | Facturé (mois) · Acomptes · Solde à recevoir · Versements dus | Revenus par mois | P&L, Grand livre, Factures, Versements |
| **Consignation** | Propriétaires · Versements calculés · Approuvés · Payés | Versements par mois | Propriétaires, Versements, Relevés |
| **IA** | Demandes à traiter · Brouillons à réviser · Approbations · Exécutions d'agents | Décisions par jour | Boîte, Approbations, Audit |
| **Administration** | Utilisateurs actifs · Invitations en attente · Règles actives · Imports récents | — | Règles, Équipe, Import, Journal d'audit |

Les compteurs n'utilisent que des filtres réels sur les DocTypes et sont limités par société (permissions de requête déjà en place).

## 5. Vues natives à ajouter aux DocTypes

- `*_list.js` : indicateurs de statut (couleurs et libellés français), `add_fields`, actions groupées permissionnées.
- `*.js` (formulaire) : boutons d'action, tableau de bord des liens, aperçu serveur des prix et de la disponibilité, avertissements d'assurance/compte/paiement (déjà calculés côté serveur).
- Kanban (`rental_state`, `Approval Request.status`), Calendrier (`starts_at` → `ends_at`), Gantt.
- Rapports à script dans le module : *Disponibilité du parc*, *Prochains départs et retours*, *Relevé propriétaire*, *Versements de consignation*, *Journal d'audit*, *Activité des clients*.

## 6. Accueil IA (page d'arrivée)

- **Page Desk** `cortex-home` + bundle `cortex_home.bundle.js` (Vue 3 compilé par Frappe, sans Frappe UI) réutilisant le rendu de blocs de `cortex_copilot`.
- Contenu : salutation, zone de saisie (Entrée pour envoyer), suggestions selon les rôles, conversations récentes (`chat.list_sessions`), raccourcis vers les workspaces, indicateurs de l'agent (état, jamais de confiance inventée).
- Passerelle : `cortex_rental.api.v1.chat.*` (Onyx). Si Onyx n'est pas configuré : message clair et suggestions de navigation restent utilisables.
- Redirection après connexion et sur `/app` vers `cortex-home` (hook `boot_session` + événement `startup` déjà présent), sans bloquer l'accès aux autres pages.
- Copilote flottant conservé sur toutes les pages Desk.

## 7. Animations

Feuille `cortex-motion.css` (chargée dans le Desk) : entrée douce du contenu de workspace (opacité + 8 px), squelettes pendant le chargement des cartes, arrivée des messages de l'accueil IA, ouverture des panneaux, survol des cartes/raccourcis. Durées 150–250 ms, courbe `cubic-bezier(.2,.8,.2,1)`, tout neutralisé sous `prefers-reduced-motion: reduce`.

## 8. Phases

| Phase | Contenu | Critère de sortie |
| --- | --- | --- |
| **P0** | Ce plan ; retrait complet de Vite, `/cortex`, hôte et Pages coquilles ; mise à jour d'`AGENTS.md`, du handoff, de la CI, de l'entrypoint | Plus aucune référence à Vite/Frappe UI ; tests verts ; l'erreur « bundle absent » ne peut plus se produire |
| **P1** | Number Cards, Dashboard Charts, Module Onboarding, 8 workspaces façon Accounting | Chaque workspace rend graphique + cartes + raccourcis avec de vraies données ; capture comparée à *Accounting* |
| **P2** | Vues natives (liste, kanban, calendrier, Gantt, formulaire) et rapports à script | Chaque ancien écran a son équivalent natif, permissions vérifiées |
| **P3** | Accueil IA, redirection d'arrivée | Première page après connexion = Accueil ; conversation réelle ou message de configuration honnête |
| **P4** | Grille de disponibilité, scan sortie/retour, animations | Parcours *réserver → sortir → retourner* faisable sans quitter le Desk |
| **P5** | Vérification sur bench, axe, adaptatif 320–1920 px, tests Python, docs, PR | 0 violation axe sur les pages Cortex, aucun débordement, CI verte |

## 9. Risques et limites connues

- Le Desk ERPNext est moins souple qu'une SPA : la matrice de disponibilité et le scan demandent du JS Desk sur mesure (P4).
- Les cartes et graphiques dépendent des données : un site vide affiche des zéros ou des graphiques vides ; c'est voulu (pas de démonstration inventée). Des données de démonstration existent pour les tests de bench.
- Onyx doit être configuré (`onyx_base_url`, `onyx_api_key`) pour la conversation réelle.
- Les libellés ERPNext non traduits (Selling, Stock…) restent en anglais tant que la traduction n'est pas ajoutée.
