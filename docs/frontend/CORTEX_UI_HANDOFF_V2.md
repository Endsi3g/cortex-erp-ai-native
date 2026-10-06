# Cortex UI handoff v2 — ERPNext-first, AI-native

**Statut :** contrat produit canonique pour l’interface Cortex et les agents de développement.  
**Version :** 3.0 · 2026-09-30  
**Socle :** ERPNext + Frappe Framework v15, constructions natives (workspaces, cartes, graphiques, rapports, listes, formulaires) et bundler intégré de Frappe pour l’accueil IA. **Plus de Vite, de Frappe UI ni de SPA `/cortex`** (décision du 2026-09-30 ; plan : [`ERPNEXT_NATIVE_PLAN.md`](ERPNEXT_NATIVE_PLAN.md)).  
**Principe :** *Cortex suggère, l’humain décide.*

> Les instructions de ce fichier priment sur les descriptions frontend antérieures de `HANDOFF.md`. Elles ne remplacent pas les règles de sécurité métier déjà codées. Quand la documentation et le code divergent, ne prétends jamais qu’une fonction est opérationnelle : vérifie l’endpoint et décris l’écart.

## Mandat pour tout agent

Traite ce document comme le contrat produit commun avant de modifier un écran, un flux IA ou le shell. Conserve ERPNext/Frappe comme système de référence et les API métier Frappe comme seule voie d’écriture. Construis d’abord avec les constructions natives de Frappe/ERPNext ; n’écris du Vue (bundle Frappe, `*.bundle.js`) que pour l’accueil IA et les dialogues qu’aucune construction native ne couvre. Évite de créer un système parallèle, des données métier fictives, une action simulée présentée comme réelle, ou des appels LLM depuis le navigateur.

Avant tout changement : inspecte l’écran concerné (workspace, rapport, script de liste/formulaire), l’API `cortex_rental.api.v1.*`, les permissions et le service métier. Toute action doit traverser les autorisations Frappe et le service de domaine compétent. Toute suggestion visible doit distinguer fait vérifié, inférence, brouillon, erreur et indisponibilité du service.

## Positionnement et invariants

Cortex est l’ERP d’une vraie société de location de caméras et d’équipements professionnels. Le parcours quotidien va de la demande client à la vérification de disponibilité, au devis, au contrat, à l’approbation, puis au check-in et à l’inspection du matériel. L’IA est une couche d’assistance présente dans ces workflows et dispose aussi d’un espace conversationnel dédié, visuellement familier aux utilisateurs de Claude mais intégré au shell ERP.

- ERPNext et Frappe restent la source de vérité pour clients, articles, séries, stocks, prix, taxes, contrats, factures, réservations, rôles, droits et audit.
- Cortex Rental apporte les workflows métier spécialisés. Aucun état critique n’est inventé par un LLM.
- Le calcul de disponibilité, les prix, les taxes, l’assurance, les dépôts, les coûts de dommage et les transitions de statut sont calculés et revalidés côté serveur.
- L’IA peut rechercher, résumer, extraire, signaler, proposer des substitutions et créer des brouillons. Elle ne confirme pas seule une réservation, un contrat, une modification de prix, une facture, un changement d’état de matériel, une réparation ou une mise en quarantaine.
- L’envoi d’un message client peut être autorisé selon la politique et le rôle; il doit déclencher une notification et laisser une trace. Toute action externe reste idempotente et auditable.
- Les permissions sont vérifiées par le serveur pour chaque requête et chaque mutation, avec isolation par entreprise. Masquer un bouton n’est pas un contrôle d’accès.
- L’interface reste utile lorsque le fournisseur IA est lent ou indisponible : elle doit afficher clairement le statut et permettre de poursuivre le travail non-IA.
- Le contexte envoyé à un agent est limité au contexte métier et aux preuves nécessaires. Ne journalise pas de données sensibles brutes par défaut.

## Direction visuelle : référence ERPNext (workspace *Accounting*)

Le modèle est le workspace *Accounting* d’ERPNext : bloc d’intégration, graphique principal, rangée de cartes de nombres, raccourcis avec compteurs, cartes de liens. Une liste de liens sans données (ancien « Modules Métiers ») est refusée. Reprends le langage de la capture Profit and Loss fournie : interface de travail dense, claire, neutre, immédiatement lisible, conçue pour les opérations d’entreprise.

- Rail vertical gauche étroit, icônes seules en état replié, séparateurs de groupes fins et sélection vert pâle.
- Barre supérieure blanche d’environ 56 px, recherche centrée, commandes et identité utilisateur à droite.
- Barre de titre et actions compacte, filtres métier alignés sur une grille stable.
- Grandes surfaces blanches, bordures fines, rayons discrets, très peu d’ombres, arrière-plan de travail gris très pâle.
- Tables larges avec lignes compactes, séparateurs horizontaux, en-têtes sobres, chiffres alignés et filtres visibles.
- Vert ERP discret comme accent de marque et de validation. Ambre pour attention/confirmation, rouge pour risque bloquant. Aucun violet néon, halo ou dégradé « copilote ».
- Les pages analytics utilisent des graphiques, KPI et tables en pleine largeur, avec unités, périodes, devise et filtres explicites.
- Responsive : préserver les actions et les valeurs importantes; réduire le rail et convertir les panneaux latéraux en tiroir sur petit écran.
- Respecter clavier, focus visible, libellés accessibles, contrastes WCAG 2.2 AA et états vides/chargement/erreur.

L’AI Workspace peut reprendre une composition conversationnelle à la Claude, avec grande zone de travail centrale et historique/contextes latéraux, mais garde le shell et la palette de Cortex. Le chat pleine page n’est pas une solution universelle pour les écrans métier.

## Shell et navigation

