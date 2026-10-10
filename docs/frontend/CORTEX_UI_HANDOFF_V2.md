# Cortex UI handoff v2 — ERPNext-first, AI-native

**Statut :** contrat produit canonique pour l’interface Cortex et les agents de développement.  
**Version :** 3.2 · 2026-10-07  
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

- **Première page après la connexion : Assistant IA** (décision de Kael du 2026-10-07). `HOME_ROUTE = "cortex-home"` dans `auth_hooks.py`; l’onboarding incomplet conserve sa route de configuration obligatoire. **Accueil IA** (Page Desk `cortex-home`, bundle `cortex_home.bundle.js`) : logo de la société, « Bonjour {prénom} », date du jour, saisie « Que puis-je faire pour vous ? », raccourcis, conversations récentes (`chat.list_sessions`). Le rail Cortex est replié par défaut sur cette page, sous réserve d'une préférence de barre latérale explicitement enregistrée. Le tableau de bord Cortex Rental reste accessible et ne doit pas être refondu. Le guide vidéo « à venir » appartient au workspace Cortex Rental seulement et ne doit pas être visible sur Assistant IA.
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

## Assistant IA : questionnaires guidés, mode démonstration, historique (2026-10-06)

Décidé avec Kael après la refonte de l'accueil IA :

- **État du moteur lu côté serveur** (`chat.status`) et affiché par une pastille dans la zone de saisie : « IA réelle · Gemini » (vert) quand un modèle est configuré et activé, « Démonstration » (ambre) sinon. L'interface ne le devine jamais ; sans réponse du serveur elle affiche « Démonstration ». Une bannière « Mode démonstration » (masquable dans les réglages, préférence locale) l'explique.
- **Mode démonstration honnête** (`services/ai/demo.py`) : sans clé de modèle, l'assistant ne comprend que quatre demandes (disponibilité, retards de retour, approbations en attente, catalogue), répond avec les vrais outils sous les droits de la personne, comprend une période écrite (« du 20 au 22 octobre ») ou le dit quand il ne la comprend pas, et ne calcule aucun prix. Aucun jeton, coût ni « vérification » inventés. Le repli aléatoire par mots-clés a été retiré.
- **Trois cartes = questionnaires guidés dans la conversation** (interface déterministe, sans modèle, **non enregistrés** dans l'historique du serveur) : *Nouvelle location* (client avec « nouveau client » → dates → équipement avec disponibilité calculée par le serveur → récapitulatif au prix du serveur → « Créer le devis » en brouillon, retenue lue après création), *Grille de disponibilité* (7 j / 30 j / dates + catégorie → mini-grille `availability.get_period_summary`, « Créer un devis avec ceci », « Ouvrir la grille complète »), *Demandes d'approbation* (liste, examen, Approuver / Refuser avec motif et confirmation, Retirer sa propre demande ; les droits viennent de `decision_options`, l'assistant ne décide jamais). Une proposition de l'assistant ouvre le même questionnaire : elle ne crée rien.
- **Historique** : tiroir à droite (recherche, groupes Aujourd'hui / Cette semaine / Plus ancien, ouvrir, retirer). Les messages de conversation sont immuables (journal) : « retirer » masque la conversation (`state = Hidden`), il ne détruit pas ses messages, et l'interface le dit. Réglages (engrenage) : bannière, effacer mon historique, lien « Budget et modèle IA » pour les administrateurs.
- **Fil d'Ariane** « Assistant IA › Conversation » dans la barre du haut ; « Assistant IA » revient à l'accueil sans toucher à l'historique. Pièces jointes : retirées tant qu'elles ne sont pas réellement traitées.
- **Pleine largeur** : le conteneur de 1290 px de Frappe est levé sur toutes les pages ; l'assistant garde une colonne de lecture d'environ 900 px. Barre latérale : Société → séparateur → Nouvelle location (ouverte et repliée), Administration ancrée au bas, juste au-dessus du profil.
- **Données de démonstration** : `dev_tools/jeu_de_demo.py` (`run`, `reinitialiser`) crée des devis, des réservations et trois demandes d'approbation de trois personnes différentes dans la société de simulation, retire l'article de test `SIM-STRESS-1` du catalogue, et refuse de s'exécuter hors d'un site de développement. Jamais en production.
- **Limites connues** : le vrai modèle (Gemini) n'a pas été essayé avec une vraie clé ; les formulaires gardent la barre latérale gauche native de Frappe.

## Chat : saisie ancrée, réponses en texte, modèles Cortex (2026-10-06, 2e lot)

Décidé avec Kael après essai de l'accueil IA :

- **Saisie collée au bas de l'écran** dans la conversation : le cadre occupe la hauteur de la fenêtre, le fil défile à l'intérieur (`.ch-thread`), la page ne défile pas. **Aucune ombre** derrière la saisie ni le bouton d'envoi (bordure fine seulement).
- **Réponses en texte normal, sans cadre ni fond de couleur** : faits vérifiés = titre + liste, sources repliées (« Sources (n) »), horodatage lisible ; avertissements = note à filet fin ; erreurs = phrase rouge sobre + « Réessayer » ; actions = boutons fantômes très discrets (plusieurs boutons consécutifs sur une seule rangée). Les propositions n'ont que trois actions : ouvrir le devis, la disponibilité ou les approbations (`proposal.action`), toutes via les questionnaires guidés.
- **Un type de bloc inconnu ne s'affiche jamais comme une erreur technique** : s'il porte du texte, il est montré comme texte ; sinon il est ignoré (avertissement console). Un refus de droits dans le mode démonstration devient une phrase claire.
- **Attente et apparition** : « Cortex réfléchit… » en texte *shimmer* pendant l'attente ; la réponse arrive d'un coup du serveur (pas de flux) et s'affiche mot à mot sur ~1,6 s au plus (animation d'un texte déjà reçu, désactivée si le système réduit les mouvements). Les outils réellement appelés s'affichent en une ligne (« Consultation des approbations ») avec un bref effet shimmer à l'arrivée. Un vrai suivi en direct des outils exigerait un flux serveur : non fait.
- **Modèles Cortex** (réglages *Cortex AI Settings*, section « Modèles Cortex proposés aux utilisateurs ») : **Cortex Rapide** (modèle des réglages, Gemini), **Cortex Équilibré** (`claude-sonnet-5-5`), **Cortex Avancé** (`claude-opus-5-5`). Chaque niveau a son identifiant, ses prix par million de jetons et son interrupteur ; il n'est offert que si la clé de son fournisseur existe (clé Gemini ou clé Anthropic, jamais envoyée au navigateur). La personne choisit le niveau dans la zone de saisie (le choix est mémorisé) ; le client envoie une **clé de niveau** (`rapide|equilibre|avance`), jamais un identifiant de modèle, et le serveur la valide. Le budget compte le **vrai coût du niveau utilisé** : un modèle plus puissant consomme le budget de la société plus vite, et l'interface affiche un indice de coût calculé à partir des prix saisis (pas une promesse). Un niveau demandé mais indisponible est refusé avec un message, jamais remplacé en silence. Au plafond de budget, le modèle économique existant prend le relais.
- **À vérifier avant la mise en service** : les prix par défaut des niveaux Équilibré et Avancé sont des valeurs de départ à confirmer auprès d'Anthropic ; l'identifiant Gemini est celui déjà saisi dans les réglages. Le fournisseur Anthropic est couvert par des tests de format (requête, outils, résultats) mais n'a pas été essayé avec une vraie clé.

## Plan de livraison demandé par Kael (2026-10-07)

Ce plan reprend la liste de demandes de Kael. Les phases sont livrées une à une pour examen avant d’entamer la suivante. Une demande marquée « existante à vérifier » ne doit pas être reconstruite sans avoir comparé le code, les contrats `api/v1.*`, les permissions et le service de domaine. Le tableau de bord principal est explicitement gelé : ne pas le refondre.

### Ordre et portée

| Phase | Priorité | Portée | État au 2026-10-07 |
|---|---:|---|---|
| 1 — Menu Société de « Nouvelle location » | Immédiate | Corriger le fond translucide du menu de sélection de société. | **Codé, non vérifié sur bench** (v0.8.0). Correctif CSS `public/css/cortex-desk-fixes.css` (chargé par `hooks.py`) : surface opaque, bordure et ombre. Contrôle de code seulement ; le rendu doit encore être confirmé sur un Desk Frappe actif. |
| 2 — Locations, disponibilité et navigation | 1 | Message erroné « La location n'est pas disponible pour la société active »; état réel du parc dans Disponibilité; « Nom du projet »; barre latérale (repli en bas, sous-groupes cachés, repliée sur l'Assistant IA); Assistant IA première page; page de société avec statistiques; chargement par page; saisie vocale honnête. | **Codé, testé hors bench** (v0.8.0), non vérifié sur bench ni dans un navigateur : voir « Phase 2 : ce qui est réellement livré » plus bas. |
| 3 — Administration, équipe et identité | 2 | Donner au propriétaire les commandes UI pour gérer les membres et règles; laisser tous les comptes consulter les profils et réserver la gestion des comptes au propriétaire; permettre au propriétaire de consulter l'activité de son équipe. Intégrer Configuration aux paramètres après l'onboarding, puis retirer la page dédiée. Faciliter la connexion d'un site Web et supprimer le défilement interne de sa barre latérale. Refaire Société et rôles, Notifications, Sécurité, Activité, Mes approbations, Statistiques et Profil pour les besoins propriétaire/équipe. Le profil doit présenter photo, nom, titre, courriel, téléphone, activité récente, état de présence, temps d'utilisation et moyen de contacter la personne lorsque les données existent. Densifier et rendre actionnables les paramètres ERPNext et utilisateur. Corriger l'alignement des panneaux de présence/activité, la lisibilité des notifications et l'icône bleue en conflit près des paramètres. Garder la messagerie entre collègues comme piste ultérieure, sans la présenter comme livrée. | **Partiel (v0.9.0), codé, testé hors bench** : profils de collègues en lecture, carte et entrée « Configuration » ajustées. Restent : voir « Phase 3 : ce qui est livré et ce qui reste ». |
| 4 — Réglages IA et fournisseurs | 3 | Auditer le sélecteur de niveaux et les réglages IA déjà présents. Étendre la configuration serveur des fournisseurs et modèles, leur activation et leur disponibilité au sélecteur; adapter le prompt système à Cortex et aux règles de la société. Les clés restent côté serveur. Vérifier avant activation les identifiants fournisseur de Gemini 3.8 Flash, Claude Sonnet 5.5 et GPT-6 Luna; Gemini 4 est « à venir » jusqu'à disponibilité officielle de son API. Aucune option indisponible ne doit sembler fonctionnelle. Corriger les commandes/réglages de démonstration et l'accent vert de Budget IA; conserver l'historique des conversations existant. | **Codé, testé hors bench** (v0.10.0) : prix corrigés, niveau Luna (OpenAI), « à venir », règles de la société dans le prompt. Aucun fournisseur essayé avec une vraie clé. Voir « Phase 4 ». |
| 5 — Finance, factures, paiements et catalogue | 4 | Ajouter un tableau de factures à Finance sans retirer ses raccourcis. Rendre Paiements plus visuel et afficher les informations utiles en premier lors de l'ouverture d'un client depuis un paiement. « Ouvrir la facture » doit ouvrir la facture correspondante. Simplifier l'impression avec des choix intégrés (A4 en priorité) pour factures et relevés/comptes, sans imposer la création d'un format. Corriger l'étiquette « Nouveau courriel » et sa casse. Rendre les paramètres plus denses/actionnables, simplifier adresse et contact, améliorer la visualisation du catalogue, afficher le statut Actif avec la casse prévue et aligner le prix d'entrée/achat avec la source de données réelle. Définir des modèles de taxes canadiens/québécois par défaut (TPS/TVQ), configurables par société et validés côté serveur. Laisser Clients et le tableau de bord principal tels quels sauf défaut précis confirmé. | **Partiel (v0.11.0), codé, testé hors bench** : tableaux de factures, paiements, formats A4/Lettre, modèles de taxes. Voir « Phase 5 ». |
| 6 — Portail client et demandes | 5 | Rendre le portail client simple pour soumettre une demande à l'entreprise, consulter un calendrier du matériel réellement disponible et suivre la réponse/approbation. Définir le parcours de signature et ses preuves avant de promettre une signature juridiquement valide. Ajouter le paiement par chèque (suivi/rapprochement par l'entreprise) et le paiement en ligne lorsque le fournisseur est configuré. | **Codé, testé hors bench** (v0.12.0) : demandes, calendrier public, suivi, chèque. **Signature définie, non livrée** (ADR-009). Voir « Phase 6 ». |
| 7 — Abonnements Cortex avec Stripe | 6 | Créer les plans et entitlements réels dans Stripe, facturer une société à 1 000 $ par mois comme prix de base demandé, émettre les factures automatiquement, puis permettre des modules/fonctions payants par société et des niveaux IA. Garder la séparation entre abonnement Cortex et paiements de location des clients. Protéger les webhooks, rendre les mises à jour idempotentes et contrôler les droits côté serveur. La devise, l'enveloppe IA incluse, les dépassements et les prix des options restent à configurer; aucun frais ne doit être activé en production avec des prix supposés. | **Codé, testé par événements simulés** (v0.13.0), **désactivé par défaut**, jamais essayé avec Stripe. Voir « Phase 7 » et ADR-010. |
| 8 — Mode sombre et finition transversale | 7 | Garder le mode clair par défaut; ajouter un choix clair/sombre dans les paramètres et appliquer un thème cohérent au Desk Frappe, workspaces, listes, formulaires, menus, dialogues, Assistant IA et pages Cortex. Repasser les contrastes, les états de chargement et les mouvements réduits sur les écrans couverts. | **Premier passage livré (v0.14.0)** : choix Clair / Sombre / Automatique, couche sombre générée, contraste audité sur 2 écrans réels. **Non vérifié sur un Desk Frappe** : voir « Phase 8 ». |

