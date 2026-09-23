# Cortex UI handoff v2 — ERPNext-first, AI-native

**Statut :** contrat produit canonique pour l’interface Cortex et les agents de développement.  
**Version :** 2.1 · 2026-09-23  
**Socle :** ERPNext + Frappe Framework, Vue 3 et Frappe UI.  
**Principe :** *Cortex suggère, l’humain décide.*

> Les instructions de ce fichier priment sur les descriptions frontend antérieures de `HANDOFF.md`. Elles ne remplacent pas les règles de sécurité métier déjà codées. Quand la documentation et le code divergent, ne prétends jamais qu’une fonction est opérationnelle : vérifie l’endpoint et décris l’écart.

## Mandat pour tout agent

Traite ce document comme le contrat produit commun avant de modifier un écran, un flux IA ou le shell. Conserve ERPNext/Frappe comme système de référence et les API métier Frappe comme seule voie d’écriture. Utilise Frappe UI en priorité pour les primitives Vue, puis les composants Cortex déjà présents. Évite de créer un système parallèle, des données métier fictives, une action simulée présentée comme réelle, ou des appels LLM depuis le navigateur.

Avant tout changement : inspecte l’écran concerné, ses contrats TypeScript, l’adaptateur API, les permissions et le service métier. Toute action doit traverser les autorisations Frappe et le service de domaine compétent. Toute suggestion visible doit distinguer fait vérifié, inférence, brouillon, erreur et indisponibilité du service.

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

## Direction visuelle : référence ERPNext

Recrée le langage de la capture Profit and Loss fournie : interface de travail dense, claire, neutre, immédiatement lisible, conçue pour les opérations d’entreprise.

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

Le shell est partagé par les pages Cortex : sidebar repliable, topbar, recherche universelle, sélection d’entreprise, notifications et profil. L’état replié est l’état initial privilégié pour retrouver le rail ERPNext de la référence; la préférence de l’utilisateur est persistée. Ne duplique pas le shell dans les vues.

Navigation IA canonique :

| Destination | Route frontend | Rôle |
|---|---|---|
| AI Inbox | `/app/cortex-ai-inbox` | Travail à traiter : suggestions, approbations, documents entrants |
| AI Workspace | `/app/cortex-ai-workspace/:itemId?` | Source, brouillon, preuves, conversation et prochaine action |
| AI Audit | `/app/cortex-ai-audit` | Décisions, acteurs, latence et événements traçables |

Les anciennes routes approvals/incoming/drafts redirigent vers l’Inbox avec leur filtre. Ne maintiens pas des files concurrentes.

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

## Composants Vue et Frappe UI

Frappe UI est le premier choix pour les contrôles accessibles, menus, dialogues, badges, champs et commandes. Réutilise le design system `src/design-system/components/ai` et complète-le sans rompre ses contrats :

- `AiStatusBadge` pour l’état, le niveau disponible et l’indication de données synthétiques.
- `AiCard` pour suggestion, risque, politique, approbation et résultat d’audit.
- `AiProvenanceCard` pour origine API, temps réel, mock/démo, fraîcheur et référence de preuve.
- À factoriser lorsque le contrat le justifie : `CortexAISuggestionCard`, `CortexAIConfidence`, `CortexAIEvidenceList`, `CortexAIValidationFooter`, `CortexAIContextPanel`, `CortexAIDiffView`, `CortexAIActionTray`, `CortexAIInboxList` et `CortexAIAuditTable`.

Un composant partagé reçoit un statut et des données explicites, ne fait pas d’appel API caché, n’infère pas la confiance, n’exécute pas une action sur simple rendu et expose les interactions via événements typés.

## Intégration IA et sécurité technique

Flux attendu : Vue → API Frappe authentifiée → service Cortex → (a) Onyx pour orchestration et langage, (b) MCP privé pour outils autorisés → API métier Frappe/ERPNext. Onyx et Ollama ne parlent jamais directement à MariaDB. ERPNext garde les calculs et états canoniques.