> **Décision du 2026-09-30 (remplace celles du 2026-09-28 et du 2026-09-29) :** Cortex est **100 % ERPNext natif**. Le projet Vite/Vue, la SPA `/cortex`, le hôte `cortex_host` et les 26 Pages Desk « coquilles » sont supprimés (l’historique Git les conserve).

- **Première page après la connexion : l’espace Cortex Rental** (décision du 2026-09-30 : l’Accueil IA ne convient pas encore, il reste ouvert à la demande). `HOME_ROUTE = "cortex-rental"` dans `auth_hooks.py`; l’onboarding renvoie aussi vers `/app/cortex-rental`. **Accueil IA** (Page Desk `cortex-home`, bundle `cortex_home.bundle.js`, à refaire selon la vision du propriétaire) : logo de la société, « Bonjour {prénom} », date du jour, saisie « Que puis-je faire pour vous ? », raccourcis, conversations récentes (`chat.list_sessions`). Cartes de nombres : chiffres en noir, accent seulement pour ce qui exige une action (approbations, retards, litiges, manquants, quarantaine). Graphiques de l’espace Cortex Rental : par mois et par jour. Le guide de démarrage affiche la description de l’étape à droite, avec un **emplacement vidéo marqué « à venir »** (`cortex_desk.js`) tant que le champ `intro_video_url` de l’étape est vide (**aucune vidéo fournie**).
- **Navigation Cortex** (`public/js/cortex_nav.js`, `public/css/cortex-nav.css`) : barre latérale **présente sur toutes les pages** du Desk, limitée à ce qui sert (Tableau de bord, Locations, Disponibilité, Approbations avec pastille, Sorties et retours, Catalogue, Numéros de série, Clients, Factures, Paiements, Finance, Assistant IA ; *Équipe et règles* pour le propriétaire ; *Site Web* et *Paramètres* pour les administrateurs du site). Elle remplace la liste des espaces de Frappe (Comptabilité, Vente, Stock, Qualité… que le propriétaire ne peut pas ouvrir). Repliable (préférence conservée), tiroir avec bouton de menu sur téléphone, « Nouvelle location » en tête, `prefers-reduced-motion` respecté. Les filtres rapides de Frappe (Assigné à, Établi par) sont masqués par défaut dans les listes (`localStorage.show_sidebar`).
- **Barre du haut** : recherche courte (« Rechercher… », raccourci Ctrl/⌘ G en infobulle) ; menu **Aide** remplacé (patch `set_cortex_help_menu`) : *Discuter avec l'assistant* (ouvre le copilote), *Contacter le support* et *Mes demandes de support* (`Cortex Support Request`, notifie les administrateurs du site), *Raccourcis clavier*. Les notifications de Frappe sont inchangées.
- **Équipe en temps réel** : widget « N en ligne » (battement de cœur `presence.ping` toutes les 60 s, en ligne = vu dans les 3 dernières minutes) et fenêtre « Activité récente » issue du journal d'audit (`presence.team_activity_snapshot`, limitée à la société). Une vraie action humaine (devis, réservation, approbation, facture, paiement…) publie l'événement `cortex_activity` aux membres de la société ; sans serveur de sockets, relève toutes les 45 s. **Le serveur de sockets doit tourner** (`bench start`, ou `node apps/frappe/socketio.js` avec `DEV_SERVER=1` en développement).
- **Finance** (ADR-005) : espace *Finance* fondé sur des enregistrements Cortex (`Cortex Rental Invoice`, `Cortex Rental Payment`, `Cortex Finance Settings`), jamais sur les documents comptables d’ERPNext (le propriétaire n’en a pas les rôles). Cartes : facturé / encaissé / solde / en retard / TPS / TVQ ; graphiques mensuels ; rapports *Créances par client* et *Taxes perçues*. Les paiements passent par `api/v1/billing.record_payment`. Le hook `boot_session` expose `frappe.boot.cortex_home` (lecture seule) et `public/js/cortex_desk.js` redirige, une fois par chargement, l’arrivée sur `/app` ou `/app/home`. Les liens directs ne sont jamais redirigés.
- **Espaces de travail** (hub *Cortex Rental* et six groupes : Opérations, Entrepôt, Catalogue, Finance, IA, Administration) : structure *Accounting*, compteurs réels filtrés par société, graphiques, listes rapides, accueil avec la carte de configuration (voir « Onboarding complet »).
- **Écrans métier natifs :** liste avec indicateurs d’état français, Kanban (*Locations par état*), calendrier et Gantt des locations, formulaire avec actions (réserver, demander le contrat, sortie par scan, retour, décision d’approbation), rapports à script (*Disponibilité du parc*, *Prochains départs et retours*, *Activité des clients*, *Versements de consignation*, *Relevé propriétaire*).
- **Langue :** français seulement. `translations/fr.csv` (~1 400 entrées) complète les traductions de Frappe/ERPNext (libellés et options des DocTypes Cortex, textes d’aide des modules, rôles, noms de graphiques) ; les messages d’erreur du serveur et les descriptions de champs Cortex sont écrits en français ; `cortex_i18n.js` traduit quelques textes que Frappe écrit en anglais dans son code (mois du Gantt, bulles de filtres, valeurs d’état dans les graphiques) ; les visiteurs non connectés reçoivent des pages en français (`before_request`). Le patch `set_french_default` règle la langue du site et des utilisateurs qui n’en avaient pas choisi une autre. Restent en anglais : les noms d’enregistrements stockés comme données (formats d’impression, rôles, rapports et notifications standard d’ERPNext, journaux d’erreurs, noms de tâches planifiées) et le libellé « Cliquez pour trier par » quand l’étiquette vient d’un champ non traduit par Frappe.
- **Animations :** `public/css/cortex-motion.css` (150–250 ms, désactivées sous `prefers-reduced-motion`).
- Connexion, demande d’accès, mot de passe oublié : pages Jinja de Frappe (`/login`, `/cortex-verify`, `/update-password`). Voir `docs/auth/LOGIN_AND_ONBOARDING.md`.