### Règles de livraison de ces phases

- Les phases 1 à 8 sont codées (v0.8.0 à v0.14.0), chacune dans son propre commit et sa propre version (voir `docs/releases/RELEASES_A_PUBLIER.md`). **Aucune n'est « vérifiée sur bench »** tant qu'un Desk Frappe actif ne l'a pas confirmée; seules l'accueil IA et la grille de disponibilité ont été vus dans un navigateur (composants montés hors Desk).
- Avant chaque écran métier, lire ses appels `cortex_rental.api.v1.*`, le service de domaine et les règles d'accès. Frappe/ERPNext reste le système de référence; pas de données de démonstration présentées comme réelles.
- Pour l'IA et Stripe, vérifier les identifiants, capacités, tarifs et états d'API auprès des fournisseurs au moment de l'implémentation. Le nom d'un modèle annoncé n'est pas une preuve de disponibilité.
- Maintenir ce plan et le niveau de vérité ci-dessous au fil des phases. Distinguer « codé », « vérifié sur bench », « testé en production » et « indisponible ».

## Phase 2 : ce qui est réellement livré (v0.8.0, 2026-10-07)

Vérifié par tests unitaires et de contrat (`pytest`, tests Node de la saisie vocale), `ruff`, compilation des composants Vue et vérification de syntaxe JavaScript. **Rien de ceci n'a été essayé sur un bench Frappe ni dans un navigateur** (aucun bench dans l'environnement de travail).