- L’URL Onyx, le jeton serveur et la configuration Ollama sont stockés côté serveur (config Frappe ou gestionnaire de secrets), jamais dans une variable `VITE_*`, le bundle, le stockage du navigateur ou la télémétrie publique.
- Le serveur résout compagnie, utilisateur, agent, permissions, contexte, outils et modèle. Le client ne peut imposer aucun de ces choix.
- Liste d’outils explicite, vide si aucun outil n’est accordé. MCP applique de nouveau les scopes, l’entreprise et les règles d’approbation.
- Les outils métier reçoivent les identifiants nécessaires, pas un prompt libre faisant office de politique.
- Le contenu d’un document entrant est une donnée non fiable, pas une instruction système. Appliquer protections contre prompt injection, validation de schéma, limites de taille, contrôle de pièces jointes et citations.
- Les messages envoyés au client, décisions, erreurs et latence doivent être traçables avec identifiant de corrélation. Évite l’enregistrement de prompts/réponses bruts avec données personnelles; masque-les ou conserve-les selon une politique explicite de rétention.
- Tolérance aux délais, annulation, limites de débit, retries bornés/idempotents et erreurs fournisseur explicites. Ne retente jamais aveuglément une mutation externe.
- Onyx Lite local est adapté au chat/agents mais ne fournit pas l’indexation RAG complète. Déploiement standard si la recherche sur corpus et les connecteurs sont requis, avec ressources suffisantes.
- Ollama est un fournisseur de modèles, pas un ERP ni un moteur de règles. En développement local, `qwen3:8b` (Q4_K_M) est installé, configuré comme fournisseur Onyx et a répondu à une génération Ollama. Le compte administrateur Onyx existe et son authentification a été vérifiée. Le nom du modèle, l’URL et le jeton de chat sont configurés côté serveur Frappe; ne les copier ni dans ce document ni dans le frontend. Cette validation locale ne signifie pas que le chat Cortex→Onyx et les outils métier ont passé une recette de bout en bout. `qwen3.5:9b` a été écarté après un appel d’outil CPU de 2 min 45 s.

## Niveau de vérité de l’implémentation

Les pages et actions doivent indiquer leur provenance réelle. Mock, fixture, API backend et service IA sont des modes différents. Le mode Mock ne devient pas « production » parce qu’il passe le build.

État vérifié le 2026-09-23 :

- La stack de développement fonctionne dans Docker : Vite sur `localhost:5173`, Frappe/ERPNext sur `localhost:8000`, Onyx Lite sur `localhost:3000`, et Ollama sur l’hôte Windows. Le frontend est en mode API réelle par défaut; les mocks ne sont activés que par configuration explicite.
- L’authentification Cortex utilise la session Frappe/ERPNext, distincte du compte Onyx. L’initialisation de session est mutualisée entre les gardes et limitée à 8 secondes afin qu’une API indisponible ne bloque pas le rendu de la page de connexion. Un utilisateur Guest reçoit normalement `403` sur l’endpoint de contexte et est redirigé vers `/login`.
- Vite pré-bundle `feather-icons` et `debug`, deux dépendances CommonJS importées par Frappe UI / Socket.IO, pour éviter les erreurs d’exports ESM dans le navigateur.
- Le compositeur utilise les clients, l’équipement, la disponibilité, l’aperçu de prix et la création de transactions côté Frappe; les totaux fiscaux du devis ERPNext restent la référence. Les numéros de série de réservation sont attribués sous verrou côté serveur. Les scans de sortie, retours partiels/complets, dommages et preuves privées utilisent les services Frappe disponibles; les preuves sont liées à la clôture et hachées côté serveur.
- Les routes AI Inbox/Workspace/Audit existent. Le compte Onyx, `qwen3:8b`, le fournisseur Ollama et la configuration serveur Frappe sont en place localement. La connexion Onyx et l’API du modèle ont été vérifiées séparément; le parcours complet de conversation et d’outil depuis l’interface Cortex reste à recetter. Onyx Lite n’offre pas l’indexation RAG ni les connecteurs du déploiement complet.
- Ne qualifie pas l’ensemble du produit de prêt pour la production : les parcours contrat, facturation et envoi client, les droits réels par rôle, l’expérience d’équipe/assignation, les opérations documentaires complètes et les intégrations comptables doivent encore être vérifiés contre leurs contrats métier. Les fonctions absentes restent explicitement indisponibles plutôt que simulées.
- La comparaison visuelle pixel-perfect avec la capture P&L n’a pas été validée par une revue de captures fiable. Elle doit rester un élément de recette, même si le shell et les pages suivent les tokens et la structure de la référence.
- Validation locale : build TypeScript/Vite, compilation Python, tests ciblés de session/route et appels HTTP Docker réussis. Lors de la dernière suite frontend complète, 250/251 tests ont passé; le test séquentiel d’import de toutes les vues a dépassé le délai de 180 s sous charge, puis a réussi isolément. Ne présente pas cette suite complète comme entièrement verte.

## Definition of Done pour une évolution

1. Le parcours respecte les règles ERPNext et les permissions serveur.
2. Le comportement en succès, erreur, chargement, état vide, confiance faible, API indisponible et permission refusée est visible et honnête.
3. Aucune action métier n’est appliquée par le seul fait d’avoir rendu ou validé une suggestion.
4. Les sources, preuves et différences proposées sont consultables.
5. L’interface respecte ce langage ERPNext et fonctionne au clavier / sur écran étroit.
6. Le build frontend et les contrôles backend pertinents passent; les vérifications live sont identifiées comme telles, distinctes des mocks.
7. Documentation, endpoint et code racontent la même chose.