Anciennes routes `/app/cortex-*` (Pages Desk) : supprimées ; le patch `remove_shell_pages` retire les enregistrements orphelins.

## Écrans IA

| Destination | Construction | Rôle |
|---|---|---|
| Accueil Cortex | Page `cortex-home` | Conversation avec l’assistant (passerelle IA interne via `chat.*`), point de départ |
| Boîte d’entrée IA | Liste *Cortex Inbound Request* + liste rapide du workspace IA | Documents entrants à traiter |
| Approbations | Liste/formulaire *Approval Request* (boutons Approuver/Refuser côté serveur) | Décisions humaines |
| Journal d’audit | Liste *Audit Event* (lecture seule) | Traçabilité |

Les sections « AI Inbox », « AI Workspace » et « AI Audit » ci-dessous décrivent le **comportement attendu** ; les écrans à deux colonnes (source / travail IA) ne sont pas encore reconstruits en natif : ne prétends pas qu’ils existent.

## AI Inbox

Vue par défaut personnelle avec bascule équipe si l’API expose réellement le périmètre équipe. N’affiche pas une bascule comme fonctionnelle si elle ne change pas le jeu de données serveur. La boîte réunit les suggestions générées, les demandes d’approbation et les documents reçus.

Disposition : titre et compte d’éléments en attente, commandes d’actualisation, vues personnelle/équipe; filtres de type, confiance, priorité, client, date et assignation; table pleine largeur; panneau de détail latéral sur grand écran, tiroir sur mobile.

Colonnes recommandées : sélection, type/titre, client/référence, agent lisible, confiance, priorité, statut, date, assigné à. La sélection groupée ne s’applique qu’aux opérations compatibles avec tous les éléments sélectionnés. Elle requiert une confirmation, vérifie les droits serveur et retourne le résultat par élément.

Actions disponibles : ouvrir, réviser, valider une approbation autorisée, rejeter, demander une correction humaine, assigner si l’API le permet, et annuler une suggestion acceptée lorsque le contrat serveur le permet. Validation humaine et application métier sont deux états distincts. En cas d’échec partiel, conserve le résultat individuel et les raisons de refus.

## AI Workspace

Deux colonnes de travail :

1. **Source à gauche :** message brut, PDF/image ou document disponible; aperçu/extrait, identité, date, page/position si fournis, citations et preuves. Les pièces jointes ou pages non disponibles sont signalées comme telles.
2. **Travail IA à droite :** champs structurés éditables, statut par champ, niveau de confiance, preuve associée, éléments manquants, risques, impact, conversation contextuelle et actions autorisées.

Afficher distinctement la valeur source, la suggestion IA et la correction humaine. Une correction manuelle prime sur une réextraction automatique, sauf demande explicite de l’opérateur. Les fonctions de versionnement, restauration, réextraction champ par champ et exécution d’action doivent être reliées à une API réelle; sinon elles doivent être présentées comme indisponibles et ne jamais donner une impression de sauvegarde.

Le bouton de validation décrit exactement le prochain événement : accepter une suggestion, soumettre une demande d’approbation, ou exécuter une action métier. Il ne transforme pas silencieusement un brouillon en réservation ou contrat.

## AI Audit

Table chronologique, filtres par agent, action et date, détail latéral, vues opérationnelle et technique. Montrer agent/acteur, action, entité, résultat, demande corrélée, durée, modèle si connu, appel(s) outil(s), preuve ou empreinte et décision humaine. Les valeurs non transmises par le backend s’affichent « non fourni » plutôt que d’être déduites.

Export CSV et impression PDF doivent respecter filtres et droits d’accès, protéger contre l’injection CSV et masquer les informations personnelles qui ne sont pas nécessaires. L’immutabilité est garantie par le backend append-only; le frontend ne doit pas la revendiquer s’il ne lit pas le journal correspondant.

## Langage et états de confiance

Les badges sont sobres et cohérents : `AI Draft`, `AI Suggested`, `Vérifié`, `À confirmer`, `Correction humaine`, `Appliqué`, `Refusé`, `Erreur d’extraction`. Inclure l’agent fonctionnel (ex. « Assistant disponibilité »), pas un préfixe de marque opaque.

Seuils métier par défaut à appliquer seulement si le backend retourne une confiance numérique calibrée :

| Confiance | Interprétation UX | Traitement |
|---|---|---|
| ≥ 0,90 | Élevée | Afficher preuves; suggestion prête à réviser; approbation requise pour les actions contrôlées |
| 0,70–0,89 | Moyenne | Signaler les champs à contrôler; révision explicite avant acceptation |
| < 0,70 | Faible | Demander correction humaine et confirmation additionnelle; aucun enchaînement automatique |

Un score du modèle n’est pas une probabilité métier tant qu’il n’a pas été calibré. En l’absence d’un score fourni ou calibré, afficher « confiance non évaluée » et raison/preuve, jamais 0 %, 100 % ou un score fabriqué. Une confiance élevée n’accorde jamais un droit d’action.

États du flux à distinguer : en attente, extraction en cours, suggestion prête, faible confiance, validation humaine requise, validé, rejeté, appliqué, annulé, expiré, remplacé, erreur. « Validé » ne signifie pas « appliqué ».

Chaque suggestion expose en langage métier : résumé, confiance avec explication, preuves utilisées, impact, risques, données manquantes, rôle requis, statut d’exécution et dernière mise à jour. L’utilisateur peut signaler une correction. Les réponses du modèle ne sont pas présentées avec la même emphase que les faits relus via une API ERP.

## Agents et surfaces d’assistance