- **Société d'un dossier (cause du message « location non disponible pour la société active »)** : une personne autorisée sur plusieurs sociétés (ou un administrateur) n'a pas de société « active » côté serveur; le serveur prenait sa société par défaut et refusait la location d'une autre de ses sociétés. `get_company_context_for_document(doctype, name)` (`permissions/agent_scopes.py`) utilise la société du dossier **seulement si la personne y est autorisée**; un indice explicite (`X-Company-ID`, paramètre `company`) reste validé comme avant, et une société hors de l'ensemble autorisé est toujours refusée. Appliqué aux actions par location (`rentals.*`, `checkout.*`, `quote_share.create_share/list_shares`). Le client n'envoie pas d'en-tête : la correction est entièrement côté serveur.
- **Saisie vocale** : cause racine trouvée — l'en-tête `Permissions-Policy` envoyait `microphone=()`, qui interdit le micro à toute la page quel que soit le navigateur; il envoie maintenant `microphone=(self)` (`services/defense.py`). Le module `public/js/cortex_shared/cortexVoice.js` vérifie avant le clic (navigateur sans reconnaissance vocale, connexion non HTTPS, politique du serveur), traduit chaque code d'erreur du navigateur en message français avec la mesure à prendre (permission refusée, microphone absent, service désactivé, réseau, aucune voix), reprend une fois en `fr-FR` si `fr-CA` n'est pas pris en charge, affiche le texte provisoire pendant l'écoute et signale l'état dans une zone `role="status"`. Le bouton est grisé et explique l'indisponibilité. **Limites :** la reconnaissance est celle du navigateur (Chrome/Edge/Safari; Firefox n'en a pas) et le navigateur peut envoyer l'audio à un service de son fournisseur; non essayée avec un vrai microphone; HTTPS exigé hors `localhost`.
- **Arrivée sur l'Assistant IA** : `HOME_ROUTE = "cortex-home"`; les personnes dont aucun rôle n'ouvre cette Page retombent sur `cortex-rental` (`auth_hooks.home_route_for`).
- **Barre latérale** : la commande de repli est en bas du rail, au-dessus du profil; repliée, les sous-groupes sont cachés; sans préférence enregistrée, elle s'ouvre repliée sur l'Assistant IA et dépliée ailleurs (une préférence explicite gagne toujours). Le guide vidéo n'apparaît que sur l'espace Cortex Rental.
- **Disponibilité : état réel du parc** : la grille comptait comme libres les unités en quarantaine, en réparation, manquantes ou retirées, alors que `AvailabilityService` (qui fait foi) les exclut. `get_matrix` exclut maintenant ces unités du parc réservable et renvoie par équipement l'état des unités (`Serial No.cortex_status`) et le matériel actuellement sorti; la page les affiche en pastilles. Un article non sérialisé n'a **pas** d'état d'unité (`null`), jamais deviné.
- **Page de société** (Administration › Société et rôles; la carte « Votre société » de la barre y mène) : tuiles lues dans les dossiers (personnes actives, clients, équipements et unités, locations en cours, devis ouverts, retours en retard, facturé/encaissé/solde dû sur 30 jours). `account.company_stats` ne remplit un bloc que si la personne a le droit de lire ces dossiers; `null` = « hors de vos droits », jamais zéro.
- **« Nom du projet »** : libellé du champ directement en français.
- **Chargement par page** (`cortex_loading.js`) : fine barre et contenu estompé entre le changement de route et la fin des appels réseau, rien si la navigation est instantanée (180 ms), 10 s au plus, animation supprimée sous `prefers-reduced-motion`. Ce n'est pas un squelette propre à chaque écran.
- **Restent à faire (phase 2)** : confirmer le rendu sur un Desk actif (menu Société, barre repliée, pastilles de parc, tuiles de société), essayer la dictée avec un vrai microphone sur Chrome, Edge et Safari/iPhone, et mesurer l'effet de l'estompage sur les écrans lents.

## Phase 3 : ce qui est livré et ce qui reste (v0.9.0, 2026-10-07)

Testé hors bench (tests unitaires avec base simulée, tests de contrat) ; non essayé sur un Desk actif.

- **Profils consultables par toute la société** : `account.colleague_profile(email)` (GET) renvoie, pour une personne de **la même société seulement**, photo, nom, rôle en une phrase, courriel, téléphone, présence (en ligne = vu dans les 3 dernières minutes), date d'arrivée, connexions et actions des 30 derniers jours, 5 dernières actions. Une personne d'une autre société est refusée. Le nom, dans le tableau « Mon équipe » de *Société et rôles*, ouvre ce profil avec « Écrire un courriel » et « Appeler » quand la donnée existe. **Le temps d'utilisation n'est pas mesuré par Cortex : il n'est pas affiché** (renvoyé `null`, jamais estimé). Le titre de poste n'existe pas dans le modèle utilisateur : le rôle en tient lieu.
- **Gestion des comptes réservée au propriétaire** : vérifié par un test de contrat — changement de rôle, activation/désactivation, logo, appareils et déconnexion d'un membre exigent `_require_team_admin`; la lecture de la liste de gestion exige `can_manage_team`. Les règles tarifaires exigent le droit d'écriture Frappe.
- **Configuration** : l'entrée de la barre latérale n'apparaît que tant que la configuration initiale est incomplète (`boot.cortex_home.setup_pending`); le propriétaire retrouve l'assistant dans une carte « Configuration de l'entreprise » de *Société et rôles*. La Page `cortex-setup` n'est **pas** supprimée (elle reste la cible de l'assistant).
- **Activité de l'équipe pour le propriétaire**, **commandes de gestion des membres et des règles** : déjà présentes (*Activité › Toute l'équipe*, *Équipe et règles*), conservées.
- **Non fait (exige un Desk Frappe actif pour être jugé)** : alignement des panneaux de présence/activité, lisibilité des notifications, icône bleue en conflit près des paramètres, barre latérale du site Web sans défilement interne, refonte de Notifications/Sécurité/Activité/Statistiques/Profil, densification des paramètres ERPNext, retrait définitif de la page de configuration. La messagerie entre collègues reste une piste ultérieure, non livrée.

## Phase 4 : réglages IA et fournisseurs (v0.10.0, 2026-10-07)

Identifiants et prix **vérifiés le 2026-10-07** : page tarifaire officielle d'Anthropic, documentation OpenAI, fiche Gemini API (recoupée par plusieurs sources). Un identifiant publié n'est pas une preuve que votre compte y a accès : aucun appel réel n'a été fait (aucune clé).