- **Assistant de demande client :** document entrant → extraction → données manquantes → brouillon de devis.
- **Assistant disponibilité :** explique un conflit à partir du service Availability et suggère des équipements alternatifs que ce même service valide.
- **Assistant devis :** organise matériel et durée; prix et taxes viennent du service de tarification ERP.
- **Assistant contrat :** résume les clauses et les risques, sans signer ni confirmer.
- **Assistant check-in :** classe une observation et rédige un brouillon de note; gravité et coûts sont décidés par les règles métier.
- **Assistant parc :** signale anomalies/maintenance avec éléments source; changement de statut et quarantaine nécessitent autorisation.
- **Assistant client :** résumé relationnel et indicateurs traçables selon rôle et disponibilité des données.
- **Assistant finance :** explique les écarts à partir des rapports ERPNext et cite la période, filtres et données sous-jacentes.
- **Assistant opérateur :** centralise les éléments à examiner et donne accès à la source de chaque suggestion.

Points d’entrée : insight priorisé sur le dashboard; « Explain availability » sur les conflits; aide de parsing dans le composer; classification d’incident au check-in; synthèse client; résumé de contrat; alertes et explications P&L. Chaque point d’entrée transmet uniquement le contexte visible et autorisé.

## Composants

Les éléments d’interface de l’accueil IA sont des composants Vue 3 compilés par le bundler de Frappe (`public/js/cortex_home`, `public/js/cortex_copilot`). Les blocs de réponse (`verified_fact`, `assistant_text`, `extracted_data`, `proposal`, `approval_required`, `risk`, `missing_information`, `tool_progress`, `error`) sont rendus par `CopilotConversation.vue`. Un composant reçoit un statut et des données explicites, ne fait pas d’appel API caché, n’infère pas la confiance, n’exécute pas une action sur simple rendu.

## Intégration IA et sécurité technique

**Moteur actuel (ADR-006) :** passerelle IA interne `services/ai/` (Gemini, modèle et clé dans *Cortex AI Settings*, budget mensuel par société dans *Cortex AI Usage*, outils de lecture sous les droits de la personne connectée, propositions sans écriture). Onyx reste sélectionnable par `cortex_chat_provider = onyx` mais n'est plus le défaut; les puces Onyx ci-dessous ne valent que dans ce cas.

Flux attendu : Vue → API Frappe authentifiée → service Cortex → (a) Onyx pour orchestration et langage, (b) MCP privé pour outils autorisés → API métier Frappe/ERPNext. Onyx et Ollama ne parlent jamais directement à MariaDB. ERPNext garde les calculs et états canoniques.

- L’URL Onyx, le jeton serveur et la configuration Ollama sont stockés côté serveur (config Frappe ou gestionnaire de secrets), jamais dans le JavaScript servi, le bundle, le stockage du navigateur ou la télémétrie publique.
- Le serveur résout compagnie, utilisateur, agent, permissions, contexte, outils et modèle. Le client ne peut imposer aucun de ces choix.
- Liste d’outils explicite, vide si aucun outil n’est accordé. MCP applique de nouveau les scopes, l’entreprise et les règles d’approbation.
- Les outils métier reçoivent les identifiants nécessaires, pas un prompt libre faisant office de politique.
- Le contenu d’un document entrant est une donnée non fiable, pas une instruction système. Appliquer protections contre prompt injection, validation de schéma, limites de taille, contrôle de pièces jointes et citations.
- Les messages envoyés au client, décisions, erreurs et latence doivent être traçables avec identifiant de corrélation. Évite l’enregistrement de prompts/réponses bruts avec données personnelles; masque-les ou conserve-les selon une politique explicite de rétention.
- Tolérance aux délais, annulation, limites de débit, retries bornés/idempotents et erreurs fournisseur explicites. Ne retente jamais aveuglément une mutation externe.
- Onyx Lite local est adapté au chat/agents mais ne fournit pas l’indexation RAG complète. Déploiement standard si la recherche sur corpus et les connecteurs sont requis, avec ressources suffisantes.
- Ollama est un fournisseur de modèles, pas un ERP ni un moteur de règles. En développement local, `qwen3:8b` (Q4_K_M) est installé, configuré comme fournisseur Onyx et a répondu à une génération Ollama. Le compte administrateur Onyx existe et son authentification a été vérifiée. Le nom du modèle, l’URL et le jeton de chat sont configurés côté serveur Frappe; ne les copier ni dans ce document ni dans le frontend. Cette validation locale ne signifie pas que le chat Cortex→Onyx et les outils métier ont passé une recette de bout en bout. `qwen3.5:9b` a été écarté après un appel d’outil CPU de 2 min 45 s.

## Portail de devis, société dans la barre latérale, formulaires mobiles (2026-10-05)

- **Portail de devis** (ADR-007) : page publique `/devis/<jeton>` (`www/devis.*`, sans compte, responsive, imprimable) ; l'équipe crée un lien à copier ou envoyé par courriel depuis la location (« Partager avec le client »). Le client accepte, refuse ou demande une modification ; la réponse est auditée, avertit l'équipe, et **ne réserve rien**. Vérifié sur le bench : création, consultation anonyme, acceptation, double réponse refusée, lien périmé/révoqué. Le courriel sortant n'est pas configuré sur le bench (échec propre, lien affiché).
- **Après l'acceptation** : alerte en direct avec bouton « Réserver », bouton « Réserver maintenant » sur la location, réservation automatique optionnelle par société (désactivée par défaut), paiement de l'acompte dans le portail (Stripe, clés de la société; webhook signé) avec instructions manuelles en repli. Vérifié sur le bench avec une session Stripe simulée : facture payée, un seul paiement (rejeu ignoré), écritures équilibrées, signature invalide refusée; **non testé avec un vrai compte Stripe**.
- **Vérification de bout en bout par l'interface (2026-10-05)** : devis → partage → acceptation par le client sur le portail → bandeau et « Réserver maintenant » → demande de contrat → approbation par **une autre personne** → sortie par balayage des séries → retour → **clôture** → facture finale → paiement (écritures comptables équilibrées). Défauts trouvés et corrigés : (1) le retour par numéro de série n'additionnait pas les unités d'une même ligne, la location restait « Sorti »; (2) le propriétaire ne pouvait pas créer de demande d'approbation (droits); (3) aucun bouton pour **clôturer, annuler ou ouvrir un litige** (ajoutés, `rentals.change_state`); (4) Approuver/Refuser cachés dans un menu (maintenant directs; le demandeur voit pourquoi il ne peut pas décider); (5) « Enregistrer un paiement » caché dans un menu (maintenant direct).
- **Mon compte** (`cortex-account`) : profil et photo, mot de passe (ancien requis, force vérifiée, autres appareils déconnectés), appareils connectés, notifications courriel, société et rôles, usage de l'IA, activité récente. Toutes les actions visent seulement la personne connectée.
- **Page de devis refondue** (épurée, minimaliste, dense : lignes compactes, barre d'actions fixe en bas sur téléphone, tout le devis visible sans défiler sur un écran de 390 px).
- **Barre latérale** : tous les groupes sont repliables (chevron toujours visible; sans préférence, seul le groupe de la page courante est ouvert). **Fil d'Ariane** « Groupe › Page › Fiche » dérivé de la barre latérale (`cortex.NAV.locate`), sans flèche au début, dans la langue de l'interface. **Titres alignés** sur la barre latérale (« Locations », « Approbations », « Catalogue », « Disponibilité »…); dates des listes en français (Intl).
- **Plafond d'IA** : au plafond mensuel, passage automatique au modèle économique avec avis à la personne (ADR-006).
- **Courriel** : Amazon SES (`docs/ops/COURRIEL_SES.md`, non testé en réel).
- **Profil en bas de la barre latérale** (avatar, nom, courriel; menu profil, aide et support, déconnexion).
- **Coûts d'API** : `docs/architecture/COUTS_API.md` (Gemini 3.8 Flash 0,75 $ / 3,75 $ par M de jetons, plafond proposé 60 $ par société et par mois, Stripe 2,9 % + 0,30 $ CA, courriel). Prix à revérifier (tarif Gemini affiché jusqu'au 31 déc. 2026).
- **Barre latérale** : carte « Votre société » (logo et nom, fournis par `boot.cortex_home`) sous la marque ; groupe Administration séparé tout en bas.
- **Guide de démarrage** : bloc « Guide vidéo de Cortex Rental » (titre, description) au-dessus de l'emplacement « à venir ».
- **Formulaires sur téléphone** (`cortex-mobile.css`) : deux champs par ligne, repères de fuseau masqués, titre sur deux lignes, débordement de 3 px corrigé sur toutes les pages.
- **Rapport Utilisation IA** corrigé (agrégation côté serveur).

## Fonctions interconnectées : retenue, rappels, dommages, client 360, utilisation du parc (2026-10-05)

Principe : un événement saisi à un endroit doit se voir partout où il compte, sans ressaisie.

- **Retenue par un devis** (ADR-008) : créer un devis retient le matériel dans la disponibilité (réglage par société, 72 h par défaut, plafond 60 jours; prolongée au partage du lien). Les unités retenues sont déduites pour les autres devis et locations, ne comptent jamais contre le devis lui-même, et le matériel redevient libre à l'expiration **sans tâche planifiée** (la requête ne compte que les retenues actives non échues). La retenue se prend sous le verrou de réservation par équipement; si le stock manque, le devis est créé **sans retenue** avec la raison affichée. Boutons « Libérer / Reprendre la retenue » (`rentals.release_hold`, `rentals.renew_hold`). La retenue **n'est pas une garantie** : seule la réservation l'est. Grille de disponibilité : cellules hachurées « Retenu par un devis » et section « Sur la période ». Vérifié sur le bench; course de 12 devis simultanés pour 1 unité → exactement 1 retenue active, la course de la dernière unité reste à 1 réservation.
- **Rappels** (`services/reminders.py`, planificateur horaire) : retenue qui expire dans 24 h, retour en retard, devis sans réponse, facture échue. Notification pour la personne responsable, sans doublon sur 24 h; **aucun dossier n'est modifié**. Non vérifié avec une vraie planification dans le temps (testé en appelant les fonctions).
- **Dommages et pertes** (réglage par société, **désactivé par défaut**) : au retour, « Abîmé » facture le coût de réparation estimé (nouvelle colonne « Coût estimé ($) » du dialogue de retour) et « Manquant » facture la valeur de remplacement × un pourcentage (100 % par défaut). Lignes « Dommages et pertes » de la facture finale, écriture dans un compte distinct (4200). Vérifié : 250 $ + valeur de remplacement, écritures équilibrées. **À confirmer avec le comptable : les taxes sont calculées sur ces lignes comme sur la location.**
- **Fiche client 360°** (`customers.summary`, `public/js/cortex_customer.js`) : solde dû, total facturé, locations, retours en retard, devis ouverts (avec retenue), locations en cours; boutons « Nouveau devis » et « Voir ses locations ». Valeurs lues dans les dossiers, **aucune cote ni risque inventé**; les montants n'apparaissent que si la personne a accès aux factures.
- **Rapport « Utilisation du parc »** (Catalogue) : par équipement, jours loués, taux d'utilisation, revenus, revenus par unité, rendement sur la valeur de remplacement, avec une remarque (très demandé / peu loué). Locations Contrat, Sorti, Retourné et Clos seulement.
- **Assistant IA** : deux outils de lecture ajoutés (`customer_summary`, `late_returns`) sous les droits de la personne; ils n'écrivent rien.
- Vérification : `dev_tools/verifier_interconnexions.py` (dommages, écritures, rapport, client 360°, outils) et `charge_et_concurrence.py` (course des retenues).