- **Prix corrigés** : Claude Sonnet 5.5 = **2 $ / 10 $** et Claude Opus 5.5 = **4 $ / 20 $** par million de jetons (les anciens défauts de 3 $ / 15 $ et 15 $ / 75 $ gonflaient la dépense dans le budget IA de ~1,5× et ~3,75×). Patch `correct_ai_tier_prices` : ne remplace que les valeurs égales aux anciens défauts, jamais une saisie manuelle. Gemini 3.8 Flash reste à 0,75 $ / 3,75 $ **jusqu'au 31 décembre 2026**, puis 1,50 $ / 7,50 $ le 1er janvier 2027 : à mettre à jour dans les réglages.
- **Niveau Cortex Luna** (OpenAI `gpt-6-luna`, 0,10 $ / 0,50 $, contexte 1 M) : nouveau fournisseur `OpenAIProvider` (Chat Completions, `reasoning_effort: "none"` exigé pour l'appel de fonctions, un message « tool » par résultat). **Désactivé par défaut** ; il n'est offert que si la clé OpenAI (*Cortex AI Settings*, chiffrée, ou `openai_api_key` du site) existe **et** que le niveau est activé. Couvert par des tests de format seulement.
- **« À venir » honnête** : Gemini 4 n'a ni identifiant ni tarif publiés (vérifié) ; `chat.status` renvoie `upcoming`, et le sélecteur l'affiche grisé, jamais sélectionnable.
- **Prompt système** : ajout des règles de la société lues dans *Cortex Finance Settings* (taxes, acompte, retenue d'un devis, règle d'approbation) ; vide si rien n'est lisible. Les prix et statuts continuent de venir des outils.
- **Inchangé et déjà présent** : sélecteur Rapide/Équilibré/Avancé, budget au coût réel du niveau, historique des conversations. Un niveau demandé mais indisponible est refusé (`TierUnavailable`), jamais remplacé.
- **Non fait** : « commandes/réglages de démonstration » et « accent vert de Budget IA » (demande trop vague pour être jugée sans voir l'écran), recette avec de vraies clés.

## Phase 5 : finance, factures, paiements (v0.11.0, 2026-10-07)

Testé hors bench (dont un rendu Jinja réel des formats d'impression avec des données de facture) ; non essayé sur un Desk Frappe.

- **Finance** : deux listes rapides « Factures à encaisser » et « Factures récentes » ajoutées à l'espace, **sans retirer aucun raccourci** (vérifié par test).
- **Paiements** : liste avec indicateurs (paiement vert, remboursement orange), sans bouton « Ajouter » (un paiement s'enregistre depuis la facture, le serveur valide le montant et les droits). À l'ouverture d'un paiement, l'en-tête montre d'abord le client : solde dû, nombre de locations, retours en retard (`customers.summary`, lecture seule, droits vérifiés). Le bouton « Ouvrir la facture » du paiement ouvre `frm.doc.invoice` (vérifié dans le code; le défaut signalé n'a pas pu être reproduit sans Desk actif).
- **Impression** : formats intégrés **Facture Cortex A4** (par défaut, patch `set_invoice_print_defaults` qui n'écrase jamais un choix existant) et **Facture Cortex Lettre**; aucun format à créer. **Non fait :** relevé de compte client imprimable (aucune construction native testable sans bench).
- **Modèles de taxes** (`services/tax_presets.py`, `billing.tax_presets` GET, `billing.apply_tax_preset` POST audité, bouton « Appliquer un modèle de taxes » sur les réglages financiers) : *Québec (TPS 5 % + TVQ 9,975 %)*, *TPS seule*, *Aucune taxe*. Droit d'écriture requis; chaque taux reste borné de 0 à 30 % par le serveur. **Limite :** le modèle de données porte deux taux; les provinces à TVH ou à taxe provinciale distincte ne sont pas couvertes (saisie manuelle). À confirmer avec le comptable.
- **Libellé** « New Email » traduit par « Nouveau courriel » (`fr.csv`).
- **Non fait** (demande trop vague ou dépendante d'un Desk actif) : densification des paramètres, simplification adresse/contact, visualisation du catalogue, casse du statut « Actif », alignement du « prix d'entrée/achat » (le catalogue ne porte pas de prix d'achat : rien n'a été inventé). Clients et tableau de bord laissés intacts.

## Phase 6 : portail client et demandes (v0.12.0, 2026-10-07)

Contrat complet : [`ADR-009`](../adr/ADR-009-portail-client-et-signature.md). Testé hors bench (validation, calendrier, rendu réel des pages avec Jinja, syntaxe du JavaScript embarqué) ; **non essayé dans un navigateur ni sur un bench**.

- **Demandes** : `/demande/<identifiant>` (sans compte) crée une *demande entrante* (canal « Web Portal ») ; elle **ne réserve, ne bloque et ne facture rien**. Chaque société active son portail et choisit son identifiant dans *Cortex Finance Settings* (`portal_requests_enabled`, `portal_slug` unique, validé). Un portail désactivé répond comme un portail inexistant. Protections : limite par IP, champ piège, consentement obligatoire, plafond de 50 demandes/société/jour, texte nettoyé de toute balise, matériel restreint aux équipements de la société.
- **Calendrier du matériel** : `portal_calendar` renvoie, par équipement et par jour, *libre / limité / complet / non offert* — **sans quantité, sans client, sans numéro de dossier** (même règle que la grille interne; `availability_summary.day_statuses`). Indicatif ; la vérification qui fait foi reste celle du serveur à la réservation.
- **Suivi** : `/suivi/<jeton>` (empreinte SHA-256 seulement) montre l'état (*reçue / en examen / traitée / refusée*), la période, le matériel et le **message que l'équipe écrit au client** (champ « Message au client » de la demande). Ni courriel ni téléphone. L'équipe voit les demandes dans la liste « Demandes du portail » de Finance et reçoit une notification en direct.
- **Chèque** (option par société : `accept_cheque`, `cheque_payable_to`) : le client annonce un chèque sur la page du devis accepté ; la facture d'acompte est créée (sa référence se met au dos du chèque), l'équipe est prévenue, la liste « Chèques annoncés » de Finance suit les annonces. **Rien n'est marqué payé** : l'entreprise enregistre le paiement en mode « Chèque » à la réception, et la page du client passe à « payé » (rapprochement `billing._sync_share_payment`).
- **Paiement en ligne** : inchangé (ADR-007), offert seulement si les clés Stripe et le secret du webhook existent. Non essayé avec un vrai compte Stripe.
- **Signature** : **aucune signature n'est offerte.** Le parcours (document figé et son empreinte, identité vérifiée, horodatage, preuves, valeur juridique à faire valider par un avocat) est défini dans l'ADR-009 ; l'interface parle d'« acceptation », pas de « signature ».
- **Limites** : aucun courriel de confirmation au demandeur (le lien de suivi s'affiche à l'écran) ; les demandes du portail n'alimentent pas encore l'extraction par IA ; pas de compte client ni d'historique par personne ; page d'accueil du portail et personnalisation visuelle non faites.

## Phase 7 : abonnements Cortex avec Stripe (v0.13.0, 2026-10-07)

Contrat complet : [`ADR-010`](../adr/ADR-010-abonnements-cortex.md). Testé par signatures et événements Stripe simulés (29 tests); **aucun compte Stripe n'a été utilisé et rien n'est activé**.

- **Désactivé par défaut et sans effet** : tant que *Cortex Subscription Settings* (réservé à *System Manager*) n'est pas activé, aucune restriction et aucun frais. L'activation est **refusée par le serveur** sans clé Stripe, secret de webhook, identifiant de prix et **confirmation humaine du prix** (1 000 $ par mois est le prix de base demandé, pas un prix supposé facturé). Chaque option offerte exige son `price_…` et sa confirmation.
- **Séparation** : abonnement Cortex = compte Stripe de la plateforme; acompte de location = clé de chaque société. Deux webhooks et deux secrets (`subscription_webhook`, `stripe_webhook`).
- **Droits côté serveur, écrits seulement par le webhook signé** : signature vérifiée (fraîcheur 5 min), événement traité une fois (*Cortex Stripe Event*), événements hors d'ordre ignorés, prix inconnus sans effet. Niveaux d'IA non acquis refusés (`TierUnavailable`) et montrés « Non inclus »; module `portal` non acquis = portail inexistant. Retard de paiement : accès conservé pendant les relances de Stripe, puis retiré à l'annulation.
- **Propriétaire** : carte « Abonnement Cortex » dans *Société et rôles* (état, plan de base, options, « Souscrire » → Stripe Checkout, « Gérer l'abonnement » → portail Stripe). Le catalogue affiché n'a ni secret ni identifiant Stripe.
- **Facturation automatique** : Stripe émet les factures et prélève (mode abonnement); Cortex n'émet rien de lui-même.
- **À décider par une personne (non supposé)** : devise, prix de base final, prix et existence des options, enveloppe d'IA incluse (0 par défaut), sociétés exemptées, taxes. **Non fait :** facturation des dépassements d'IA, essai gratuit, rabais, essai avec un compte Stripe de test.

## Phase 8 : mode sombre et finition (v0.14.0, 2026-10-07)

- **Clair par défaut.** Choix **Clair / Sombre / Automatique** dans *Mon compte › Profil › Apparence*, enregistré côté serveur pour la personne seule (`account.set_theme`, POST limité, valeurs `Light|Dark|Automatic` validées; champ standard `User.desk_theme`) et appliqué tout de suite (`cortex.applyTheme`, attribut `data-theme` que Frappe utilise pour son propre mode sombre). Sans choix enregistré : clair.
- **Couche sombre Cortex générée** (`bin/generate-dark-theme.mjs` → `public/css/cortex-dark.css`, chargée en dernier) : relit les règles existantes (feuilles de style et blocs `<style>` des composants Vue) et réécrit chaque couleur de fond, de texte et de bordure avec une palette sombre, **uniquement sous `html[data-theme="dark"]`** — le mode clair n'est pas touché (test : aucune règle hors du sélecteur sombre). Les boutons presque noirs deviennent clairs avec leur texte inversé; les teintes (vert, ambre, rouge, bleu) et les propriétés locales (`--ok`, `--full-bg`…) suivent. Régénérer après une modification de style : `NODE_PATH=… node bin/generate-dark-theme.mjs` (dépendances `postcss`, `@vue/compiler-sfc`).
- **Vérifié, pour de vrai, dans Chromium** (composants montés avec un faux `frappe`, pas dans un Desk) : l'**accueil IA** et la **grille de disponibilité** (avec les pastilles d'état du parc de la phase 2), en clair et en sombre. Audit automatique du contraste de chaque texte rendu : **0 texte sous 4,5:1 en clair et en sombre** sur ces deux écrans (118 textes sur la grille). Captures : `docs/review/captures/mode-sombre/`. Ces captures ont servi à corriger deux défauts de la première version (gris-bleu « ardoise » pris pour du bleu d'accent; jetons de teinte sans repli).
- **Contraste de la palette** : test (WCAG) sur chaque niveau de texte et chaque couleur sémantique contre chaque surface; il a trouvé et fait corriger un jeton à 4,42:1.
- **Non vérifié** : la barre latérale, *Mon compte*, l'assistant de configuration, le copilote, les dossiers reliés et tout le Desk de Frappe (listes, formulaires, menus, dialogues) en sombre. La couche est appliquée à ces écrans mais **aucun n'a été vu** (il faut un Desk actif); le mode sombre natif de Frappe dépend de sa propre feuille de style. Les pages publiques (devis, demande, suivi, connexion) suivaient déjà le réglage du système. À faire par une personne : parcourir chaque écran en sombre et signaler les défauts.
- **Finition transversale** : états de chargement par page et `prefers-reduced-motion` respectés (phase 2); aucun nouveau mouvement n'a été ajouté.

## Suite demandée par Kael (2026-10-07, après v0.14.0) : phase 9

Demandes reçues après la livraison des phases 1 à 8. **Aucune n'est encore codée au moment de cette entrée** ; l'état de chacune est mis à jour ici à mesure qu'elle est livrée. Décisions de Kael prises dans ce message :

| # | Demande | Décision / portée | État |
|---|---|---|---|
| 9.1 | Abonnements : prix, devise, options offertes, enveloppe d'IA incluse, sociétés exemptées | Créer des **valeurs par défaut modifiables** (réglages préremplis, rien n'est facturé tant que les prix ne sont pas confirmés) | **Codé (v0.15.0)** : patch une fois + bouton « Remplir avec les valeurs par défaut » ; détail ci-dessous |
| 9.2 | Acceptation / signature du contrat | **Pas d'avocat requis** (remplace la condition de l'ADR-009). Ajouter d'abord un **consentement explicite** : le client coche qu'il a lu et compris les conditions du contrat avant de signer. **La société peut modifier le contrat** (modèle de conditions propre à chaque société) | **Codé (v0.15.0)**, vu à l'écran dans Chromium |
| 9.3 | Portail des demandes : identité | Logo de l'entreprise bien visible, **pied de page « Cortex »** | **Codé (v0.15.0)**, vu à l'écran (portail, suivi, devis) |
| 9.4 | Image de marque configurable (nice to have) | Configurer les images dans l'ERP (bannière, photos d'équipement) et les **refléter chez les clients** (portail, devis) ; seuls les fichiers publics sont exposés | **Codé (v0.15.0)** : logo, bannière, phrase d'accueil, couleur d'accent, photos d'équipement |
| 9.5 | Écran « Demande reçue » | Plus dense, plus rempli et **plus interactif** (récapitulatif, étapes, copie du lien, ajout au calendrier, etc.) | **Codé (v0.15.0)**, vu à l'écran (ordinateur, téléphone, sombre) |
| 9.6 | Voir et corriger ce qui n'avait pas été vu à l'écran | Barre latérale, *Mon compte* (Apparence, Abonnement, statistiques de société, profils), assistant de configuration, formulaires du Desk (paiement avec le client en tête, réglages de taxes), formats d'impression de facture | **Contesté par Kael le 2026-10-07 (v0.15.1)** : vu seulement dans un banc d'essai hors Desk, pas dans l'application réelle ; la barre latérale et le mode sombre sont signalés comme ne correspondant pas à la demande. Voir « Phase 9.6 » ci-dessous |
| 9.7 | Retours de Kael sur le portail (2026-10-07) | Vraies photos de Sony α7 IV pour juger les vignettes ; expliquer le **orange** du portail ; le logo « Propulsé par Cortex » doit mener au **site Web de Cortex** ; « Demande reçue » **trop compacte** → plus d'espace, vue épurée ; **Copier le lien** en **icône** sur petit écran ; FAQ plus soignée | **Codé (v0.15.1)**, vu à l'écran (ordinateur, téléphone, sombre) ; l'adresse du site de Cortex est à **configurer** (voir ci-dessous) |

Ordre d'exécution voulu : Handoff d'abord, puis commit, push et notes de version, avant tout autre travail. **Les tags et Releases GitHub restent impossibles à créer depuis l'environnement** (poussée de tags refusée par le dépôt, outil sans création de release) : voir `docs/releases/RELEASES_A_PUBLIER.md`.

## Phase 9 (v0.15.0) : valeurs par défaut, consentement, image de marque, « Demande reçue »

Vu à l'écran dans Chromium (portail, suivi et devis rendus avec Jinja, API simulée) ; testé hors bench. Non essayé sur un Desk Frappe (les formulaires de réglages et leurs boutons n'y ont pas été montés).

- **9.1 Valeurs par défaut des abonnements** (`subscriptions.default_settings`, patch `seed_subscription_defaults`, bouton « Remplir avec les valeurs par défaut » sur *Cortex Subscription Settings*) : devise **CAD**, prix de base **1 000 $/mois**, enveloppe d'IA incluse **60 $/mois** (celle du budget par défaut d'une société), plan de base incluant le niveau *Rapide*, options offertes **Portail client 49 $**, **Équilibré 99 $**, **Avancé 249 $**, **Luna 19 $**, et **toutes les sociétés existantes exemptées**. Tout est modifiable. Le patch ne s'exécute qu'une fois et seulement si rien n'a jamais été configuré. **Les prix des options (49/99/249/19) sont des valeurs de départ inventées pour amorcer les réglages, non des prix décidés.** La facturation reste désactivée, aucun prix n'est confirmé et aucun identifiant Stripe n'est saisi : rien ne peut être facturé avant la confirmation humaine.
- **9.2 Consentement et conditions** : voir l'ADR-009 (section « Acceptation et signature »). Case obligatoire « J'ai lu et compris… » avant d'accepter, conditions modifiables par société avec modèle de départ et version, instantané par devis, preuves conservées. **Ce n'est pas une signature certifiée** ; le modèle de départ n'est pas un avis juridique.
- **9.3 Identité du portail** : logo de la société (40 px), bannière et phrase d'accueil optionnelles, couleur d'accent (clair seulement), **pied de page « Propulsé par Cortex »** sur le portail, le suivi et le devis.
- **9.4 Images configurables dans l'ERP et reflétées chez les clients** : champs *Bannière du portail*, *Phrase d'accueil*, *Couleur d'accent* (*Cortex Finance Settings*) et *Photo de l'équipement* (*Cortex Rental Item Profile*). **Seuls les fichiers publics (`/files/…`) sont exposés** ; un fichier privé est ignoré (testé), la bannière privée est refusée à l'enregistrement, la couleur est validée (#RRGGBB) et le texte du bouton reste lisible sur elle (≥ 4,5:1). Les photos apparaissent dans le calendrier du portail, la page de suivi et les lignes du devis.
- **9.5 « Demande reçue »** : récapitulatif complet (période et nombre de jours, demandeur, coordonnées, matériel avec photos et quantités, message), frise des prochaines étapes, lien de suivi avec **Copier le lien**, **Ouvrir le suivi**, **M'envoyer le lien par courriel** (message prérempli), **Ajouter au calendrier** (fichier .ics valide, vérifié), **Imprimer / PDF**, **Faire une autre demande**, questions fréquentes dépliables. Formulaire plus interactif : étapes, quantités par équipement, compteur de caractères, résumé en direct. Page de suivi : frise d'avancement, cartes, mêmes actions.
## Phase 9.6 et 9.7 (v0.15.1) : vérifications à l'écran et retours sur le portail

**Avertissement (retour de Kael, 2026-10-07) :** tout ce qui suit a été « vu » dans un **banc d'essai à moi** : des fichiers du produit montés dans Chromium avec un **faux `frappe`**, **ma propre feuille de style de page** (fond, polices, boutons) et des données inventées. Ce banc ne reproduit ni le Desk de Frappe, ni son mode sombre natif, ni les autres feuilles de style de Cortex. Les mentions « vu à l'écran / corrigé » ci-dessous valent donc **pour ce banc seulement**, et la phrase « le rendu global est bon » était **fausse à l'échelle de l'application**. Kael rapporte, sur l'application réelle : la barre latérale ne correspond pas à ce qui avait été demandé, le **mode sombre ne fonctionne pas**, plusieurs pages ne ressemblent pas au reste de l'application, et « Votre société en chiffres » n'est que « pseudo correct ». **Non diagnostiqué** : je n'ai pas de captures de l'application réelle. Piste (non vérifiée) pour le sombre : la couche `cortex-dark.css` n'est générée qu'à partir de 5 feuilles CSS et 7 composants Vue ; `cortex-theme.css`, `cortex-utilities.css`, `cortex-login.css`, `cortex-mobile.css`, les espaces de travail et les formulaires du Desk ne sont pas couverts. Tests Python hors bench verts. **Rien n'a été essayé sur un Desk Frappe actif.**

**Vu à l'écran, défauts trouvés et corrigés**
- **Barre latérale** (v0.15.0 et suite) : repli, bascule en pied, tiroir mobile, sombre ; pastille « réduit » et carte de société en mobile corrigées dans `cortex-nav.css`.
- **Mon compte**, onglets *Profil* (carte **Apparence** : le choix Sombre pose `data-theme="dark"` et l'alerte « Apparence enregistrée. » s'affiche), *Société* (**abonnement**, **statistiques de société**, droits, équipe) et la **fiche d'un collègue** (fenêtre). Défauts réels corrigés : en sombre, les **lignes des tableaux** (« Mes droits », « Mon équipe ») restaient **blanches avec un texte clair**, donc illisibles (surfaces blanches codées en dur dans `cortex-theme.css`, absentes de la couche sombre générée : ajoutées au générateur, régénéré ; la correction des lignes de tableaux est vue à l'écran, celle des boutons `.cx-btn`, compteurs, puces et tiroir **ne l'est pas**) ; le plafond d'IA s'affichait « 12.40 $ / 60 $ » (point décimal) au lieu du format canadien-français commun à la page ; l'activité récente du collègue se coupait en deux lignes ; les noms de l'équipe prenaient le bleu de lien par défaut.
- **Assistant de configuration** (`cortex-setup`) : étapes Entreprise, Équipe, Prix et taxes, Récapitulatif en clair, sombre et téléphone : aucun défaut visuel trouvé. Les enregistrements n'ont pas été exécutés (API simulée).
- **Formats d'impression de facture** A4 et Lettre : logo de la société ajouté, marge du bloc de notes ; PDF produits par Chromium.
- Le `TypeError … 'map'` vu dans le harnais venait d'un **jeu d'essai erroné** (la liste « Ce qui m'attend » est renvoyée dans `{items: […]}` par le serveur), pas du code du produit.

**Pas vu à l'écran : formulaires du Desk** (paiement avec le client en tête, réglages de taxes, boutons de modèles de taxes). Ils reposent sur `frappe.ui.form` et la page Desk complète : le code passe `node --check` et les tests de contrat, mais **il faut les ouvrir sur un bench** avant de les déclarer recettés.

**9.7 Retours sur le portail**
- **Pourquoi du orange ?** Ce n'était **pas la couleur par défaut** : le portail utilise le **vert Cortex `#066336`** tant qu'aucune couleur d'accent n'est réglée (*Cortex Finance Settings › Couleur d'accent*). L'orange venait de mon société d'essai fictive (accent `#7c2d12` et bannière orange) dans les captures. L'accent configuré ne s'applique qu'en mode clair ; en sombre le portail garde le vert clair Cortex.
- **Pied « Propulsé par Cortex »** : le logo et le texte forment un lien (nouvel onglet, `rel="noopener"`) vers le site de Cortex **quand l'adresse est configurée** : `bench --site <site> set-config cortex_site_url https://…` (https seulement, vérifié par `brand.site_url`). **L'adresse du site Web de Cortex n'existe nulle part dans le dépôt : je ne l'ai pas inventée.** Sans valeur, le texte reste sans lien. Le logo passe à la version claire en mode sombre.
- **« Demande reçue »** : une seule colonne, une idée par carte (récapitulatif, matériel, prochaines étapes, lien de suivi, questions fréquentes), plus d'espace, référence en pastille, pastille de lettre quand un équipement n'a pas de photo. **Copier le lien** devient une **icône** sous 560 px (nom accessible conservé) ; les actions ont des icônes ; la FAQ a des chevrons et plus d'air.
- **Photos d'essai** : deux vraies photos de **Sony α7 IV** (Wikimedia Commons, **CC0**, Bautsch) ont servi à juger les vignettes ; elles restent hors du dépôt (jeu d'essai local).


## Plan du pilote « avant lundi » (2026-10-10) : état réel

Demandé par Kael : IA complètement fonctionnelle, migration de données accessible à de gros volumes, toutes les pages d'un ERP, Gemini 3.8 à l'essai, PostHog.

| Point du plan | État vérifié dans le code | Reste |
| --- | --- | --- |
| Modèle Gemini 3.8 | `gemini-3.8-flash` est le défaut de *Cortex AI Settings* (patch `set_ai_pricing_defaults`), repli `gemini-3.5-flash-lite`, plafond puis modèle économique. Prix annoncé jusqu'au 31 déc. 2026. | **Jamais essayé avec une vraie clé** dans le Desk. Premier essai réel = premier critère de réussite du pilote. |
| PostHog | **Codé (cette livraison)** : `services/analytics.py`, `public/js/cortex_analytics.js`, boot `cortex_analytics`. Éteint sans `posthog_key`. Masquage par défaut des données d'affaires. | Créer le projet PostHog, régler la clé, tester dans un Desk ; avis de confidentialité aux utilisateurs du client ; réglage individuel dans Mon compte ; événements métier explicites (`cortex.track`) à ajouter écran par écran. |
| Migration de données | Existe seulement par l'*Importation de données* native de Frappe (liens dans Administration et Catalogue ; historique par société). **Rien de propre à Cortex** : pas de modèles de fichier par type, pas de validation avant import, pas de reprise. | `max_file_size` est à 10 Mo dans l'exemple de production : trop petit pour des centaines de milliers de lignes. Vérifier sur bench la limite de lignes par importation de Frappe v15 et la tenue du travail en arrière-plan avant de promettre ce volume. |
| Pages d'un ERP complet | Locations, disponibilité, approbations, sorties/retours, catalogue, séries, clients, factures, paiements, finance, abonnements, portail. | Écart non mesuré : achats/fournisseurs, inventaire/entrepôts, paie, rapports comptables ne sont pas des écrans Cortex. À décider avec Kael ce qui est « nécessaire » pour le pilote. |

Rien de ce tableau n'a été essayé sur un Desk Frappe actif.

## Phase 10 : IA native — actions, cartes dédiées, statistiques (2026-10-10, EN COURS)

> **Règle de travail de Kael (2026-10-10) :** avant un gros chantier, écrire le plan ici et le pousser ; à la fin de chaque phase, mettre cette section à jour (**fait / reste à faire / pourquoi ces choix**), pour qu'une autre personne reprenne vite. Ne jamais redessiner la page Assistant IA sans proposition validée (maquette d'abord) ; corriger seulement les défauts sûrs. Demander plutôt que supposer. Pas de travail difficile à annuler.

### Intention de Kael
« AI native » ne veut pas dire que tout passe par l'IA : **beaucoup d'actions restent manuelles**, mais **l'IA de Cortex doit pouvoir tout faire dans l'application** (et s'améliorer avec les modèles). Un seul système pour toute société de location (caméras, équipement, véhicules…), adaptable (colonnes, sections, catégories de pages). Le chat doit être riche et interactif (cartes dédiées pour chaque action, cartes de statistiques avec une flèche vers l'endroit d'où vient le chiffre), au design de Cortex.

### Décisions prises (avec Kael) et pourquoi
| Décision | Pourquoi |
| --- | --- |
| Propose → aperçu → **approbation humaine** → exécution (ADR-011) | Garde « Cortex suggère, l'humain décide » ; l'IA ne contourne ni droits ni audit |
| Exécution avec **les droits de la personne**, par la même fonction que l'écran | Une seule voie d'écriture à tester ; aucune élévation de privilèges |
| **Carte dédiée (maquette B)** pour chaque action | Choix de Kael ; aperçu en tableau, totaux, état (à approuver, fait, refusé, périmée, échec) |
| Changements de structure : **aperçu + approbation du propriétaire**, un **site par client** | Un site par client isole `Custom Field`/`Property Setter`/`Workspace` ; le propriétaire garde la main ; annulable |
| Secteurs : **modèles de secteur + IA** | Prévisible pour le client, flexible grâce à l'IA |
| Interrupteur de site `cortex_ai_actions` (éteint par défaut) | Réversible en une commande ; rien ne s'active sans validation |
| L'état d'une carte vient **toujours du serveur** (`actions.refresh_blocks`) | Une carte approuvée ne redevient jamais « à approuver » au rechargement |
| Statistiques : **données réelles seulement**, lien `/app/...` vérifié (`stats.safe_href`) | Aucune estimation inventée ; jamais de lien externe |

### Fait (poussé sur la branche `claude/fervent-thompson-fs0kg0`, PR #15)
- **Moteur d'actions** (`services/ai/actions.py`, DocType `Cortex AI Action`, `chat.decide_action`) : créer un client, créer un devis. Revalidation, verrou, point de sauvegarde, audit. Tests : `test_ai_actions.py`.
- **Blocs de chat** `action_card` et `stat_card` (`chat_schemas.py`) ; outils de lecture `finance_trend`, `rentals_by_state` et carte pour `finance_summary` (`services/ai/stats.py`, tests `test_ai_stats.py`). Format canadien-français (`stats.money`, `stats.human_dt`).
- **Composants Vue** : `CopilotActionCard.vue` (carte dédiée, choix B de Kael), `CopilotStatCard.vue` (KPI, barres ou ligne en SVG, flèche en haut à droite vers la source), branchés dans `CopilotConversation.vue` (l'accueil IA les reçoit aussi). `chatClient.js` : `decideAction`, `openDeskPath` (chemin `/app/...` revérifié, `route_options` pour les listes filtrées).
- **Mode sombre** : `cortex-dark.css` régénéré (+140 lignes, rien retiré).
- **Banc d'essai réutilisable** : `tools/ui-harness/` (README).
- **Vérifié dans le banc d'essai (Chromium, faux `frappe`, PAS le Desk)** : rendu clair/sombre, bureau 900 px et mobile 390 px ; clic « Créer le devis » → appel `decide_action` correct, état « Fait », lien « Ouvrir le devis » → route du document ; échec de droits → message en rouge et bouton encore actif ; flèches des cartes de statistiques → bonne route ; 122 textes, **0 sous 4,5:1** en clair et en sombre. Captures : `docs/review/captures/phase10-cartes/`.
- Maquette : `docs/frontend/mockups/proposition-assistant.html`.

### Audit de la page Assistant IA (banc d'essai, lecture seule + 2 correctifs sûrs)
- **Corrigé (sans changer l'apparence)** : zone cliquable de 24 px (WCAG 2.2, 2.5.8) pour les trois icônes « Ouvrir… » des cartes (les icônes n'ont pas bougé d'un pixel; seul le fond au survol est plus grand) et pour « Masquer » du bandeau de démonstration (texte ~2 px plus bas). Audit mécanique après : 0 bouton sans nom, 0 cible < 24 px, 0 débordement horizontal à 1280 et 390 px, 0 image sans `alt`.
- **Non touché, à décider par Kael** : (1) les trois illustrations des questionnaires guidés utilisent des **dégradés violet, bleu, vert** alors que la direction visuelle de ce document demande « aucun violet néon, halo ou dégradé copilote » ; (2) le texte de la zone de saisie (« Que puis-je faire pour vous aujourd'hui ? ») répète le titre (« Comment puis-je vous aider aujourd'hui ? ») ; (3) le mode démonstration est signalé deux fois (bandeau + pastille), voulu ou redondant ?
- Limite : audit fait avec un faux `frappe` et sans les feuilles de style du Desk ; non vu dans l'application réelle.

### Décisions de cette étape
- Les montants des cartes d'action utilisent le même format que les statistiques (« 1 234,50 $ ») : un seul format partout.
- Le graphique est un SVG maison (pas de bibliothèque) : aucune dépendance de plus, rendu identique clair/sombre, `role="img"` + `<title>` par barre. Limite : pas d'infobulle riche ni de zoom.
- En sombre, le vert des barres devient menthe (`#6ee7b7`) par la conversion automatique : lisible, mais à valider par Kael sur un Desk réel.

### Reste à faire (ordre proposé)
1. ~~Vérifier les deux cartes dans le banc d'essai~~ **fait**. Reste : les voir dans un **vrai Desk** avec `cortex_ai_actions` activé (`bench --site <site> set-config cortex_ai_actions 1`), `bench build --app cortex_rental`, `bench migrate` (nouveau DocType).
2. Plus d'actions métier, **une par une, seulement celles qu'on peut annuler facilement ou qui passent déjà par l'approbation** (réservation, retenue, paiement, approbation…). Candidates à valider avec Kael.
3. Modifier la structure par l'IA (champs, sections, espaces, catégories de pages) avec avant/après et annulation ; modèles de secteur.
4. Chat : réponse en continu, pièces jointes, mémoire/projets, étapes visibles.
5. Migration de gros volumes (modèles de fichier, validation avant import, reprise ; `max_file_size` 10 Mo trop petit).
6. PostHog : la clé `phc_…` est à fournir par Kael ; avis de confidentialité ; réglage individuel.
7. Audit de l'interface de la page Assistant IA : liste des défauts sûrs corrigés / à décider.

### Comment ajouter une action ou une carte (pour la personne suivante)
- **Action** : écrire `_prepare_x(args, company) -> Prepared` (validation, droits, aperçu structuré `rows`/`totals`) et `_run_x(payload, company)` (appelle la fonction partagée de l'écran), `register(ActionSpec(...))` dans `actions.py`, ajouter l'outil `propose_x` dans `tools.py` (via `_propose`), à `PROPOSING_TOOLS`, à `tool_policy.AGENT_TOOL_MAP` et à `gateway.TOOL_LABELS`. Si la fonction de l'écran est enfermée dans un décorateur, **extraire un cœur** (voir `rentals.insert_quote`, `customers.insert_customer`) plutôt que dupliquer.
- **Carte de statistiques** : un outil de lecture qui renvoie `stat_block` = `stats.card(...)` avec des chiffres lus par `frappe.get_list` (droits + société) et un `source_href` réel.
- **Jamais** : écrire directement depuis un outil, inventer un chiffre, mettre un lien externe, ou présenter une exécution échouée comme réussie.

### Limites connues
Rien de cette phase n'a été essayé sur un Desk Frappe actif ni avec un vrai modèle. Les composants ont été vus seulement dans le banc d'essai (`tools/ui-harness/`). Les outils `propose_*` restent invisibles pour le modèle tant que `cortex_ai_actions` n'est pas activé.

## Phases 11 à 13 : suite demandée par Kael le 2026-10-10 (PLAN, rien de codé)

> Plan écrit **avant** le travail (règle de Kael). Chaque phase mettra cette section à jour : fait / reste / pourquoi. Ordre choisi par moi, à contester.

### Demandes de Kael (résumé fidèle)
1. **Voir la réflexion derrière les actions de l'IA** (pourquoi une proposition de devis, etc.). Cartes de statistiques : très satisfait; **peut aussi utiliser d'autres graphiques** (pas seulement des barres).
2. L'IA doit pouvoir **tout faire et tout référencer, de A à Z**, dans toute l'application, et le système doit être **versatile pour tous les domaines** de location.
3. **Parcours d'entrée soigné et animé** : page de connexion → écran de chargement → **onboarding complet** (plusieurs pages dédiées si utile, le plus rapide et facile possible, l'IA aide à configurer dès le début) → **Assistant IA** comme première page.
4. **Assistant IA plein écran** : pas de fil d'Ariane, pas de barre du haut sauf « Mon compte » et réglages ; barre latérale réduite à son icône (aspect plein écran) ; **polices moins grasses** (sinon « enfantin »).
5. **Info-bulles** et **visite guidée interactive** de l'application (quelle page fait quoi, comment ça marche), **passable**, qui aide à configurer le compte avec l'IA.
6. Actions suivantes **dans l'ordre que je veux** : libérer/renouveler la retenue, demander une réservation, etc. (celles qui s'annulent ou passent par une approbation).
7. Accueil IA : les 3 cartes à dégradés → **accent vert** (ou garder; choix laissé à moi : accent vert, réversible) ; le texte de la zone de saisie ne doit plus **répéter le titre**.
8. PostHog : la clé viendra plus tard. **Poser des questions, ne rien supposer.** **Prendre des captures, ouvrir un bench et tester moi-même**, visuellement et par le code, tout ce que je livre.

### Plan et logique
| Phase | Contenu | Pourquoi dans cet ordre |
| --- | --- | --- |
| **12 (d'abord)** | **Vrai bench ERPNext** via Docker (images Docker Hub par le miroir `mirror.gcr.io`, car `github.com` est refusé par le proxy du bac à sable et Docker Hub direct renvoie 429) : installer `erpnext` + `cortex_rental`, `bench migrate`, tests Frappe (`test_multitenant_isolation`, etc.), captures du **vrai Desk** | Tout ce qui est livré depuis v0.8.0 n'a **jamais** tourné sur un Desk. Le bench est le seul vrai test; il décide de la suite |
| **10b** | Réflexion visible dans la carte d'action; autres types de graphiques (anneau, barres horizontales); actions : libérer/renouveler la retenue, demander une réservation, enregistrer un paiement, décider une approbation; outils de **lecture générique** (chercher/lire n'importe quel enregistrement permis) avec carte de référence + lien; correctifs de l'accueil (dégradés, texte de saisie) | Prolonge ce que Kael a validé |
| **11** | **Maquettes d'abord** (écran de chargement, pages d'onboarding, visite guidée) → intégration : connexion animée, chargement, onboarding multi-pages assisté par l'IA, Assistant IA plein écran, polices allégées, info-bulles, visite guidée | Nouvelles surfaces = proposition validée avant de coder (règle de Kael) |
| **13** | Modification de structure par l'IA (champs, sections, catégories de pages) avec avant/après et annulation, modèles de secteur ; migration de gros volumes ; chat (flux continu, pièces jointes, mémoire) | Dépend du bench et d'un exemple de fichier du client |

### Garde-fous (rappel)
Approbation humaine avant toute écriture; droits de la personne; audit; revalidation; **annulable ou refusé**; rien d'irréversible sans question; chaque « vu à l'écran » dit s'il vient du banc d'essai hors Desk ou du vrai bench.

## Phase 12 : vrai bench ERPNext (2026-10-10) — premier résultat

**Montage (reproductible)** : Docker par le miroir `mirror.gcr.io` (`github.com` est refusé par le proxy du bac à sable; Docker Hub direct répond 429). `dockerd` démarré à la main (`--iptables=false --bridge=none`, réseau `host`) ; MariaDB 10.6 + Redis 7 + `frappe/erpnext:v15` (ERPNext 15.122) ; l'app est copiée dans `apps/cortex_rental` et installée en éditable avec `PIP_CERT=/root/.ccr/ca-bundle.crt` (le proxy ré-émet le TLS : ne jamais désactiver la vérification). Site `cortex.localhost`, **assistant de configuration ERPNext exécuté** (langue Français, Canada, CAD) : sans lui, il manque types d'entrepôt, groupes d'articles, etc. `bench install-app cortex_rental` puis `bench migrate` : **sans erreur, 40 DocTypes Cortex créés**.

**Résultat de la suite complète dans le bench : 649 tests, 0 échec** (22 ignorés : tests écrits pour le mode « sans Frappe », et tests qui lisent le `Makefile` ou `bin/` du dépôt). Au premier passage : 29 erreurs et 2 échecs, **tous venant des tests** (fixtures manquantes, hypothèses fausses), pas du produit :
- **Isolation entre sociétés : prouvée** (6 tests : une personne de la société A ne voit ni ne lit le journal d'audit de B; un compte d'agent ne lit pas le journal du tout). Le test utilisait `frappe.get_all` (qui ignore les permissions) : corrigé en `get_list`.
- **Concurrence** (4), **télémétrie des agents** (2), **retours de matériel complet/partiel** (2) : passent. Le verrou Redis par article fonctionne; le test était fragile (le verrou vit 5 s).
- Fixtures communes : `tests/live_fixtures.py` (société avec pays, article avec groupe, client, utilisateurs humains). `NO_FRAPPE` marque les tests du mode simulé.

**Constats sur le produit (à décider, non modifiés)**
1. **L'utilisateur `Administrator` est traité comme un agent** : il reçoit tous les rôles, dont « Agent Service Account », donc il ne peut pas confirmer une réservation ni décider une approbation (`_current_actor_is_agent`, `audit.py`, `approval_request.py`). Un humain doit avoir le rôle Rental Manager. Je n'ai pas « corrigé » : si le serveur MCP des agents se connectait avec le compte Administrator, la correction donnerait des pouvoirs humains aux agents. **Question pour Kael.**
2. **Un devis retient le matériel** (72 h par défaut) : un test ou un client qui crée plusieurs devis pour les mêmes dates peut se voir refuser une réservation (c'est voulu; attention aux jeux de données de démonstration).
3. Les noms racines d'ERPNext (« Tous les départements ») suivent la langue de l'assistant de configuration. Création de société testée en `fr` et en `en` sur ce site : OK; à retester quand le provisionnement client sera exercé.

**Commandes pour rejouer** : voir `tools/bench/README.md`.

## Phase 10b et 12 (suite) : vérifié dans le VRAI Desk (2026-10-10)

**Fait et vu dans un vrai Desk Frappe (Chromium → `bench serve`, ERPNext 15, site français)** : connexion, arrivée sur l'Assistant IA, historique, conversation avec **vraies cartes** (données créées par le moteur d'actions lui-même : 4 devis, 2 réservations, 2 factures, 1 paiement), **approbation réelle** (« Créer le devis » → devis `CR-TRX-2026-00036` créé, lien « Ouvrir le devis » qui l'ouvre), flèches des cartes de statistiques (→ Finance), anneau et barres avec les chiffres réels, mode sombre. **Aucune erreur JavaScript** (hors `socket.io`, absent de mon bench). `bench build` compile les trois bundles Vue avec le vrai bundler de Frappe. Captures : `docs/review/captures/phase12-vrai-bench/`.

**Suite complète dans le vrai bench : 668 tests, 0 échec** (22 ignorés : mode « sans Frappe » et tests qui lisent des fichiers du dépôt). Nouveaux tests d'intégration : `test_ai_actions_live.py` (16 : proposer sans écrire, approuver par la voie de l'écran, refus par les droits de Frappe, aperçu périmé = rien d'écrit, double approbation, isolation entre sociétés, retenue libérée puis renouvelée puis réservation, paiement sur une vraie facture d'acompte, décision d'approbation par un autre humain).

**Bogue de production trouvé et corrigé** : `insert_customer` écrivait `territory = "All Territories"` et `customer_group = "Commercial"` en dur ; sur un site configuré en français ces noms n'existent pas (« Tous les territoires ») et **la création d'un client échouait** (aussi dans le compositeur de devis). Maintenant : un groupe et un territoire pris parmi ceux qui existent (`default_group_and_territory`).

**Ajouté dans cette étape** : réflexion visible (« Pourquoi cette proposition » : explication déclarée par l'assistant, étiquetée non vérifiée; données consultées; ce que l'action fera et comment revenir en arrière), cartes d'action pour retenue (libérer, renouveler), réservation, paiement, décision d'approbation (ADR-011), anneau et barres horizontales, accueil IA : zone de saisie qui ne répète plus le titre et **trois cartes en accent vert** (choix de Kael).

**Corrigé grâce au vrai Desk** : la balise `<footer>` des cartes était décalée par la feuille du Desk (remplacée par un `div`); « 2.5 jour(s) » écrit au format français.

**Constats ouverts**
1. Quelques icônes de la barre latérale paraissent ternes en mode sombre sur la capture (contraste des traits mesuré à 12:1 : c'est le dessin de certaines icônes du Desk, à examiner).
2. Le texte « Bonsoir, kael. » vient du nom complet de l'utilisateur de test (non recalculé) : à revérifier avec un vrai compte.
3. `Administrator` est traité comme un agent (voir Phase 12) : question toujours ouverte pour Kael.
4. Les actions *paiement* et *décision d'approbation* ne s'annulent pas par un bouton (paiement : remboursement; approbation : nouvelle demande); l'aperçu le dit (« Ce qui va se passer »). Validées par Kael dans la liste, mais à garder en tête.

## Phase 10c : l'IA fonctionne de bout en bout dans le vrai Desk (2026-10-10) — priorité demandée par Kael

**Demande de Kael : rendre le système d'IA fonctionnel de bout en bout avant de toucher au reste (le parcours d'entrée est en attente).**

**Ce qui est prouvé (vrai Desk, vrai serveur, vraie base, vrais droits)** — `tools/ui-harness/e2e-ai.mjs`, **27 vérifications sur 27** :
- *Devis* : demande tapée → modèle → `search_customers` → `search_rental_items` → `check_inventory_availability` → `propose_create_quote` → carte avec « Pourquoi cette proposition » → **approbation** → devis créé en base avec les deux articles → lien qui l'ouvre.
- *Rechargement* : la carte approuvée reste « Fait ». *Statistiques* : trois cartes (résumé, barres, anneau), la flèche ouvre Finance.
- *Paiement* : la carte nomme la vraie facture; approuver la fait passer à « Payée » en base, paiement par chèque enregistré. *Retenue* : libérée en base.
- *Pannes* (toutes en français, sans carte trompeuse) : clé refusée, service indisponible (503), limite 429 du fournisseur (relance silencieuse, réponse obtenue), modèle introuvable (le modèle de repli répond), **plafond de dépense** (entre 100 et 150 % : modèle économique + avis; au-delà : refus clair), **sans clé : mode démonstration étiqueté**.

**Ce qui n'est PAS prouvé** : le comportement d'un **vrai modèle Gemini** (décisions, qualité des raisons, appels d'outils réels) ni la facturation réelle. Le « modèle » des essais est un faux serveur (`tools/bench/fake_gemini.py`) qui **valide la requête comme l'API réelle** et suit des scénarios codés utilisant les vrais résultats des outils. **À faire dès que Kael fournit la clé** : la saisir dans *Cortex AI Settings*, retirer `cortex_ai_gemini_base_url`, rejouer la même suite (`e2e-ai.mjs`) puis juger la qualité des réponses.

**Défauts réels trouvés par ces essais et corrigés** :
1. Les outils **sans argument** (résumé financier, locations par état) étaient déclarés avec `properties: {}` : la documentation officielle les déclare **sans** `parameters`, l'API risquait de refuser toute la requête. Désormais : types en majuscules, aucun `parameters` ni `required` vide (`GeminiProvider.schema`). Un test de contrat valide chaque outil contre le validateur du protocole.
2. L'agent principal **n'avait pas l'outil de recherche de clients** : impossible de préparer un devis. Ajouté; un test exige que chaque proposition ait les outils de lecture dont elle a besoin.
3. Une **clé refusée (401/403)** retombait en mode démonstration comme une clé absente (trompeur) : maintenant message clair « clé refusée ».
4. **Site neuf sans maîtrise des jetons** : prix = 0 et plafond = 0 (les patchs ne sont pas rejoués à l'installation). `after_install` applique maintenant les valeurs de départ (0,75 $ / 3,75 $ par M de jetons, 60 $ par mois, modèle économique), sans jamais écraser une valeur saisie. **Important pour « un site par client ».**
5. Message de limite de débit du chat **en anglais** : en français. Disponibilité « 5.0 libre(s) » : format français. Le modèle dit « ci-dessous » (les cartes s'affichent sous son message). Nouvel outil de lecture `list_invoices` (sans lui, impossible de proposer un paiement).

**Rejouer** : `tools/bench/README.md` (faux Gemini, clé d'essai `fake-gemini-key`, `cortex_ai_gemini_base_url` — **jamais en production**, seules les adresses https ou locales sont acceptées).

**Reste à faire (IA)** : action générique « modifier un champ » avec avant/après et annulation (validée par Kael), outil de lecture générique pour tout référencer, modification de structure (champs, sections, catégories) avec approbation du propriétaire, flux continu, pièces jointes, mémoire; qualité avec un vrai modèle.

## Phase 11 (en cours) : parcours d'entrée — décisions de Kael (2026-10-10), construit directement (« oublie la maquette »)

**Règle générale (Kael) : l'IA aide, elle ne fait pas à la place de la personne, et l'application reste légère en jetons. « Déterministe d'abord » :** tout ce qui peut se faire sans modèle (modèles de secteur, listes, validations, textes d'aide, visite guidée) est codé en dur; le modèle n'est appelé que sur demande explicite, **jamais au chargement d'une page**. **Aucune IA dans l'onboarding ni dans la visite guidée.**

| # | Chantier | Décision de Kael | État |
| --- | --- | --- | --- |
| 11.0 | Barre latérale | **Administration replié par défaut** (il s'ouvrait à cause de `cortex-setup` et ne se refermait pas) | **Fait, vérifié dans le vrai Desk** (`data-auto` dans `cortex_nav.js`) |
| 11.1 | Écran de chargement après la connexion | **Accueil personnalisé court** : « Bienvenue, {prénom} », nom et logo de la société, fondu doux, pas de liste d'étapes, une seule fois par connexion | À faire |
| 11.2 | Assistant IA plein écran | **Ta page, presque intacte** : retirer le fil d'Ariane et la barre du haut (sauf Mon compte et Paramètres), barre latérale réduite aux icônes (avec son bouton), **polices plus légères** | À faire |
| 11.3 | Onboarding | **Garder l'actuel tel quel**; ajouter **animations seulement** (transition entre étapes, coche, barre de progression, « Enregistré »). Pas d'IA | À faire |
| 11.4 | Visite guidée | **Une visite globale pas à pas** (halo + bulles), **contenu** : où est chaque page et à quoi elle sert + comment l'application fonctionne (demande → devis → réservation → contrat → sortie → retour → facture → paiement); **elle ouvre chaque page**; **automatique une fois** à la première arrivée sur l'Assistant IA après l'onboarding, **relançable** depuis Aide; passable à tout moment. Pas d'IA | À faire |

Pourquoi : l'IA qui remplit tout coûte des jetons et retire le contrôle; un onboarding guidé par des textes, des exemples et des animations est prévisible, rapide et gratuit à exécuter. L'IA commence sur l'Assistant IA, sur demande.

## Niveau de vérité de l’implémentation

État vérifié le 2026-09-30 sur le bench de développement (Frappe/ERPNext 15.121) :

- **Changements de la phase 2 (2026-10-07) — codés, testés hors bench, non recettés dans un navigateur :** voir la section « Phase 2 : ce qui est réellement livré ». Une version antérieure de ce document décrivait comme codés des éléments absents du code (arrivée sur Assistant IA, repli de la barre, en-tête `X-Company-ID`, explications du dictaphone); ils ne l'étaient pas et sont maintenant réellement implémentés.

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