## Mon compte v2, appareils connectés et approbations (2026-10-06)

- **Mon compte** (`cortex-account`, 7 onglets) : en-tête (photo, rôles, 5 chiffres des 30 derniers jours), *Profil*, *Statistiques* (période au choix : devis créés et taux de conversion, réservations, contrats, clôtures, matériel sorti et retourné, retours abîmés, équipements les plus sortis, factures et paiements enregistrés, approbations, usage de l'IA, graphique d'activité par jour), *Approbations* (historique de mes décisions et de mes demandes, avec motif; « auto-approbation » signalée), *Activité* (historique complet du journal d'audit, filtre par type et période, export CSV), *Sécurité*, *Notifications* (boîte de la cloche + alertes Cortex par personne + courriel), *Société et rôles* (rôles expliqués, droits écran par écran lus du serveur, équipe, usage de l'IA). Toutes les valeurs sont lues dans les dossiers (aucune estimation) et sont limitées à la personne et à sa société (`services/account_insights.py`).
- **Appareils connectés** (`services/devices.py`, DocType `Cortex Device Session`, crochet `on_session_creation`) : à chaque ouverture de session on garde l'agent utilisateur, d'où navigateur, système (iOS, Android, Windows, macOS…), type d'appareil, modèle quand il est fourni (Android), adresse IP et heure; seule l'empreinte SHA-256 de l'identifiant de session est conservée. **Déconnexion à distance** d'un appareil ou de tous les autres (vérifiée : l'iPhone déconnecté est renvoyé à la page de connexion, l'Android reste connecté), tracée dans le journal d'audit. Les administrateurs voient les appareils de l'équipe et peuvent déconnecter un appareil ou toutes les sessions d'une personne (`administration.team_devices`, `sign_out_member`); désactiver un membre ferme ses sessions. **Limites honnêtes** : l'agent utilisateur est déclaré par le navigateur; Windows 10 et 11 ne se distinguent pas; macOS ne donne pas sa version; l'adresse IP est celle que voit le serveur (derrière un proxy, celle du proxy sans en-tête de transfert); aucun lieu n'est déduit de l'IP; les sessions ouvertes avant cette fonction s'affichent « Non identifié ».
- **Bug des demandes d'approbation** : le bouton « Ajouter » ouvrait un formulaire brut sans moyen de le remplir correctement. Maintenant la création directe est interdite (`in_create`, redirection) et la liste offre « Demander une approbation » (choix d'une réservation). **Règle des deux personnes** : le demandeur ne peut ni approuver ni refuser sa propre demande, il peut la **retirer**. **Propriétaire seul** : s'il est la seule personne autorisée de la société, il peut décider de sa propre demande (réglage par société « Le seul approbateur peut décider de ses propres demandes », activé par défaut); la décision est inscrite « auto-approbation » dans l'audit. Dès qu'une autre personne autorisée existe, la règle des deux personnes revient. Vérifié avec `dev_tools/verifier_approbations.py` (tous les rôles) et par l'interface (demande → décision par une autre personne → contrat).
- **Alertes personnelles** : les rappels (retenue, retour en retard, devis sans réponse, facture échue) et la réponse d'un client à un devis respectent les préférences de chaque personne.

## Mon compte v3 : pages dédiées, une colonne (2026-10-06)

- **Groupe « Mon compte »** dans la barre latérale, avec sept pages dédiées (`/app/cortex-account/<page>`) : *Profil*, *Statistiques*, *Mes approbations*, *Activité*, *Sécurité*, *Notifications*, *Société et rôles*. Chacune a son titre, son sous-titre, son fil d'Ariane (« Mon compte › Page ») et son entrée active dans la barre. Les onglets horizontaux sont retirés. `cortex.NAV.locate` reconnaît les entrées `page/sous-page`.
- **Règles de mise en page** (à garder pour toute page de réglages) : **une seule colonne**, tout aligné à gauche, aucune colonne latérale qui laisse un grand vide; les tableaux ont du **remplissage** (le texte ne touche jamais la bordure); les tuiles d'une même carte ont la **même taille** et se répartissent en rangées égales; les listes longues se **plient** (appareils, connexions, équipe).
- **Rôles lisibles** : plus de pastilles de rôles techniques. Un profil en une phrase (*Propriétaire, Gestionnaire, Comptoir, Inventaire, Finance, Lecture seule*, `account_insights.role_summary`). Les noms de rôles traduits sont aussi simplifiés (*Propriétaire, Opérations, Comptoir, Inventaire, Finance, Consignation, Approbation des demandes*). Les droits sont affichés écran par écran, lus du serveur, avec un lien « Ouvrir » vers chaque écran.
- **Photo de profil** : cercle réel (80 px, `aspect-ratio`), téléversement d'une vraie image (PNG, JPEG, WebP, 3 Mo; vérifiée sur le bench) en cliquant la photo; elle remplace aussi l'avatar de la barre latérale.
- **Interconnexion** : chaque chiffre des 30 derniers jours (profil) et des statistiques ouvre la liste qui le compose (*Activité* filtrée par type et période); *Activité* a un mode « Toute l'équipe » (qui a fait quoi, qui a demandé, **qui a confirmé**) pour qui peut lire le journal d'audit; « Ce qui m'attend » (retenues qui expirent, réservations sans contrat, retours en retard, approbations à décider, factures échues) a un bouton d'action par ligne; des raccourcis (nouvelle location, mes devis, mes demandes, mes appareils); la page *Société* offre « Gérer l'équipe et les rôles », « Appareils de l'équipe » et « Activité de l'équipe » aux administrateurs.

## Équipe en ligne : infobulle (2026-10-06)

La pilule de la barre du haut n'affiche que les avatars des personnes en ligne avec leur point vert (aucun texte « N en ligne »). Au survol ou au focus, une infobulle liste chaque personne et ce qu'elle fait : l'écran affiché (« Disponibilité · Lighting », « Locations · CR-TRX-… »), sinon sa dernière action. L'écran est envoyé par le battement de cœur (`presence.ping(where)`), gardé 3 minutes en mémoire (texte brut, 80 caractères, jamais écrit dans un dossier) et visible seulement par les membres de la même société. Un clic ouvre toujours l'activité récente de l'équipe.

## Auto-approbation, export, logo, statistiques allégées (2026-10-06)

- **Auto-approbation du propriétaire seul : désactivée par défaut** (patch `disable_sole_approver_default` remet à zéro l'ancien défaut). Chaque société l'active elle-même, **seul le propriétaire**, après avoir lu une fenêtre qui explique ce que cela change (`services/approval_policy.py` : bénéfices, dangers, conseil) et coché « J'ai compris les risques » ; le serveur refuse l'activation sans cette confirmation et l'inscrit à l'audit (`cortex.approvals.self_approval_changed`). La fenêtre est offerte depuis un bandeau de la liste des approbations (quand la personne est la seule autorisée), depuis le formulaire d'une demande bloquée (« Comprendre et décider ») et depuis *Mon compte › Société et rôles*. La règle des deux personnes revient d'elle-même dès qu'une autre personne autorisée existe.
- **Libellé lisible** : le code interne de l'action (`rental.transaction.transition_to_contract`) n'est plus montré; le formulaire affiche « Confirmer un contrat · CR-TRX-… · demandée par … » (`cortex.approvalActionLabel`).
- **Statistiques allégées** : un résumé (4 chiffres et le graphique), puis une ligne pliable par domaine avec son résumé (Locations, Matériel, Facturation, Approbations, IA); le détail des tuiles se déplie à la demande.
- **Exporter** : un seul bouton « Exporter » ouvre une fenêtre qui demande **PDF ou CSV** (`cortex.exportData`, `public/js/cortex_export.js`). Le PDF est généré dans le navigateur (lettre à l'horizontale, pagination, accents; aucun service externe). Disponible sur *Activité* (moi ou équipe, jusqu'à 500 lignes) et *Mes approbations*. Vérifié : PDF ouvert et lu, CSV téléchargé.
- **Logo de la société** : étape « Ajouter le logo de votre entreprise » dans le guide de démarrage, carte « Logo de la société » (propriétaire seulement) dans *Société et rôles*; PNG, JPEG ou WebP de 2 Mo au plus (SVG refusé), copie publique, audit; il s'affiche dans la barre latérale, les devis envoyés et l'accueil. Le logo est maintenant une étape **obligatoire** de l'assistant de configuration (voir « Onboarding complet »).

## Administration fusionnée, dossier relié (2026-10-06)

- **« Mon compte » est fusionné dans « Administration »** (groupe du bas de la barre latérale) : Profil, Statistiques, Mes approbations, Activité, Sécurité, Notifications, Société et rôles, puis Équipe et règles, Site Web, Paramètres. Les routes restent `/app/cortex-account/<page>`; le fil d'Ariane lit « Administration › Page ».
- **Dossier relié** (`services/dossier.py`, `api/v1/dossier.py`, `public/js/cortex_dossier.js`) : en haut d'une **location**, d'une **facture** et d'un **paiement**, les liens vers tout ce qui s'y rattache (client, factures et solde dû, paiements, approbation et qui l'a décidée, retenue, retours, écritures comptables, auteur) et un « Historique du dossier » (qui a fait quoi, qui a demandé, qui a confirmé). Lecture seule, limitée à la société et aux droits de la personne. **Ordre de priorité des liens d'action (décision de Kael : commencer par les écrans les plus importants)** : 1. location, 2. facture, 3. paiement (faits); suivants : approbation, fiche client (déjà reliés), grille de disponibilité, tableau de bord.

## Onboarding complet : assistant de configuration (2026-10-06)

Décidé avec Kael : **assistant plein écran à l'arrivée** + **liste qui reste sur l'accueil** tant que ce n'est pas terminé. Le guide natif *Module Onboarding* (« Bienvenue dans Cortex ») est **retiré** (patch `remove_native_onboarding`); l'emplacement vidéo « à venir » est resté sur l'espace Cortex Rental (`cortex_desk.js`).

- **Page Desk `cortex-setup`** (`cortex_rental/page/cortex_setup/`, rôles Cortex System Manager / System Manager / Rental Manager; la route `cortex-onboarding` est prise par la liste du DocType). Monté dans `body` pour couvrir toute la fenêtre (barre latérale comprise); fenêtres et alertes Frappe passent au-dessus. Accès : arrivée (`cortex_desk.js`, si `bootinfo.cortex_home.setup_required_missing`), carte « Terminer la configuration » de l'accueil, Administration › Configuration.
- **Étapes** (`services/onboarding.STEPS`) : *Votre entreprise* (**obligatoire** : logo, adresse, ville, province, code postal, pays, devise, téléphone, courriel), *Vous, le propriétaire* (**obligatoire** : prénom, mobile, fuseau), *Votre équipe*, *Votre catalogue* (liens vers l'ajout/import), *Prix, taxes et règles* (TPS, TVQ, acompte), *Votre première location* (devis d'essai) : **facultatives, passables**.
- **Règles serveur** : `skip_step` refuse les étapes obligatoires (`not_skippable`); `complete_step` ne marque que les facultatives; `finish` refuse tant qu'une étape obligatoire manque (`required_missing`); le logo est exigé par `save_company_profile` (`logo_required`). Les étapes facultatives passées sont mémorisées (`skipped_steps`) et reviennent dans le récapitulatif (« Ouvrir »).
- **Retour arrière partout** : Retour, stepper cliquable, récapitulatif avec « Modifier »; la saisie est conservée (aussi après le téléversement du logo). Seul l'avancement est verrouillé tant qu'une étape obligatoire manque (un lien direct ramène à l'étape à faire).
- **Vérifié en navigateur** avec une société neuve (`dev_tools/verifier_onboarding.py`) : redirection à l'arrivée, refus sans adresse puis sans logo, téléversement du logo, refus sans mobile, passage des étapes facultatives, retour à l'entreprise (champs conservés), récapitulatif, fin; mobile 390 px sans débordement; comptes de démonstration non redirigés (sociétés marquées terminées).
- **Limites** : aucun courriel d'invitation réel envoyé en essai (dépend du service courriel); l'import de catalogue passe par l'outil natif *Data Import*.

## Préparation à la production (2026-10-06)

- **Stress test et fuzz** : `docs/audit/STRESS_TEST_2026-10-06.md` (0 erreur 5xx sur 6 210 requêtes hostiles, 4 courses de concurrence correctes, 0 fuite entre sociétés, 65 req/s à 40 utilisateurs sur gunicorn, 91 jours simulés sans violation d'intégrité).
- **Code défensif** : `services/defense.py` (vrais octets des images, frein global, limites par action, 429 au verrouillage, en-têtes de sécurité), `@defense.safe_input` sur tous les endpoints (valeur invalide = 417 en français), pagination bornée, dates et lignes de devis validées, test de contrat statique (`tests/test_defense.py`).
- **Comportement visible** : un trop grand nombre d'appels répond « Trop de demandes en peu de temps » (429); le compte se verrouille 5 minutes après 5 échecs de connexion; une période de location dont la fin précède le début est refusée (elle était facturée 1 jour).
- **Exploitation** : `docs/ops/DEPLOIEMENT.md`, `infra/production/` (nginx, supervisor, sauvegarde), `ops/predeploy.py` (contrôle avant mise en ligne), `health.health` et `health.ready`.
- **Reste à faire avant des clients payants** : clés réelles (courriel, Gemini, Stripe) à éprouver, TLS/domaine, revue de sécurité externe, 2FA des propriétaires, essai de charge du serveur de sockets.

## Niveau de vérité de l’implémentation

État vérifié le 2026-09-30 sur le bench de développement (Frappe/ERPNext 15.121) :

- **Vérifié :** redirection d’arrivée vers l’Accueil ; accueil sans violation axe WCAG 2.1 AA et sans débordement dès 320 px ; les 7 workspaces rendent onboarding, graphique, cartes de nombres, raccourcis et listes rapides avec les vraies données ; grille de disponibilité (équipements × jours, détail par cellule) branchée sur `availability.get_matrix` ; liste, Kanban, calendrier/Gantt et formulaire de *Location* ; retour de matériel enregistré de bout en bout depuis le dialogue natif ; les cinq rapports s’exécutent.
- **Accessibilité et écrans étroits :** `public/js/cortex_a11y.js` ajoute les noms accessibles que Frappe omet (boutons-icônes, cases de liste, filtres, grilles, menus déroulants) et `cortex-a11y.css` corrige les contrastes (gris « muted » de Frappe, calendrier) et le débordement des widgets à 320–375 px ; 0 violation axe WCAG 2.1 AA sur l'accueil, les 7 workspaces, la grille, la liste, le formulaire, le Kanban, le calendrier, le Gantt, les rapports et les approbations. Ces correctifs s'appliquent aussi aux écrans ERPNext d'origine ; ils sont ajoutés par script après rendu, donc un nouvel écran Frappe peut demander une règle de plus.
- **Limites honnêtes :** aucune clé API du modèle n'est saisie sur le bench (*Cortex AI Settings*) : l'accueil affiche alors le message de configuration renvoyé par le serveur au lieu d'une réponse; l'identifiant `gemini-3.8-flash` est à confirmer chez le fournisseur; les appels réels n'ont pas été testés (fournisseur simulé). Le plafond de coût est à déterminer (0 = aucun plafond). Les libellés d'ERPNext non traduits par Frappe restent en anglais. Un site vide affiche des zéros et des graphiques vides (pas de données de démonstration inventées). La grille de disponibilité est indicative (elle déduit « parc − quantités bloquantes du jour » des réservations renvoyées par le serveur) ; la vérification qui fait foi reste celle du serveur à la réservation. Sous 900 px, les tables de formulaire défilent horizontalement dans leur cadre.
- **Non reconstruit :** les écrans à deux colonnes de l’AI Workspace, le scan par caméra (le champ Code-barres de Frappe accepte un lecteur ou la saisie), les équipes/assignations.
- **Écritures comptables (vérifié sur 91 jours) :** journal à partie double par société (542 écritures, 0 déséquilibrée, écarts clients/encaisse/taxes à 0), rapports *Journal comptable* et *Balance de vérification*; le grand livre d'ERPNext n'est pas alimenté.
- **À recetter :** envoi réel du courriel de devis (compte de messagerie), parcours contrat → facturation → envoi client, droits réels par rôle, export vers le logiciel du comptable, conversation avec un vrai modèle (clé requise) et ses outils. Ne qualifie pas le produit de prêt pour la production.

## Definition of Done pour une évolution

1. Le parcours respecte les règles ERPNext et les permissions serveur.
2. Le comportement en succès, erreur, chargement, état vide, confiance faible, API indisponible et permission refusée est visible et honnête.
3. Aucune action métier n’est appliquée par le seul fait d’avoir rendu ou validé une suggestion.
4. Les sources, preuves et différences proposées sont consultables.
5. L’interface respecte ce langage ERPNext, est en français, et fonctionne au clavier / sur écran étroit.
6. `bench build`, `ruff` et les tests Python pertinents passent; les vérifications live sont identifiées comme telles, distinctes des mocks.
7. Documentation, endpoint et code racontent la même chose.
