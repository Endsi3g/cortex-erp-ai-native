# Changelog — Cortex

## Unreleased


## v0.15.1 — 2026-10-07

Phase 9.6 et 9.7. **Vu uniquement dans un banc d'essai hors Desk (faux `frappe`, ma propre feuille de style de page) ; testé hors bench ; non essayé sur un Desk Frappe.** Kael signale (2026-10-07) que la barre latérale et le mode sombre ne correspondent pas, dans l'application réelle, à ce qui était demandé : voir le Handoff, « Phase 9.6 et 9.7 ».

### Corrigé
- **Mode sombre** : lignes de tableaux blanches à texte clair (Mon compte › Société : droits, équipe) : **vu et corrigé**. Boutons, compteurs, puces et tiroir à fond blanc codé en dur : ajoutés à la couche sombre, **non vus à l'écran**.
- **Mon compte** : plafond d'IA au format canadien-français, activité récente d'un collègue lisible, noms de l'équipe sans bleu de lien par défaut.
- Barre latérale : pastille et carte de société en mode réduit sur mobile ; avatars à initiales lisibles en sombre.

### Ajouté / modifié
- **Pied « Propulsé par Cortex »** cliquable vers le site de Cortex quand `cortex_site_url` est réglé dans la configuration du site (https seulement) ; logo clair en mode sombre.
- **« Demande reçue »** épurée : une colonne, plus d'espace, **Copier le lien** en icône sur petit écran, actions avec icônes, FAQ à chevrons, pastille de lettre sans photo.
- **Factures imprimées** (A4/Lettre) : logo de la société.

### Pas encore vérifié
- Formulaires du Desk (paiement avec le client en tête, réglages de taxes) : à ouvrir sur un bench.
- L'adresse du site Web de Cortex n'est pas dans le dépôt : à régler (`set-config cortex_site_url`).

## v0.15.0 — 2026-10-07

Phase 9 (demandes de Kael du 2026-10-07), première partie. **Vu à l'écran dans Chromium pour le portail, le suivi et le devis ; testé hors bench.**

### Ajouté
- **Abonnements : valeurs par défaut modifiables** (devise CAD, 1 000 $/mois, enveloppe d'IA de 60 $, options Portail/Équilibré/Avancé/Luna, sociétés existantes exemptées) : patch une fois + bouton. **Prix des options = valeurs de départ à confirmer**; rien n'est facturé.
- **Contrat : consentement explicite** (« J'ai lu et compris… ») avant d'accepter un devis, **conditions modifiables par société** avec modèle de départ et version, instantané par devis, preuves conservées (version, empreinte, date, empreinte IP/navigateur). Pas d'avis juridique requis (décision de Kael); ce n'est pas une signature certifiée.
- **Portail** : logo, bannière, phrase d'accueil et couleur d'accent de la société; photos d'équipement; **pied de page « Propulsé par Cortex »** (portail, suivi, devis). Seuls les fichiers publics sont exposés.
- **« Demande reçue »** dense et interactive : récapitulatif, étapes, copie du lien, courriel prérempli, ajout au calendrier (.ics), impression, nouvelle demande, FAQ. Page de suivi enrichie.

### Corrigé
- L'ADR-009 avait été créé dans `apps/docs/adr/` au lieu de `docs/adr/` (liens du Handoff cassés) : déplacé.

## v0.14.0 — 2026-10-07

Phase 8 du plan de livraison. **Premier passage : vérifié dans Chromium sur l'accueil IA et la grille de disponibilité; non vérifié sur un Desk Frappe.**

### Ajouté
- **Mode sombre** : choix Clair / Sombre / Automatique dans *Mon compte › Profil › Apparence* (enregistré par personne; **clair par défaut**).
- **Couche sombre générée** (`bin/generate-dark-theme.mjs`) : appliquée seulement sous `html[data-theme="dark"]`, le mode clair n'est pas modifié. Contraste audité : 0 texte sous 4,5:1 sur les deux écrans vérifiés; palette testée (WCAG).
- Captures de validation dans `docs/review/captures/mode-sombre/`.

### Pas encore vérifié
- Barre latérale, Mon compte, configuration, copilote et Desk de Frappe en sombre : à parcourir sur un Desk actif.

## v0.13.0 — 2026-10-07

Phase 7 du plan de livraison. **Codé et testé par événements Stripe simulés ; désactivé par défaut ; jamais essayé avec un compte Stripe.**

### Ajouté
- **Abonnements Cortex** (ADR-010) : plan de base, modules et niveaux d'IA payants par société; Stripe Checkout et portail; webhook signé, idempotent et ordonné; droits appliqués côté serveur (niveaux d'IA, portail client).
- Carte « Abonnement Cortex » dans *Société et rôles* (propriétaire).
- Réglages de plateforme *Cortex Subscription Settings* : l'activation exige clés, identifiants de prix et **confirmation humaine des prix**; sociétés exemptées possibles.

### À savoir
- Rien n'est facturé ni restreint tant que la facturation n'est pas activée. Prix, devise, enveloppe d'IA incluse et options sont à décider par une personne.

## v0.12.0 — 2026-10-07

Phase 6 du plan de livraison. **Codé et testé hors bench ; non essayé dans un navigateur.**

### Ajouté
- **Portail de demandes** (`/demande/<identifiant>`, sans compte) : demande de location, calendrier public du matériel (libre / limité / complet, sans quantité ni client), suivi par lien personnel (`/suivi/<jeton>`). Une demande ne réserve rien. Activé par société, protégé (limite par IP, champ piège, consentement, plafond quotidien).
- **Paiement par chèque** : annonce par le client sur la page du devis, facture d'acompte créée, équipe prévenue, rapprochement quand l'entreprise enregistre le chèque. Rien n'est marqué payé par le client.
- Listes « Chèques annoncés » et « Demandes du portail » dans Finance.
- **ADR-009** : portail, chèque et parcours de signature (défini, non livré; validation juridique requise).

### Corrigé
- Le gabarit de suivi aurait affiché la méthode `dict.items` au lieu du matériel (bogue trouvé par le test de rendu).

## v0.11.0 — 2026-10-07

Phase 5 du plan de livraison (partielle). **Codé et testé hors bench ; non essayé sur un Desk Frappe.**

### Ajouté
- **Finance** : listes « Factures à encaisser » et « Factures récentes » (tous les raccourcis conservés).
- **Paiements** : indicateurs paiement/remboursement; le client (solde dû, locations, retards) en tête du paiement.
- **Formats d'impression de la facture** : A4 (par défaut) et Lettre, intégrés.
- **Modèles de taxes** Québec, TPS seule, aucune taxe (`billing.apply_tax_preset`, audité, taux bornés par le serveur). Les provinces à TVH ne sont pas couvertes.
- « New Email » traduit en « Nouveau courriel ».

### Pas encore fait
- Relevé de compte client imprimable, densification des paramètres, visualisation du catalogue, casse du statut « Actif ».

## v0.10.0 — 2026-10-07

Phase 4 du plan de livraison. **Codé et testé hors bench ; aucun fournisseur essayé avec une vraie clé.**

### Corrigé
- **Prix des niveaux IA** : Sonnet 5.5 = 2 $ / 10 $ et Opus 5.5 = 4 $ / 20 $ par million de jetons (page tarifaire d'Anthropic, 2026-10-07). Les anciens défauts surestimaient le coût dans le budget IA. Patch `correct_ai_tier_prices` (ne touche pas aux valeurs saisies à la main).

### Ajouté
- **Cortex Luna** (OpenAI `gpt-6-luna`) : fournisseur `OpenAIProvider`, clé OpenAI chiffrée côté serveur, désactivé par défaut.
- **Gemini 4 « à venir »** dans le sélecteur (aucune API publique), jamais sélectionnable.
- **Règles de la société** (taxes, acompte, retenue, approbation) dans le prompt système de l'assistant.
- Tests : prix vérifiés, niveaux, fournisseur OpenAI (format), règles de la société.

### À savoir
- Gemini 3.8 Flash passe à 1,50 $ / 7,50 $ le 1er janvier 2027 : mettre les prix à jour dans les réglages.

## v0.9.0 — 2026-10-07

Phase 3 du plan de livraison (partielle). **Codé et testé hors bench ; non essayé sur un Desk Frappe.**

### Ajouté
- **Profil d'une personne de la société** (`account.colleague_profile`) : photo, rôle, courriel, téléphone, présence, connexions et actions sur 30 jours, dernières actions, boutons courriel et appel. Ouvert à toute la société, refusé hors société. Le temps d'utilisation n'est pas affiché (non mesuré).
- Carte « Configuration de l'entreprise » dans *Société et rôles*; l'entrée « Configuration » de la barre latérale n'apparaît que tant que la configuration initiale est incomplète.
- Tests de contrat : gestion des comptes réservée au propriétaire, profils limités à la société.

### Pas encore fait
- Alignement présence/activité, lisibilité des notifications, icône bleue, barre latérale du site Web, refonte des pages Notifications/Sécurité/Activité/Statistiques/Profil, messagerie entre collègues (piste ultérieure).

## v0.8.0 — 2026-10-07

Phases 1 et 2 du plan de livraison de Kael (`docs/frontend/CORTEX_UI_HANDOFF_V2.md`). **Codé et testé hors bench ; non essayé sur un Desk Frappe ni dans un navigateur.**

### Corrigé
- **Saisie vocale impossible** : l'en-tête `Permissions-Policy` interdisait le micro à toute la page (`microphone=()`); il l'autorise maintenant à Cortex seulement (`microphone=(self)`).
- **« Cette location n'est pas disponible pour la société active »** à tort pour une personne autorisée sur plusieurs sociétés : l'action par location utilise désormais la société du dossier si la personne y est autorisée (`get_company_context_for_document`); une société hors de ses droits reste refusée.
- **Grille de disponibilité** : les unités en quarantaine, en réparation, manquantes ou retirées ne comptent plus comme libres (comme la vérification qui fait foi).

### Ajouté
- **Saisie vocale honnête** (`cortexVoice.js`) : indisponibilité dite avant le clic, erreurs expliquées en français (permission, microphone, réseau, service, aucune voix), texte provisoire, reprise en `fr-FR`, zone d'état accessible.
- **État réel du parc** dans Disponibilité (unités par état, matériel sorti) et **statistiques de la société** (Administration › Société et rôles, `account.company_stats`, chaque bloc selon les droits).
- **Chargement par page** : barre fine et contenu estompé, respect de « moins d'animations ».
- Arrivée sur l'Assistant IA (repli sur Cortex Rental sans droit d'accès), commande de repli de la barre latérale en bas du rail, barre repliée sur l'Assistant IA sans préférence enregistrée, libellé « Nom du projet ».
- Tests : résolution de société, en-têtes, saisie vocale (Node), état du parc, statistiques, contrat de la phase 2.

### Documentation
- Le handoff décrivait comme codés des éléments absents du code (arrivée sur l'Assistant IA, repli de la barre, `X-Company-ID`, explications du dictaphone); corrigé et réellement implémenté.

## v0.7.0 — 2026-10-07

Assistant IA refondu, interface pleine largeur, préparation à la production. Remplace les notes de v0.6.0 sur les actions « directes » de l'assistant : l'assistant ne crée plus rien de lui-même.

### Assistant IA
- **Trois questionnaires guidés** dans la conversation : *Nouvelle location* (client avec création, dates, équipement avec disponibilité du serveur, récapitulatif au prix du serveur, « Créer le devis » en brouillon), *Grille de disponibilité* (7 j, 30 j ou dates + catégorie, mini-grille, « Créer un devis avec ceci ») et *Demandes d'approbation* (examiner, approuver, refuser avec motif, retirer sa demande, selon les droits). Les propositions de l'assistant ouvrent le même questionnaire.
- **Mode démonstration honnête** (`services/ai/demo.py`) : sans clé de modèle, quatre demandes comprises (disponibilité, retards, approbations, catalogue) avec de vraies données, périodes écrites comprises (« du 20 au 22 octobre »), aucun prix ni confiance inventés. Pastille « Démonstration » / niveau Cortex lue côté serveur (`chat.status`).
- **Modèles Cortex** : *Rapide* (Gemini), *Équilibré* (Claude Sonnet 5.5), *Avancé* (Claude Opus 5.5) ; identifiants, prix et interrupteurs dans *Cortex AI Settings* ; clé Anthropic chiffrée ; fournisseur Anthropic (`AnthropicProvider`) ; choix du niveau validé par le serveur (clé de niveau, jamais un identifiant) ; budget au coût réel du niveau ; indice de coût calculé. **À vérifier** : prix par défaut d'Équilibré et d'Avancé ; fournisseur Anthropic non essayé avec une vraie clé.
- **Chat** : saisie collée au bas de l'écran sans ombre, fil défilant dans son cadre, réponses en texte normal (plus de cartes vertes), boutons d'action fantômes, attente « Cortex réfléchit… » en texte shimmer, texte révélé mot à mot (animation, pas un flux ; `prefers-reduced-motion` respecté), outils consultés affichés. Un type de bloc inconnu n'est plus jamais une erreur technique.
- **Historique** en tiroir (recherche, groupes, ouvrir, retirer ; les messages restent au journal, `state = Hidden`), réglages (bannière, effacer mon historique, lien « Budget et modèle IA »), fil d'Ariane « Assistant IA › Conversation », pièces jointes retirées tant qu'elles ne sont pas traitées, cartes accessibles au clavier.
- Nouvelles API : `chat.status`, `chat.delete_session`, `chat.clear_history`, `availability.get_period_summary`, `customers.create_customer`. Corrige : réponses vides (enveloppe `data`), salutation figée « Kael », `preview_pricing` en erreur 500 avec des articles en texte JSON, recherche de catalogue de l'assistant qui pouvait déborder sur une autre société.

### Mise en page
- **Pleine largeur** sur toutes les pages (la limite de 1290 px de Frappe est levée) ; l'assistant garde une colonne de lecture d'environ 900 px.
- **Barre latérale** : Société → séparateur → Nouvelle location (ouverte et repliée), Administration ancrée au bas ; un groupe qui s'ouvre reste visible en entier, les entrées ne se compressent plus, fondu en bas quand il reste des entrées.

### Données de démonstration et vérification
- `dev_tools/jeu_de_demo.py` (`run`, `reinitialiser`) : devis, réservations et trois demandes d'approbation de trois personnes ; retire l'article de test `SIM-STRESS-1` ; refuse hors site de développement.
- Tests ajoutés (assistant, niveaux, fournisseur Anthropic, présentation du chat) ; accessibilité vérifiée avec axe sur l'accueil, la conversation et les trois questionnaires, ordinateur et téléphone.

### Documentation
- README (racine et application) et index `docs/README.md` réécrits ; `HANDOFF.md` et `PROJECT.md` marqués historiques ; `SECURITY.md` mis à jour ; handoff V2 complété.

## Avant v0.7.0 : tout ce qui suit v0.5.0 (regroupé)

- **Préparation à la production** : stress test complet (fuzz de 112 endpoints, concurrence, isolation entre sociétés, charge sur gunicorn, 91 jours simulés), code défensif (`services/defense.py`, `safe_input`, frein de débit, vrais octets des images, 429 au verrouillage, en-têtes de sécurité), santé réelle (`health.ready`), contrôle pré-déploiement (`ops/predeploy.py`), guide de déploiement et fichiers `infra/production/`, sauvegarde et restauration vérifiées. Corrige : recherche de clients du compositeur de devis en erreur si le champ d'assurance n'existe pas; période de location inversée facturée 1 jour; 23 causes d'erreur 500 sur des entrées invalides.
- **Onboarding : transitions fluides** entre les étapes (fondu et glissement dans le sens de la navigation, hauteur de la carte animée, progression et étapes mises à jour en place, entrée et sortie en fondu, respect de « moins d'animations »). Correctif : l'assistant restait par-dessus l'écran après « Continuer plus tard » ou la fin (Frappe n'appelle pas `on_page_hide`). Enregistrement de l'entreprise ~20× plus rapide.
- **Onboarding complet** : assistant plein écran (`/app/cortex-setup`) à l'arrivée du propriétaire + carte « Terminer la configuration » sur l'accueil. Étapes **obligatoires** (entreprise avec logo, adresse, téléphone, courriel; propriétaire avec mobile) et **facultatives passables** (équipe, catalogue, prix et taxes, première location), retour arrière partout, récapitulatif. Règles appliquées par le serveur. Guide natif *Module Onboarding* retiré (patch `remove_native_onboarding`).
- **« Mon compte » fusionné dans « Administration »** (barre latérale). **Dossier relié** sur les locations, factures et paiements : liens vers client, factures, paiements, approbation, retenue, retours, écritures et historique (qui a fait quoi, qui a confirmé).
- **Auto-approbation du propriétaire seul désactivée par défaut**, avec fenêtre « Comprendre et décider » (bénéfices, dangers, case de confirmation, audit) accessible depuis la liste des approbations, la demande bloquée et *Société et rôles*. Libellé lisible à la place du code `transition_to_contract`. Statistiques allégées (résumé + lignes pliables). Un seul bouton **Exporter** (PDF ou CSV, PDF généré dans le navigateur). **Logo** de la société (étape du guide de démarrage + carte propriétaire).
- **Mon compte v3** : groupe « Mon compte » dans la barre latérale avec sept pages dédiées (une colonne, tout à gauche, tableaux aérés, tuiles de même taille, cartes pliables), rôles résumés en un profil clair, photo de profil ronde et téléversable, chiffres cliquables vers l'activité filtrée, activité de toute l'équipe (qui a fait quoi, qui a confirmé), « Ce qui m'attend » avec actions. Noms de rôles traduits simplifiés.
- **Mon compte v2** : 7 onglets denses (profil, statistiques, approbations, activité complète avec export, sécurité, notifications, société et rôles avec droits), appareils connectés identifiés (navigateur, système, modèle, adresse IP) avec **déconnexion à distance** d'un appareil ou de tous, appareils de l'équipe pour les administrateurs, historique des connexions, alertes personnelles.
- **Approbations** : plus de formulaire brut (bouton « Demander une approbation »), « Retirer ma demande », auto-approbation du propriétaire seul (réglage, journal d'audit), règle des deux personnes sinon. `dev_tools/verifier_approbations.py`.
- **Retenue du matériel par un devis** (ADR-008) : le devis retient le matériel dans la disponibilité (72 h par défaut, réglable, expiration sans tâche planifiée), grille hachurée et section « Sur la période », boutons Libérer / Reprendre. **Rappels horaires** (retenue qui expire, retour en retard, devis sans réponse, facture échue). **Frais de dommages et de pertes** optionnels à la facture finale (compte 4200). **Fiche client 360°**, rapport **Utilisation du parc**, outils de lecture de l'assistant (`customer_summary`, `late_returns`). Course de 12 devis simultanés vérifiée (une seule retenue).
- **Actions complètes d'une location** : Annuler, Ouvrir un litige et Clôturer le dossier (API `rentals.change_state`); correctif du retour par numéro de série (une ligne de plusieurs unités sérialisées restait à moitié retournée); création de demandes d'approbation permise aux gestionnaires; Approuver/Refuser et Enregistrer un paiement en boutons directs.
- **Mon compte** : profil, sécurité (mot de passe, appareils), notifications, société et rôles, usage de l'IA, activité.
- **Disponibilité** plus grande et épurée (remplissage proportionnel, en-têtes fixes). **Devis** : confirmation par case à cocher, bouton d'envoi retardé, refus serveur sans confirmation, PDF dans la barre d'actions, barres de répartition. Tableau de bord aéré, groupes Opérations et Assistant épinglés.
- **Plafond d'IA** : passage automatique au modèle économique (`gemini-3.1-flash-lite`) avec avis à la personne; refus seulement à 150 % du budget. Patch `set_ai_economy_defaults`.
- **Page de devis** refondue (épurée, dense, pensée pour les petits écrans). Barre latérale : groupes tous repliables; fil d'Ariane « Groupe › Page › Fiche » en français; titres de pages alignés sur la barre latérale (Locations, Approbations, Catalogue…); dates de liste en français. Guide Amazon SES.
- **Après l'acceptation d'un devis** : alerte en direct avec bouton « Réserver », réservation automatique optionnelle par société (au nom de la personne qui a partagé, disponibilité revérifiée), paiement de l'acompte dans le portail (Stripe Checkout avec les clés de la société, webhook signé, paiement unique par session) avec instructions manuelles en repli.
- **Coûts d'API** (`docs/architecture/COUTS_API.md`) : prix de `gemini-3.8-flash` (0,75 $ / 3,75 $ par M de jetons) et plafond de 60 $ par société et par mois proposés par défaut (patch `set_ai_pricing_defaults`); comparaison Stripe, Resend et SES.
- Profil de la personne connectée en bas de la barre latérale.
- **Portail de devis** (ADR-007) : `/devis/<jeton>` sans compte (lien à copier ou courriel), jeton haché, instantané du devis, accepter / refuser / demander une modification, audit (acteur « Customer »), notification et activité en temps réel, boutons sur la location. Accepter ne réserve rien.
- Barre latérale : carte de la société, Administration en bas; guide vidéo titré; formulaires mobiles plus courts; rapport *Utilisation IA* corrigé; débordement mobile de 3 px corrigé.
- **Passerelle IA** (`services/ai/`, ADR-006) : Gemini (défaut `gemini-3.8-flash`, à confirmer) dont le modèle se change dans *Cortex AI Settings*, modèle de repli optionnel, clé chiffrée côté serveur, boucle d'outils sous les droits de la personne connectée (lecture + propositions, rien n'écrit ni n'approuve), budget mensuel en dollars/jetons par société (*Cortex AI Usage*, *Cortex AI Budget*, rapport *Utilisation IA*; plafond à déterminer, 0 = aucun), historique de conversation transmis au modèle, messages d'erreur clairs. Moteur par `cortex_chat_provider` (`gateway` par défaut, `onyx`, `mock`).
- **Écritures comptables** : journal à partie double par société (`Cortex Journal Entry`), généré à chaque facture, paiement et remboursement, équilibré et immuable; plan de comptes configurable; rapports *Journal comptable* et *Balance de vérification*; reprise des factures existantes (patch `backfill_journal_entries`). Contrôles d'intégrité ajoutés à la simulation.
- **Navigation façon Claude** : marque et fil d'Ariane à gauche, catégories repliables, icônes d'origine, « Nouvelle location » et bouton de repli, présence en temps réel dans la barre du haut, titre et sous-titre sur chaque page, assistant IA en deuxième catégorie; grille de disponibilité dense, une catégorie par sous-page.
- **Navigation et temps réel** : barre latérale Cortex persistante et épurée (rôles, pastille d'approbations, repliable, tiroir mobile), recherche lisible, menu Aide (assistant, support), demandes de support (`Cortex Support Request`), équipe en ligne et activité en temps réel (`api/v1/presence.py`, `services/team_activity.py`, événement `cortex_activity`), transitions et survols plus fluides, listes plus lisibles (dates courtes, approbations en phrases), cartes en deux colonnes sur téléphone. Nouveau compte simulé `sim.proprio@cortex.test` (propriétaire complet).
- **Facturation Cortex** (`docs/adr/ADR-005-facturation-cortex.md`) : réglages financiers par société (TPS 5 %, TVQ 9,975 %, acompte 30 %, règle de frais de retard désactivée par défaut), facture d'acompte à la réservation, facture finale à la clôture (moins l'acompte), frais de retard configurables, paiements et remboursements immuables (`api/v1/billing.record_payment`, audités, idempotents), vues financières maison (cartes, graphiques, rapports *Créances par client* et *Taxes perçues*), espace Finance sans raccourcis comptables ERPNext. Emplacement vidéo « à venir » dans le guide de démarrage.
- **Audit de 91 jours et tests de charge** (`docs/audit/AUDIT_SIMULATION_90_JOURS.md`, `dev_tools/simulate_company.py`, `dev_tools/charge_et_concurrence.py`). Défauts corrigés : verrou de réservation relâché avant la validation (double réservation de la dernière unité), approbations impossibles pour un gestionnaire, attribution des séries sans dates, idempotence en parallèle, numérotation des règles tarifaires par société, droits rapport/export/impression, lecture des clients, séries et demandes entrantes, société par défaut des rapports, grille de disponibilité qui ne s'affichait plus.
- **Interface :** arrivée sur l'espace Cortex Rental, « Paramètres » au lieu de « Paramètres ERPNext », cartes en noir, graphique des locations par jour, description des étapes du guide, fil d'Ariane sous Cortex Rental, bouton copilote rond sur téléphone, cartes kanban avec date et total, formats québécois.
- Plans : application mobile (`docs/mobile/MOBILE_APP_PLAN.md`) et décision du moteur IA (`docs/architecture/AI_ENGINE_DECISION.md`). Captures complètes dans `docs/review/captures/`.
- **Cortex is now 100 % native ERPNext (decision of 2026-09-30).** Vite, Frappe UI, the standalone `/cortex` app, the Desk host and the 26 shell Pages are removed (Git history keeps them; patch `remove_shell_pages` deletes the orphan Page records, `clear_default_app` the old `default_app`).
  - **Workspaces in the style of ERPNext *Accounting*:** hub *Cortex Rental* plus *Opérations*, *Entrepôt*, *Catalogue*, *Finance*, *IA* and *Administration* with a native onboarding block (*Module Onboarding*), charts, 26 number cards, shortcuts with live counts, quick lists and link cards.
  - **AI home** (`cortex-home`, Frappe bundler, Vue 3): first page after sign-in ("Que puis-je faire pour vous ?"), composer, role-based prompt suggestions, workspace tiles, recent conversations, honest configuration message when Onyx is not configured. Landing redirect via `boot_session` flag + `public/js/cortex_desk.js`.
  - **Native views:** state indicators for rentals, approvals, check-ins, inbound requests, payouts and extraction runs; Kanban *Locations par état*; calendar and Gantt for rentals; rental form actions (reserve, request contract, check-out by scan, return) and approval decision buttons, all through `cortex_rental.api.v1.*`; five script reports (*Disponibilité du parc*, *Prochains départs et retours*, *Activité des clients*, *Versements de consignation*, *Relevé propriétaire*).
  - **French only:** `translations/fr.csv` for Cortex strings and patch `set_french_default` (site language and users without an explicit choice); rental form regrouped in sections.
  - **French coverage:** user-facing server errors and DocType field help translated; ~1,400 strings in `translations/fr.csv` (Frappe/ERPNext gaps, module onboarding help, roles, chart names); signed-out visitors get French pages; `cortex_i18n.js` fixes English strings hardcoded in Frappe. Record names stored as data (print formats, standard reports, roles) stay as they are.
  - `cortex-motion.css`: 150–250 ms transitions between states, skeletons, reduced-motion support.
  - Plan and status: `docs/frontend/ERPNEXT_NATIVE_PLAN.md`; contract: `docs/frontend/CORTEX_UI_HANDOFF_V2.md` v3.0. Older frontend docs are marked obsolete.
  - **Accessibility and narrow screens:** `cortex_a11y.js` names the unlabeled Frappe controls (icon buttons, list checkboxes, filters, grids, dropdowns) and `cortex-a11y.css` fixes contrast and the 320–375 px widget overflow; axe-core reports 0 violations on the home, the 7 workspaces, the grid, list, form, Kanban, calendar, Gantt, reports and approvals.
  - **Availability grid** (`cortex-availability` Page, Frappe bundler): equipment × days with free quantities from `availability.get_matrix`, category/search/period filters, cell detail with links to the rentals and "new rental that day". Indicative; the server re-checks at booking.
  - Known: Onyx is not configured on the dev bench; ERPNext labels not translated by Frappe stay in English.
- Administration screens are now real: **Règles tarifaires** (create/edit/deactivate rules with validation, duplicate protection and a server-computed reference curve), **Équipe et rôles** (profiles, deactivate/reactivate, invitations; owner protected; audited) and **Import et migration** (guided Data Import entry points and team history), backed by `api/v1/administration.py` and permission-checked. Desk Pages `cortex-rental-policy`, `cortex-team`, `cortex-import` and `cortex-audit-event` are added and linked from the Administration workspace.
- **Assistant Cortex** is a real full-screen conversation (history, structured reply blocks rendered without HTML injection, retry, clear message when Onyx is not configured); the copilot drawer renders the same blocks. New endpoint `chat.get_messages`.
- Polish pass: text-muted tokens raised to AA contrast (`#4f6f5f`, `#666666`), accessible names on icon buttons/checkboxes/progress bars, heading order, French sentence-case route titles, onboarding links stay inside the app. axe-core: 0 violations on the standalone screens audited.
- Standalone Cortex app served by Frappe at `/cortex` (Vue 3 + frappe-ui Vite plugin, `www/cortex.py`, `website_route_rules`, router base `/cortex`, short URLs). `npm run build:spa` / `make build-spa`; built by the Docker entrypoint. Vue sign-in, forgot-password, email-link and access-request screens, account menu (profile, Desk, sign out), and `add_to_apps_screen` + default app so signed-in users land on `/cortex`. The Desk pages remain.
- The standalone shell no longer ships invented data: universal search lists real pages and searches rentals/equipment through the API, the approvals badge is unknown until the server answers, the Copilot calls the chat gateway instead of a scripted reply, and the mobile tabs no longer point at demo rentals. Sidebar is expanded by default.
- Sign-in polish from design review: raised form block, larger lead, `Envoyer le lien`, `← Retour à la connexion`, more visible brand label.
- New two-panel sign-in (`/login`) in the app's own font and tokens (Inter, Cortex green), light and dark, adaptive from 320 to 1920 px, with inline errors, a busy state and visible labels. Frappe's « Powered by » footer credit is removed. axe-core reports no violations in either scheme on login, forgot password, access request, verification and new-password pages.
- Enterprise access flow: two-step access request → email verification (single-use, hashed token) → manual or automatic approval (`Cortex Access Settings`) → provisioning of Company, owner user (never `System Manager`), company-scoped permissions and default 7-for-3 pricing rule → new-password page → guided company setup at `/app/cortex-company-setup` (profile, team invitations, catalog, rental rules). Complete forgot-password flow with anti-enumeration and a resend cooldown. Branded email templates.
- Google and GitHub sign-in buttons appear only when the corresponding Social Login Key is enabled with real OAuth credentials (see `docs/auth/LOGIN_AND_ONBOARDING.md`). Apple is not implemented.
- Adds the `cortex-login` agent skill (`.claude/skills/cortex-login`) and unit tests for the access rules, auth pages and onboarding contract.
- Known: `shellResponsiveChallenge.spec.ts` reports an unhandled `fetch` to `localhost:3000` (logout) when run without a backend; it is present on the base branch too.
- All Desk pages now mount the same Vue 3 + Frappe UI bundle (`npm run build:desk`). The legacy esbuild pages (availability, check-in, composer, customers, fleet, supervision, P&L) are removed; `cortex-customers`, `cortex-fleet` and `cortex-supervision` showed hard-coded demo data and are replaced by real read models (`customers.list_customers`, equipment list, AI Inbox approvals).
- The profit-and-loss screen reads ERPNext's report and shows an explicit error when it fails instead of zeros (`reportError`).
- Fixes unstyled `/login` and `/me` pages: `bench build --app cortex_rental` alone does not build Frappe's website and desk bundles; `entrypoint-bench.sh` now runs a full `bench build` when they are missing.

## v0.5.0 — 2026-09-23

This release establishes the ERPNext-first, AI-native Cortex workspace and documents the implementation contract for future product and AI agents in `docs/frontend/CORTEX_UI_HANDOFF_V2.md`.

- Adds the Cortex AI Inbox, Workspace, and Audit views, with human review boundaries and server-owned decision rules.
- Connects rental composition, availability, approvals, check-in/check-out, and evidence workflows to Frappe domain APIs; pricing and inventory decisions remain server-side.
- Adds the Onyx/Ollama chat gateway and local deployment guidance. The local Qwen3 8B setup is configured, while complete browser-to-model workflow and tool execution still require end-to-end validation.
- Fixes session initialization and router loading so concurrent session checks are shared and a stalled Frappe session request times out instead of leaving the app loading indefinitely.
- Fixes Vite dependency interop for Feather Icons and `debug` in the frontend development build.
- Updates the ERPNext-inspired shell and responsive operational screens. Pixel-perfect parity with the supplied reference has not yet been confirmed by screenshot review.

Release validation: frontend production build, targeted session/router/API tests, Python compilation, and local service checks passed. The full frontend suite had one dynamic-import timeout under load (250 tests passed); that isolated route-import test passes when run alone, so the complete suite is not represented as fully green.

Known limitations: contract/invoice workflows, outbound customer messaging, full document-ingestion lifecycle, team assignment, and accounting integrations need further API/permission validation. Onyx chat and tool execution require end-to-end verification. See the canonical handoff for current scope and evidence.

---

Scope of this pass: a Claude security/design review of the Gemini-generated
`cortex_rental` Frappe app, `cortex-mcp` FastMCP facade, and supporting
infra found several BLOCKER/HIGH-severity gaps against the Cortex PRD
(multi-tenant isolation, state-machine enforcement, idempotency, CI
integrity, availability correctness, and a few PostgreSQL/duplication
inconsistencies left over from the Frappe migration). This changelog
documents what was found, what was fixed, and what remains open.

No prior git history existed for this branch — the Gemini-authored
scaffold was committed as a `chore: import initial Frappe/ERPNext
scaffold (baseline)` commit first, and every fix below is a separate,
atomic commit on top of it so the diff for each phase is reviewable on
its own.

Repository: https://github.com/Endsi3g/cortex-erp-ai-native
Branch: `test/PRD-demo-scenario`

---

## Phase 1 — Multi-tenant Company isolation (`ec59bb6`)

**Problem.** `X-Company-ID` (and, on the MCP side, a `company` argument
on every single tool) was accepted as-is with no check that the caller
was actually authorized for that Company. Any authenticated agent or
user could read or write another tenant's data by supplying a different
value — including via an LLM tool call, which means a prompt injected
through an ingested document could redirect a request cross-tenant.
Separately, `permission_query_conditions` was wired in `hooks.py` for 4
DocTypes but the implementation was a no-op stub (`return ""`), so
row-level filtering silently did nothing.

**Fixed.**
- `get_company_context()` now resolves the caller's authorized Companies
  server-side (Frappe `User Permission`) and only accepts a
  `X-Company-ID` hint that's already in that set.
- `require_agent_scope()` now checks the actual per-tool scope
  (`SCOPE_ROLE_MAP`) instead of "any Agent Service Account role".
- `permission_query_conditions` implemented for real, extended from 4 to
  9 Company-scoped DocTypes (was missing `Cortex Rental Transaction`,
  `Cortex Inbound Request`, `Consignment Owner`, `Rental Pricing Rule`,
  `Cortex Rental Item Profile` entirely).
- `Cortex Rental Item Profile` (the equipment catalog + rates actually
  used by `search_items`) had **no** `company` field at all — every
  tenant could see every other tenant's catalog and pricing. Added.
- Core ERPNext `Customer` isn't natively Company-scoped; added a
  `cortex_company` Custom Field (fixture) and filtered `search_customers`
  / `create_customer_draft` by it.
- Every MCP tool signature/schema no longer accepts `company` at all —
  the tenant is fixed to the MCP deployment's configured Company.
- Added Role fixtures for the PRD §5 role list (previously undefined
  anywhere in the codebase — `bench migrate` had nothing to provision).

## Phase 2 — Unconditional state-machine enforcement (`b1b5adc`)

**Problem.** `Cortex Rental Transaction.validate()` only recomputed
pricing. The actual transition rules (agent-cannot-self-advance,
Contract preconditions) lived exclusively in `transition_to()` — and
`Agent Service Account` held `write: 1` at the DocType level. A direct
`doc.save()` via the generic REST API or Desk UI could set
`rental_state` straight to `Contract` or `Closed`, bypassing every
check and the audit trail. Separately, `ApprovalRequest.approve()`
only executed a mutation for `entity_type == "Sales Order"`, which
nothing in this codebase creates — approving a request against the
actual `Cortex Rental Transaction` entity used everywhere else did
nothing.

**Fixed.**
- `validate()` now unconditionally diffs persisted vs. incoming
  `rental_state` and re-runs the state-machine check, regardless of
  entry path. New documents can only be created in `Quote`.
- `Agent Service Account`'s DocType permission on `Cortex Rental
  Transaction` reduced to read-only; writes only happen through the
  audited API layer.
- `ApprovalRequest.approve()` now dispatches to the real entity via
  `transition_to()`, re-validating preconditions as the human approver.

## Phase 3 — Idempotency-Key on every mutating endpoint (`a66e32d`)

**Problem.** No endpoint deduplicated writes. An agent retry after a
network timeout — a routine MCP failure mode — would create duplicate
quotes, approval requests, customer drafts, or consignment payouts.

**Fixed.** New `Cortex Idempotency Record` DocType + `with_idempotency()`
wrapper: replays the recorded response for a matching
(Company, scope, Idempotency-Key) retry, rejects key reuse with a
different payload, resolves concurrent-retry races via the DB's own
unique-name constraint. Wired into all 4 mutating endpoints.

## Phase 3.5 — Removed a live, unscoped, orphaned API surface (`0d9184b`)

**Problem, found while cleaning up.** A whole second, unversioned
`api/{quotes,approvals,items,availability}.py` module existed alongside
`api/v1/`, superseded but never deleted — and still `@frappe.whitelist`
live. It had **no** `require_agent_scope()` call at all, read
`X-Company-ID` with no authorization check (bypassing the Phase 1 fix
entirely, since it never called `get_company_context()`), and returned
fabricated fake data instead of real DocType writes. Confirmed
unreferenced by anything operational via repo-wide grep — deleted, with
the one stale doc reference (`docs/07`) updated with an explicit
"outdated, do not use" notice.

## Phase 4 — CI/security pipelines actually test the real code (`32f7442`)

**Problem.** `.github/workflows/ci.yml` and `security.yml` were still
the pre-migration Laravel/PHP pipeline (Pint, PHPStan, Pest, composer
audit, `apps/cortex-core`, `plugins/Webkul/CortexRental`) — none of
those paths exist in this repo. Every step was gated behind
`if [ -f ... ]`, so it printed a message and exited 0 regardless. CI was
structurally unable to fail.

**Fixed.** Rewrote both workflows for the real stack: `ruff check`,
`ruff format --check`, DocType JSON schema check, `pytest apps/` on
Python 3.11 (`ci.yml`), and `pip-audit` + secret-pattern scanning
(`security.yml`). Added root `ruff.toml`; discovered and fixed a config
gotcha where each app's own `pyproject.toml` (no `[tool.ruff]` section)
silently stopped Ruff's config auto-discovery, so both CI and
`bin/pre-claude-check.sh` now pass `--config ruff.toml` explicitly.
Applied `ruff format` once across `apps/` (61 files, formatting only) so
the newly-enforced format check starts green.

## Phase 5 — Availability correctness + mutation-time locking (`69a6d91`)

**Problem.** `AvailabilityService.check()` had two independent bugs:
`frappe.db.count(...) or 5.0` treated a real, correct zero-serial count
as falsy and fabricated "5 available"; every DB error was silently
swallowed into a fake "10 available". Quarantine/repair/missing units
were never excluded (`maintenance_qty` was a permanent stub). Separately,
ADR-002 explicitly deferred the mutation-time locking strategy
("Travaux Futurs / PRD-INV-003") — nothing prevented two concurrent
confirmations of the last unit from both succeeding.

**Fixed.** Both fabrication bugs removed; DB errors now propagate.
Added a `cortex_status` Custom Field on `Serial No`
(Active/Quarantine/Under Repair/Missing/Decommissioned — core ERPNext
has no such states) and excluded non-Active units from the fleet count.
Implemented the ADR-002 locking strategy: `transition_to()` into
Reservation/Contract now acquires a short-TTL Redis/Valkey lock per
(company, item_code) and re-checks availability under that lock before
committing.

Also removed a dangling `doc_events` block in `hooks.py` referencing
`cortex_rental.overrides.*` — no such module exists anywhere in the app,
so `bench migrate` would have failed on the import.

## Phase 6 — Dead duplicate code + infra drift cleanup (`8fbb106`)

- Deleted `cortex_rental/pricing.py`: a second, diverging implementation
  of the billable-days rule (disagreed with the canonical
  `services/pricing.py` for 2- and 4-day windows). Confirmed unreferenced
  after Phase 3.5.
- Unified the two independently-drifted PII denylists
  (`services/consignment.py` vs. `consignment_payout.py`) into one
  allowlist-first, denylist-backstop design, imported once.
- Fixed `"engine": "PostgreSQL"` → `"InnoDB"` on 6 DocType JSON files —
  the actual stack is MariaDB/InnoDB; an invalid engine value risked
  breaking `bench migrate`. Updated ADR-002 to match.

---

## Evidence

### Local, full validation (`./bin/pre-claude-check.sh`, final run)

```
[1/6] Git Status & Diff Summary...                     ✓ clean tree at HEAD
[2/6] git diff --check                                 ✓ no conflicts/whitespace issues
[3/6] Ruff (--config ruff.toml)                         ✓ All checks passed! · 63 files already formatted
[4/6] pytest apps/                                       23 passed, 8 skipped in 0.07s
[5/6] DocType JSON schema check                          ✓ 11/11 DocTypes validated
[6/6]                                                     ✓ TOUTES LES VÉRIFICATIONS SONT PASSÉES AVEC SUCCÈS
```

The 8 skipped tests are frappe-gated (`@unittest.skipUnless(frappe, ...)`)
— they exercise real multi-tenant isolation, quarantine exclusion, and
concurrent-reservation rejection against Frappe/MariaDB/Redis, none of
which are provisioned in this sandbox. They're written now so the first
real `bench --site <site> run-tests --app cortex_rental` on a live bench
proves the fixes, not just documents intent. See:
`apps/cortex_rental/cortex_rental/tests/test_multitenant_isolation.py`,
`test_availability_concurrency.py`.

### Live GitHub Actions run (not just local)

Pushed to `origin/test/PRD-demo-scenario` and the rewritten CI pipeline
ran for real:

```
$ gh run watch 33285056747 --exit-status
✓ test/PRD-demo-scenario Cortex CI Pipeline · 33285056747

JOBS
✓ Shell & Workflow Validation (pre-claude-check)  in 13s
✓ Python 3.11 — Ruff, DocType schema check & pytest  in 15s
```

Run: https://github.com/Endsi3g/cortex-erp-ai-native/actions/runs/33285056747

---

## Second wave — Gemini/Onyx validation, real bench attempt, and the 4 previously-flagged follow-ups

Requested as a follow-up to the section above. Status of each item that
was explicitly out of scope in the first wave:

### Gemini model test through the Onyx system prompt (`f6da28f`)

Onyx itself is not vendored in this repo (only its YAML config) and
could not be deployed here. What was actually run: the real
`cortex_intake_system.md` system prompt against the real
`gemini-3.7-flash` model (confirmed to exist via `GET /v1beta/models` —
the PRD/`.env.example`-specified model; `gemini-2.0-flash` is
deprecated, the API's own 404 pointed at `gemini-3.6-flash` first, but
3.7 is what's actually specified) on 4 of the 10
`prompt_injection_security_tests.json` cases. All 4 (system-prompt
override, cross-tenant exfiltration, indirect document injection,
forced availability hallucination) were correctly refused/contained.
See `docs/evals/2026-08-30-onyx-intake-gemini-3.7-flash.md` — this is a
prompt-quality signal, not a security proof; the code-level fixes hold
regardless of model behavior, and the full agentic tool-calling path
still needs a real Onyx+MCP+bench deployment.

### Real Frappe bench validation — attempted, blocked by environment, not code (`0aee7dc`)

Found and fixed a real bug while trying: `infra/docker/Dockerfile.bench`
referenced `frappe/bench:v15.0.0`, a tag that has **never existed** on
Docker Hub (verified against the actual tag list) — Gemini fabricated
it. Fixed to `frappe/bench:latest` (Framework v15 is chosen via `bench
init --frappe-branch version-15`, not the image tag), and swapped its
Postgres system deps for the real MariaDB ones. Provisioning itself hit
a hard wall: pulling MariaDB/Valkey filled this sandbox's disk to 99%
(146 MB free), and Docker Desktop crashed as a result. Cleaned up
(images/volumes removed, disk back to 6.2 GB free) rather than retrying
blind — 6.2 GB is still too tight for a full frappe+erpnext+node_modules
build, and this is a sandbox disk-space limit, not something fixable in
code. The frappe-gated tests throughout this repo remain unexecuted
here; they're written and ready for the first real `bench run-tests`.

### `Rental Item` vs. `Cortex Rental Item Profile` — decided (`0aee7dc`, ADR-004)

`Rental Item` deleted (confirmed unreferenced by any service/API/test).
`Cortex Rental Item Profile` is now the sole canonical catalog DocType;
gained the two fields `Rental Item` had that it genuinely needed
(`is_serialized`, `total_quantity`) so non-serialized items are now
modeled at all — `AvailabilityService` branches on `is_serialized`
instead of always counting `Serial No` rows. See
`docs/adr/ADR-004-rental-item-catalog-consolidation.md`.

### `Cortex Agent Run` / `Cortex Agent Tool Call` — implemented (`f6da28f`)

New DocTypes + a `@log_tool_call` decorator applied to all 7 agent-facing
endpoints, recording Success/Denied/Error with timing, correlated by a
caller-supplied `X-Request-ID` (cortex-mcp's `FrappeClient` now sends
one per call, plus `X-Cortex-Agent-Id` from a new `CORTEX_MCP_AGENT_ID`
setting) — separate from `Cortex Audit Event`, which only covers
business mutations, not the agent-facing API surface itself.

### Evidence/Extraction pipeline — implemented, explicitly bounded (`580c483`)

New `Cortex Evidence Reference` (hashed file/text, gated by a
`scanned_clean` flag) and `Cortex Extraction Run` (schema-validated,
confidence-scored) DocTypes. `intake_extraction_schema.json` — previously
pure documentation — is now actually enforced via `jsonschema`, with
`review_required` set below the 0.85 confidence threshold the intake
prompt already promises. **Not** implemented: the PRD's pre-signed
S3/MinIO "Upload Intent" direct-upload flow (no upload endpoint exists
anywhere in this codebase to build on — a separate infra feature) and
ClamAV scanning (the gate field exists; nothing sets it automatically
yet). Both are real gaps, not silently dropped.

### Check-in / partial-return / quarantine workflow — implemented (`5bfced0`)

New `Cortex Check-In` / `Cortex Check-In Item` DocTypes (human-staff-only,
no MCP tool — physical receiving needs a person scanning serial numbers).
Completing one updates each returned `Serial No`'s `cortex_status` per
disposition and a new `returned_qty` on the transaction line; the
transaction only moves `Checked Out -> Returned` once every line is
fully back, so a partial return correctly stays `Checked Out`.

### Still open after this wave

- **No live bench validation** (see above — environment-blocked, not
  a code gap).
- **`docs/07-frappe-erpnext-implementation-guide.md`** still documents
  a superseded design iteration; flagged inline, not rewritten.
- **1-site-per-client vs. shared-site-multi-Company** — Phase 1 makes
  the shared model safe, but the lower-risk pilot default
  recommendation from the original review still stands; not decided
  here.
- **Upload Intent (pre-signed S3/MinIO) + ClamAV scanning** — see
  Evidence/Extraction section above.

---

## Third wave — Onyx self-hosted decision, widget integration, README, release

### Onyx: self-hosted, widget-integrated, Gemini as default provider

Decision (2026-08-30): Onyx runs **self-hosted** (not Onyx Cloud), with
Gemini configured as its default LLM provider, and its chat surfaced
inside Cortex via the official `<onyx-chat-widget>` web component
rather than requiring a separate tab. Verified against the real Onyx
docs/GitHub repo before writing anything, following the same discipline
as the earlier `frappe/bench:v15.0.0` catch — no service names, image
tags, or config keys were guessed:

- `infra/onyx/README.md`: deployment via Onyx's own official installer/
  `docker-compose.yml` (`onyx-dot-app/onyx` — `relational_db`, `index`,
  `opensearch`, `cache`, `inference_model_server`, `minio`), explicitly
  **not** vendored into this repo's own compose file (a separate,
  independently-versioned stack, matching the PRD's "service
  indépendant" requirement as Onyx's own architecture, not just a
  Cortex preference). Documents the MCP-only connection path (Onyx never
  talks to Frappe/MariaDB directly) and that Gemini-as-default is
  configured through Onyx's own Admin Panel (Settings → LLM Providers)
  — no reliable env var name for this was found, so it's documented as
  a manual step rather than invented.
- `apps/cortex_rental/cortex_rental/www/onyx-assistant.{html,py}`: a
  Frappe `www` page (verified pattern: `.html` + `.py` with
  `get_context()`) embedding the widget, authenticated-users-only,
  reading `onyx_backend_url` / `onyx_widget_api_key` /
  `onyx_widget_script_url` from `site_config.json` (never committed).
  Explicitly documented as not weakening any server-side check — the
  widget is client-side UX; every real tool call still goes through
  Cortex MCP → the whitelisted, scope/tenant-checked API.
- **Known gap, not hidden**: the widget JS bundle's exact served path
  on a self-hosted deployment was not verified (public docs only show
  the cloud example `https://your-cdn.com/onyx-widget.js`) — the page
  defaults to `{backend_url}/widget/onyx-widget.js` but this needs
  confirming against a real deployment. `onyx_widget_api_key` must be a
  chat-only, limited-scope Onyx key (their docs are explicit it's
  visible in client-side page source).

### README, first release, PR fixes

- `README.md` updated to match the actual current DocType/service/
  endpoint inventory (was missing every DocType and service added in
  waves one and two), corrected two stale DocType names
  (`Cortex Consignment Owner`/`Cortex Approval Request` → their real
  names `Consignment Owner`/`Approval Request`), added the Onyx
  self-hosted + widget architecture, and links to `CHANGELOG.md`,
  `HANDOFF.md`, `infra/onyx/README.md`, and ADR-004.
- Fixed the failing `PR Conventions & PRD Compliance` check
  (`.github/workflows/pr-verification.yml`) on PR #1: it requires the
  PR description to reference a canonical PRD tag
  (`PRD-ARCH`/`PRD-NFR`/`PRD-TRX`/etc.), which the original description
  didn't include despite covering all of them.
- First tagged release: [v0.1.0](https://github.com/Endsi3g/cortex-erp-ai-native/releases/tag/v0.1.0)
  (notes mirror this changelog's summary).

---

## Fourth wave — README overclaim corrections (external review)

An external review of `README.md` (after v0.1.0) correctly flagged
several statements that were too strong for a codebase that has never
run against a live Frappe bench, plus a few real ambiguities. All
addressed directly in `README.md`, not just noted:

- Removed the "garantit zéro surréservation" claim — replaced with
  "conçu pour prévenir", matching what's actually been validated (unit
  tests in mock mode, no live concurrency test).
- The architecture diagram's "Authentification / Token + X-Company"
  block was genuinely ambiguous — could read as if the header
  authenticates. Split into separate Auth / Authz / Tenant-resolution
  lines matching what Phase 1 actually built.
- `Cortex Rental Transaction`'s `Closed` state clarified as operational,
  not financial — there is in fact no `erpnext_sales_invoice` link
  field yet, so this is a real, now-documented gap (added to
  `HANDOFF.md`'s open items), not just a wording fix.
- The Redis/Valkey lock description upgraded from "verrou atomique" to
  an accurate description of what it actually does: per-`item_code`
  (not per-`serial_no`) coordination + a re-check before write, with no
  MariaDB `SELECT ... FOR UPDATE` layered under it yet (ADR-002 already
  said this; the README didn't reflect it).
- `Audit Event`"append-only immuable" softened to "append-only
  applicatif" with the concrete gap named (`frappe.db.set_value()`,
  direct SQL, bench console, System Manager break-glass access aren't
  covered by the DocType hooks) — tracked as a new open item
  **PRD-ARCH-AUD-001** in `HANDOFF.md`.
- The Onyx widget integration marked "expérimental / à valider en
  staging" in both places it's mentioned, rather than implying it's a
  stable, verified integration.
- Added a "Statut de maturité" table (implemented vs. validated vs.
  proven-under-load, per domain) and a "before any pilot" checklist,
  both linking to `HANDOFF.md` rather than duplicating it.
- New `docs/compatibility-matrix.md`: the actual pinned vs. unpinned
  versions across the repo (Frappe/ERPNext are genuinely unpinned —
  `bench init --frappe-branch version-15` selects a branch, not a
  patch — and cortex-mcp's three Python version references
  (`pyproject.toml` `>=3.10`, Dockerfile `3.12-slim`, ruff `py311`)
  aren't aligned). Written from what the config files actually say, not
  guessed.

---

## Fifth wave — first real screen: Cortex Availability + Workspace

**Problem.** A first successful deploy against a real bench (screenshot
from a second machine) surfaced the actual gap this whole session had
been building toward but hadn't yet closed: no Frappe Workspace, no
custom page, nothing under `/app/cortex-*` — every backend fix so far
(DocTypes, services, whitelisted API methods) had no UI in front of it.
Opening the site showed the stock Frappe `Users` workspace and nothing
Cortex-specific to click. This wave builds the first real screen end to
end rather than adding more backend that stays invisible.

**Scope for this pass** (explicitly narrowed, confirmed with the user):
Workspace + the Availability matrix only — the first two items of the
five-screen priority order below. Composer/Check-in/Approvals/Assistant
are follow-ups, not attempted here.

**Frontend approach.** Verified against real, current sources before
writing anything (not guessed): the framework's own documented
["Using Vue in a Desk Page"](https://docs.frappe.io/framework/using-vue-inside-a-desk-page)
pattern — a native Frappe `Page` (`/app/cortex-availability`) whose
controller `frappe.require()`s a `.bundle.js` that Frappe's own
`bench build` compiles automatically, no separate npm/vite project, no
extra build step beyond what a Frappe bench already runs. This was
chosen over the `frappe-ui/vite` SPA plugin (also real, verified against
`frappe-ui`'s own `vite/README.md`) because that plugin serves a
top-level route (e.g. `/g`) outside the `/app/*` Desk namespace the PRD
explicitly wants these five screens under — it's the right tool for a
detached SPA (à la Helpdesk/CRM), not for a Desk-native page.
`frappe-ui`'s own component library is **not** imported yet: a real,
currently-open upstream issue documents esbuild breaking on
`frappe-ui` imports inside this exact Desk-page bundle pattern, and
there's no bench here to debug that against — the page is hand-built
with plain Vue 3 + scoped CSS instead, so it has zero new npm
dependencies to fail to install. Revisit `frappe-ui` for the next
screen once a real bench confirms the import issue does or doesn't
reproduce here.

**Added.**
- `cortex_rental/api/v1/availability.py`: `get_matrix` — a new
  human-staff-only (`require_human_staff_role`, no MCP tool, no agent
  scope) whitelisted method distinct from the existing agent-facing
  `check_availability`. Returns, per `Cortex Rental Item Profile`
  matching the Company/category/search filters, every transaction
  (`Quote`/`Reservation`/`Contract`/`Checked Out`) overlapping the
  requested window, plus a `has_conflict` flag. Company is always
  server-resolved via `get_company_context()` — never accepted from the
  client, same invariant as every other endpoint in this repo.
  Disclosed simplification: `has_conflict` sums blocking quantity across
  the *whole* requested window rather than sweeping day-by-day, so it
  can under-report a conflict confined to a sub-range — a visual aid
  only, not a booking-safety authority (that's still
  `AvailabilityService` at confirmation time, unchanged).
- `cortex_rental/cortex_rental/page/cortex_availability/`: the Page
  doctype record + controller, role-gated to the same
  `HUMAN_STAFF_ROLES` set as the backend (defense in depth, not the
  only gate).
- `cortex_rental/public/js/cortex_availability/`: `CortexAvailability.vue`
  + `cortex_availability.bundle.js`. Day/week/month toggle (month is a
  30-day rolling window, not a calendar-month grid — disclosed
  simplification, not built to avoid scope creep in this pass), category
  and state filters in a **collapsible sidebar with a real CSS width/
  opacity transition** (not the binary show/hide the user flagged as a
  bad interaction — this is scoped to Cortex's own pages only, per the
  user's explicit choice, not a change to Frappe Desk's native sidebar),
  search, per-item lane-stacked transaction blocks (blocks never
  overlap visually within a row even when multiple `Quote`s share a
  window), a conflict badge, and a color+icon+text badge for every state
  (never color alone, per the user's explicit requirement). Clicking a
  block navigates to the real `Cortex Rental Transaction` form
  (`frappe.set_route`); "Créer une soumission" opens a real
  `frappe.new_doc()` prefilled with the visible date range and the
  server-resolved Company — equipment lines still need to be added
  manually on the form (prefilling a child-table row from a route
  param is a real follow-up, not faked here).
- `cortex_rental/cortex_rental/workspace/cortex-rental/`: the `Cortex
  Rental` Workspace — shortcuts (Disponibilité, Transactions,
  Approbations, Assistant Onyx) and cards (Opérations, Catalogue,
  Clients, Finance, Intelligence, Administration) link **only** to
  DocTypes/pages that exist in this repo right now. Nothing points at a
  screen that hasn't been built yet — that's exactly the "text with
  dead links" complaint this wave exists to fix.
- Two new tests in `test_demo_scenario.py` covering `get_matrix_handler`
  (required-field validation, and the labeled-mock fallback when no
  live Frappe/DB is available — same contract as the existing
  `AvailabilityService` mock branch).

**Not done in this pass** (tracked in `HANDOFF.md`): Composer/Check-in/
Approvals/Assistant screens, `frappe-ui` component adoption, and any
verification against a live bench — this was written and syntax/unit-
tested here, but never opened in a browser, because no bench is
reachable from this environment. See `HANDOFF.md` §2 for the exact
build/reload commands to run on the machine that does have one.

---

## Sixth wave — Cortex Operations System design system foundation

**Problem.** A live screenshot from a real deployment (tower machine)
showed the app working but visually bare — no design system, no
reusable components, hand-copied colors per page (Availability's own
ad-hoc `STATE_META`). The user supplied a detailed, prescriptive design
spec ("Cortex Operations System": tokens, typography, spacing, 9
foundation components, WCAG 2.2 AA requirements) and asked for it to be
implemented — explicitly scoped to the foundation only, not the
remaining operational screens.

**Packaging decision** (confirmed with the user before writing code):
the spec's literal `apps/cortex_rental/frontend/` npm+Vite+TypeScript
project was **not** adopted. CSS custom properties + plain Vue SFCs
under `public/`, no new build pipeline — same reasoning as the fifth
wave's Desk-Page-over-SPA choice: a second, unverified build pipeline
with no bench to test it against would repeat a risk already avoided.
Tailwind (also specified) wasn't adopted for the same reason (needs a
PostCSS/Vite build step) — a small hand-rolled utility set instead.

**Added.**
- `apps/cortex_rental/cortex_rental/public/css/`: `cortex-tokens.css`
  (full palette + business-state tokens, spacing/radius/shadow/motion/
  focus-ring), `cortex-theme.css` (typography scale, focus-visible ring,
  `prefers-reduced-motion`, everything scoped under `.cortex-app` so
  nothing here can touch core Frappe Desk styling), `cortex-utilities.css`
  (buttons, badges, density modes, skeleton shimmer). Wired via
  `hooks.py`'s `app_include_css` (verified real hooks.py keys against
  docs.frappe.io before use — not guessed).
- `apps/cortex_rental/cortex_rental/public/js/cortex_shared/`: nine
  components (`CortexStatusBadge`, `CortexRiskBadge`,
  `CortexReadinessIndicator`, `CortexEmptyState`, `CortexPageHeader`,
  `CortexEvidenceLink`, `CortexAuditTimeline`, `CortexLoadingState`,
  `CortexErrorState`) plus `stateMeta.js`, the single source of truth
  every badge reads from (real `rental_state`/`cortex_status` values →
  design-token keys). `CortexEvidenceLink` and `CortexAuditTimeline` are
  explicitly placeholders — they render caller-supplied data, no real
  preview/download or Audit Event query wired yet.
- **États — wired vs. reserved** (`docs/design-system.md`): the spec
  proposes 16 state tokens; only 12 correspond to a real DocType value
  today (`Cortex Rental Transaction.rental_state` or
  `Serial No.cortex_status`). `draft`, `partial_return`,
  `invoice_prepared`, `invoiced` are defined as tokens (forward
  compatible) but explicitly marked as not reachable by any screen
  today — the same "no dead links" discipline as the Workspace, applied
  to design tokens.
- `bin/check-contrast.py`: a dependency-free WCAG 2.2 AA contrast
  checker (no JS test runner exists in this repo) that parses the
  actual shipped CSS tokens and computes real contrast ratios. **First
  run found every single state badge's border color from the spec
  failed the 3:1 non-text-contrast minimum against the page** — the
  pastel ~50-level border tints measured as low as 1.36:1, because the
  badge fills themselves are only ~1.1:1 against white, so the border
  is what actually has to carry the component's visible boundary, not
  decorate it. Fixed by swapping every state's border to its palette's
  500/600/700-level shade (same hue, same intent, real contrast) — not
  eyeballed, re-verified by the same script until it passed clean.
  Also caught and fixed two text-contrast shortfalls (`cancelled` label
  at 4.34:1, destructive-button hover text at 4.41:1, both under 4.5:1).
- Retrofitted `CortexAvailability.vue` (fifth wave) onto the new
  system: `CortexPageHeader` replaces its hand-rolled toolbar, calendar
  bars/legend/sidebar dots pull color and label from `stateMeta.js`
  instead of a locally duplicated map, loading/error/empty states use
  the new shared components, and every hardcoded hex color in its
  `<style>` block is now a `var(--cortex-*)` token reference. Confirms
  the design system actually works on a real screen rather than staying
  an unused foundation (deliberate choice, confirmed with the user).
- Branding: `app_logo_url`/`app_icon`/`app_color` in `hooks.py`
  (verified real hooks.py keys) plus a placeholder indigo monogram SVG
  — a real brand mark is a later decision, not invented here.
- `docs/design-system.md` and `docs/design-system-component-contracts.md`.

**Not done in this pass** (by design, per the spec's own scoping and
the user's confirmed choices): dark mode (light-mode tokens only —
the spec itself warns against a "faux dark mode" shipped unvalidated),
responsive breakpoints (no page needs tablette/mobile layout yet),
`frappe-ui` component adoption (same known esbuild-import risk as the
fifth wave), and the remaining page-specific components
(`CortexAvailabilityCell`, `CortexSerialAssignment`,
`CortexApprovalCard`, etc.) — those arrive with the screen that
actually uses them, not as unused scaffolding.

---

## Seventh wave — Cortex Chat Gateway backend (mocked, no live Onyx)

**Problem.** The user supplied two large specs: a Cortex↔Onyx chat
backend architecture and a Copilot UI panel. Explicitly scoped down
with the user before writing code (both specs are individually a
multi-day build) to backend first, mocked, no UI, as its own reviewable
PR — the panel is a separate follow-up PR once this contract exists.

**Security shape, enforced structurally, not just by convention.**
`SendMessageRequest`/`ChatContext` (`schemas/chat_schemas.py`, Pydantic
v2, `extra="forbid"`) have no field for `company`, `agent`, `model`, or
`allowed_tool_ids` at all — a client that tries to send one gets a hard
validation error, not a value that's silently ignored. Verified with a
throwaway script before writing any service code (sending each of those
four keys and confirming `ValidationError`), then locked in as tests
(`test_chat_gateway.py::TestClientCannotEscalate`).

**Added.**
- Three DocTypes: `Cortex Chat Session` (one per user/company/agent,
  `agent_profile` always server-resolved), `Cortex Chat Message`
  (human/agent/system turns, `content_sanitized` never a raw prompt),
  `Cortex Chat Context Snapshot` (the *resolved*, permission-checked
  context, not whatever the client originally sent). Chat privacy is a
  new permission dimension beyond Company scoping — two staff at the
  same Company must not read each other's conversations — added as
  `_own_chat_session_condition`/`_own_chat_child_condition` in
  `permissions/__init__.py` (Company filter AND `user =
  frappe.session.user`, bypassed only for System Manager).
- `services/agent_router.py`: `AgentRouter.resolve_agent(page)` — takes
  only a page, no client-requested-agent parameter exists to override
  it with (enforced by a test that inspects the function signature).
- `services/tool_policy.py`: `ToolPolicyResolver` — per-agent allowlist
  built only from tool names that actually exist in
  `apps/cortex-mcp/cortex_mcp/server.py` today (`search_rental_items`,
  `search_customers`, `check_inventory_availability`,
  `create_quote_draft`, `create_customer_draft`,
  `submit_approval_request`, `prepare_owner_statement`). The spec calls
  for three read-only agents (`cortex-returns`, `cortex-approval-
  assistant`, plus part of `cortex-operations`) that need a read-only
  MCP tool that doesn't exist yet — given an empty tool list and
  disclosed as a real gap in `HANDOFF.md`, rather than inventing a
  `read_transaction`-style tool name that isn't real.
- `services/chat_context.py`: `ChatContextResolver` — the actual
  enforcement of "le serveur doit vérifier que l'utilisateur peut voir
  la ressource": `frappe.has_permission()` plus an explicit Company
  match check on the referenced document, raising
  `ChatContextPermissionError` (→ `frappe.PermissionError` in the API
  layer) rather than trusting the client's claim about what it's
  looking at.
- `services/onyx_chat_client.py`: `OnyxChatClient` interface +
  `MockOnyxChatClient` — deterministic, keyword-driven (not random), so
  every response is explicitly labeled as simulated and never fabricates
  a real system fact (e.g. never claims a specific quantity is
  available). This is the one seam a real Onyx-calling client would
  implement later.
- `services/chat_response_transformer.py`: validates every raw block
  through the same `ChatBlock` discriminated union the frontend
  contract is written against (`TypeAdapter`) — a malformed block
  becomes a visible `ErrorBlock`, never a crash or a silently dropped
  answer.
- `services/chat_telemetry.py`: reuses the existing Cortex Agent
  Run/Tool Call trail (`services/agent_telemetry.py`) rather than a
  parallel logging system — required a small, backward-compatible
  change to `record_tool_call()` (added optional `agent_id`/
  `request_id` overrides) since chat calls come from a human Desk
  session, not an MCP call with `X-Cortex-Agent-Id` headers.
- `services/chat_session.py`: `ChatSessionService`, the gateway
  orchestrator — rate limiting via `frappe.cache()` (real Frappe API,
  not guessed), a real no-DB fallback path (same convention as
  `AvailabilityService.check()`'s mock branch) so the full
  validate→route→policy→mock-client→transform pipeline is genuinely
  exercised by tests in this sandbox, not just written and hoped-for.
- `api/v1/chat.py`: `create_session`, `send_message`, `get_session`,
  `list_sessions`, `pin_context`, `clear_context` — all
  `require_human_staff_role` (same gate as `checkin.py`), no MCP tool,
  not part of the agent-facing surface.
- 18 new tests (`test_chat_gateway.py`), 17 running for real in this
  sandbox (client-escalation rejection, agent-router/tool-policy drift
  detection, mock-client labeling, transformer error handling, full
  send-message round trip) plus 1 correctly `skipUnless(frappe, ...)`
  for real cross-user isolation on a live bench.

**Not done in this pass** (tracked in `HANDOFF.md`): no real Onyx HTTP
client, no streaming/SSE, no `CortexCopilotPanel` frontend (separate
PR, stacked on this one), the read-only MCP tool gap above, and no
retention/deletion job for `Cortex Chat Session.retention_until` (field
exists, nothing populates or enforces it yet).

---

## Eighth wave — Cortex Copilot Panel (real backend, mocked Onyx)

**Problem.** Follow-up to the seventh wave, per the user's confirmed
sequencing ("backend first, panel next"). Builds the floating,
non-modal chat panel from the copilot-panel spec — but wired to the
**real** `cortex_rental.api.v1.chat` endpoints from wave seven, not
client-side mock data, since that backend already exists and works.

**New verified pattern**: `app_include_js` referencing a `.bundle.js`
with ESM imports, resolved globally on every Desk page (not just one
Page's own bundle) via `frappe.ready()`. Cross-checked against two
independent searches (Frappe v14 migration notes: `app_include_js`
moved from raw JS paths to bundle references; a Frappe forum thread on
`app_include_js` + `import` + esbuild) before writing
`cortex_copilot.bundle.js` — this is the mechanism that makes the
launcher appear on every page, not just a single Desk Page's route.

**Added.**
- `public/js/cortex_copilot/`: `CortexCopilotPanel.vue` (floating or
  docked mode), `CopilotHeader`/`ContextBar`/`QuickActions`/
  `Conversation`/`Composer`, and eight block renderers — one per real
  `ChatBlock` type from `schemas/chat_schemas.py`
  (`CopilotVerifiedFact`, `CopilotExtractedData`, `CopilotProposalCard`,
  `CopilotApprovalCard`, `CopilotRiskCard`, `CopilotMissingInfoCard`,
  `CopilotToolProgress`, `CopilotErrorCard`) — matching the backend
  contract exactly rather than the slightly different component list
  named in the earlier draft spec, since wave seven's shipped schema is
  the authority now, not a prompt written before it existed.
  `chatClient.js` calls the real endpoints; nothing here fabricates a
  response.
- `public/js/cortex_assistant/` + `cortex_rental/page/cortex_assistant/`:
  the detached `/app/cortex-assistant` Desk Page, same verified
  Vue-in-a-Desk-Page pattern as Disponibilité (fifth wave), hosting the
  same panel component in "docked" mode.
- Global launcher: `hooks.py`'s `app_include_js` +
  `cortex_copilot.bundle.js`, hidden for `Guest` and non-staff roles as
  a client-side courtesy (the real gate stays
  `require_human_staff_role()` server-side, unaffected either way).
- Reuses design-system components directly rather than duplicating them:
  `CortexReadinessIndicator` for approval requirements,
  `CortexErrorState`/`CortexEmptyState`/`CortexLoadingState` for panel
  states — exactly the "don't duplicate Frappe UI/Cortex components"
  rule the design system doc itself states.
- Workspace: added a real "Assistant Cortex" shortcut to
  `/app/cortex-assistant`; relabeled the existing widget shortcut
  "Assistant Onyx (widget, expérimental)" so the two aren't confused —
  one is a real, working chat backed by this wave's gateway, the other
  is the still-unverified `<onyx-chat-widget>` embed from the fourth
  wave.
- `docs/frontend/copilot-panel.md`: full file map, the verified
  `app_include_js`/`frappe.ready()` pattern, and an explicit table of
  what's real vs. a disclosed simplification in this pass (no context
  editor, no live route-change reactivity, proposal/approval buttons
  re-engage the real chat pipeline or navigate to a real existing Form
  rather than opening screens that don't exist yet, no streaming).

**Honesty choices worth calling out**: `CopilotProposalCard`'s primary
button does not create anything — there is no Transaction Composer yet
to open prefilled, so it re-sends the proposal's own title as the next
message through the real pipeline instead of faking a mutation.
`CopilotApprovalCard`'s button navigates to the real `Approval Request`
Desk Form (which does exist) rather than a fabricated approvals queue
screen.

**Not done in this pass** (tracked in `HANDOFF.md`): no streaming, no
context editor drawer, no live reactivity to Desk navigation while the
panel stays open, and still no real Onyx client underneath any of this
— every response rendered here comes from `MockOnyxChatClient`.

---

## Ninth wave — Copilot panel: context editor + live route reactivity

**Problem.** Two items disclosed as "not built" at the end of the
eighth wave, picked up as a direct continuation: a real context editor
(not a fake one) and live context reactivity as the user navigates
Desk while the panel stays open.

**Verified before writing**: `frappe.router.on('change', ...)` is the
current, real Frappe client event for route changes — cross-checked
against a current forum answer, deliberately not the older
`frappe.route.on(...)` form that also turns up in search results (a
pre-2018, since-refactored API). `frappe.router.off(...)` is called
symmetrically on unmount but only behind a truthiness guard, since its
existence wasn't independently confirmed the way `.on()` was — if
missing, the listener leaks rather than crashing the panel.

**Added.**
- `CortexCopilotPanel.vue`: `frappe.router.on('change', ...)` keeps the
  context bar (and the next message's payload) in sync with Desk
  navigation, without touching any already-sent message.
- `CopilotContextBar.vue`: a real "Modifier le contexte" toggle —
  scoped honestly to the one field this app actually resolves (whether
  the currently open document is included in the next message). No
  checkboxes for "item sélectionné"/"documents ajoutés" from the
  original mockup — nothing produces that selection state in this app
  yet, so no control that would silently do nothing.
- The share/don't-share choice resets to "shared" whenever the
  referenced document itself changes (a per-message decision, not a
  sticky preference that should carry over onto an unrelated document).

**Not done** (still tracked in `HANDOFF.md`): everything from the
eighth wave's remaining list — streaming, wiring proposals to a real
Transaction Composer, and a real Onyx client.

---

## Tenth wave — Cortex Transaction Composer

**Problem.** Continuation of the screen-by-screen build, per the
design spec's own explicit priority order (Disponibilité, then
Composer, then Check-in — Disponibilité and the Copilot Assistant were
already done). `/app/cortex-transaction-composer`: customer search/
create, item search, live pricing, live per-line availability, real
quote creation.

**Almost entirely built on existing backend** — `search_customers`,
`create_customer_draft`, `search_items`, `check_availability`, and
`create_quote_draft` all already existed (from earlier waves/the
original Gemini scaffold) and are gated by `require_agent_scope`,
which already grants access to any `HUMAN_STAFF_ROLES` member — no new
permission plumbing needed, just a real caller.

**One new endpoint**: `api/v1/quotes.py::preview_pricing` — a
read-only twin of the existing `create_draft_handler`, same
`PricingService` calls, nothing persisted. Added because the design
system explicitly forbids computing price in JavaScript ("Le prix est
présenté comme résultat du PricingService, pas comme calcul
frontend") — there was no honest way to show a live price preview
while composing without it. Unlike `create_draft_handler`, a missing
`unit_rate` defaults to `0.0`, not a fabricated `100.0` — a live
preview silently showing a fake $100/day would be worse than an
obviously-wrong $0.

**One real bug fix bundled in**: `create_quote_draft`'s `lines`
argument now gets `frappe.parse_json()`'d when it arrives as a string
— how a browser's `frappe.call()` form-encodes a nested array. This
endpoint had previously only ever been called with a real Python list
(MCP, tests), so this path was untested until a browser caller
actually needed it; it would have silently corrupted every quote a
human created through this page otherwise (iterating a JSON string's
characters instead of its line objects).

**Explicitly not built, and explained why in
`docs/frontend/transaction-composer.md`** rather than left ambiguous:
serial number auto-assignment (a Quote never blocks inventory —
serials are only claimed at Reservation confirmation, so building this
on the Composer would imply a guarantee this state doesn't make),
customer-tier automatic discounts (no such logic exists in
`PricingService`), and a readiness indicator during composition
(`create_draft_handler` always returns all three readiness flags
`false` — nothing computes real readiness before the transaction
exists; shown honestly on the real Form after creation instead).

**Added.**
- `cortex_rental/page/cortex_transaction_composer/` +
  `public/js/cortex_transaction_composer/`: the page, same verified
  Vue-in-a-Desk-Page pattern as every other Cortex screen.
- `public/js/cortex_shared/dateUtils.js`: `fmtDateTime`/`addDays`
  extracted from `CortexAvailability.vue` once a second page needed the
  exact same helper — not introduced speculatively.
- Availability's "+ Créer une soumission" now routes to the Composer
  via `frappe.route_options` (the real Frappe cross-page handoff
  pattern) instead of the raw native `frappe.new_doc()` form it used
  before this page existed.
- Workspace: added a "Nouvelle transaction" shortcut, positioned right
  after Disponibilité to match the priority order.
- 3 new tests (`test_demo_scenario.py`): `preview_pricing` matches
  `create_draft_handler`'s math exactly, requires a date window, and
  defaults a missing rate to `0.0` rather than a fabricated value.

**Not done in this pass** (tracked in `HANDOFF.md`): accessory/kit
suggestions, free-text lines, and permission-gated line-level discount
overrides (this pass's discount field has no permission check at all).

## Eleventh wave — Cortex Accounting / Profit and Loss Statement

**Problem.** `docs/design-system-accounting-pnl.md` specified a full
Accounting/P&L screen but its own architecture section assumed a
Next.js/shadcn stack — this app deliberately has no npm/Vite build
step (`docs/design-system.md` "Packaging"). Confirmed with the user
before building anything: stay on the existing Vue-3-in-a-Desk-Page
pattern, no second frontend stack, same as every other Cortex screen.

**Built on ERPNext's own accounting engine, not a new one.** This app
already depends on `erpnext` (see `HANDOFF.md`'s `bench get-app
erpnext` step), which owns GL Entry, Fiscal Year, and a working
`Profit and Loss Statement` report. `api/v1/accounting.py::
get_profit_and_loss` calls that report's `execute()` and reshapes its
output into the KPI/period/account-tree JSON the screen renders —
reimplementing double-entry P&L math here would have duplicated a
system ERPNext already owns correctly.

**Not verified against a live bench** (same caveat as every other
Frappe/ERPNext integration point in this app — no bench in this
sandbox). The exact column/row field names ERPNext's report returns
(`account`, `account_name`, `indent`, a "Total Income"/"Total Expense"/
"Net Profit" row by name rather than a flag) are documented assumptions
in `accounting.py`'s module docstring, not confirmed output. Only the
pure reshaping logic (`transform_pnl_report`, `_build_pnl_filters`) is
tested here (12 tests, `test_accounting_pnl.py`) — the whitelisted
endpoint itself needs a real bench run to prove ERPNext's actual
version matches these assumptions.

**New finance-only permission gate.** `require_human_staff_role()`
(used everywhere else) grants Counter Staff/Inventory Manager/
Consignment Manager access too — too broad for company-wide financial
statements. Added `require_finance_role()`
(`permissions/agent_scopes.py`), scoped to Operations Manager, Finance
Manager, Account Reviewer, and Rental Manager.

**Two toolbar fields shown disabled, not wired**: `Branch` and `Report
View` from the design mockup have no equivalent ERPNext filter on this
report — same "don't build a dead link" rule already applied to
unwired state tokens in `design-system.md`. `Company` is shown
read-only (resolved server-side via `get_company_context()`), not a
picker — this page doesn't add a second way to select tenant Company.

**Added.**
- `cortex_rental/page/cortex_accounting_pnl/` +
  `public/js/cortex_accounting_pnl/`: the page, same verified
  Vue-in-a-Desk-Page pattern as every other Cortex screen.
- `api/v1/accounting.py`: `get_profit_and_loss` (whitelisted GET),
  plus the pure `_build_pnl_filters`/`transform_pnl_report` functions.
- 4 new shared components (`public/js/cortex_shared/`):
  `CortexKpiSummary`, `CortexFinancialChart` (hand-rolled inline SVG,
  no charting library), `CortexFinancialTable` + `CortexAccountRow`
  (recursive, real `<table>`/`th scope="col"` markup — genuinely
  tabular data, unlike Availability's flex-div calendar grid). Plus
  `formatters.js::formatCurrency`. Documented in
  `docs/design-system-component-contracts.md`.
- `cortex-tokens.css`: `--accounting-income`/`--accounting-expense`/
  `--accounting-profit`, scoped separately from the general Cortex
  indigo brand palette per the spec's distinct 3-color series.
  `cortex-utilities.css`: `.cx-sr-only` (visually-hidden accessible
  fallback, used by the chart's screen-reader data table).
  Buttons/controls on this screen still use the standard
  `--cortex-primary-*` action color, not the spec's separate blue —
  keeps one action color app-wide.
- Workspace: added a "Profit and Loss Statement" shortcut and a Finance
  card link.
- 12 new tests (`test_accounting_pnl.py`), all passing without a
  bench (pure transform/filter logic, synthetic ERPNext-shaped input).
- Finalisation P&L :
  - Menu d'actions et d'export : export CSV direct côté client avec indentation hiérarchique et KPI, vue d'impression et export PDF `@media print` épurée, et lien vers le rapport natif ERPNext.
  - Drill-down interactif : clic sur les comptes feuilles (`type === "account"`) ouvrant le Grand Livre ERPNext (`General Ledger`) préfiltré sur le compte, la société et la période sélectionnée.
  - Autocomplétion native HTML via `<datalist>` pour `Fiscal Year`, `Cost Center`, et `Finance Book` chargées dynamiquement depuis l'API Frappe.
  - Sélecteur d'états financiers (*Profit and Loss Statement* actif, *Balance Sheet* et *Cash Flow* réservés).

## Twelfth wave — Cortex Check-in Scanner & Equipment Returns (PRD-RET)

**Scope & Design Decisions.**
Aligned with the user through a structured interview (`/grill-me`):
- Dedicated native Frappe Desk Page `/app/cortex-checkin` using Vue 3 SFC (same zero-npm verified pattern).
- Continuous 3-step workflow without blocking modals:
  1. *Live Scan & Colisage* (Fast scan bar, synthesized Web Audio feedback, auto-match serials, steppers for bulk non-serialized items).
  2. *Diagnostic & Revue des Écarts* (Technical inspection cards for Damaged/Quarantine/Missing items, severity, damage type, estimated repair cost).
  3. *Bilan, Relevé de Restitution & Clôture* (Summary KPIs, double option for partial vs loss-settled return, print-ready Return Receipt).
- Multi-tenant scoping via `get_company_context()` and idempotent write protection (`with_idempotency`).

**Added.**
- `cortex_rental/page/cortex_checkin/` + `public/js/cortex_checkin/`: Desk page and Vue 3 application bundle.
- `services/checkin.py`: `search_active_transactions`, `lookup_scan_target`, and `process_checkin`.
- `api/v1/checkin.py`: endpoints `get_active_transactions`, `lookup_scan`, and `submit_checkin`.
- `cortex_check_in.json` & `cortex_check_in_item.json`: DocType fields for damage severity, damage type, estimated repair costs, and finalization modes.
- `cortex_rental_transaction.js`: "Effectuer le Check-in" action button on the Desk form when in `Checked Out` state.
- `cortex-rental.json`: Added "Check-in & Retours" shortcut and Operations card link.
- `test_checkin_api.py`: Unit tests for handlers, parsing, scan lookup, and mock checkin processing (85 tests passing total).
- `docs/frontend/checkin-scanner.md`: Complete frontend contract and architecture guide.

## Thirteenth wave — SaaS-Grade Hardening, Universal Deployment Script & Demo Fixtures

**Scope & Architecture Decisions.**
- **Backend Performance**: Batch SQL queries in `availability.py` (`GROUP BY item_code`) and `services/checkin.py` (`search_active_transactions`), eliminating N+1 loops.
- **Deep Multi-tenant Isolation**: Strict tenant boundary assertions on all serial numbers and transaction items in `process_checkin`.
- **Frontend SaaS Finish**: Reusable reactive `toastBus.js` / `CortexToast.vue` for non-blocking feedback and `cx-tabular-nums` typography.
- **Universal Deployment Script (`./bin/deploy.sh`)**: Multi-target deployment script supporting `tour` (native bench), `docker` (complete Compose stack), and `fixtures`.
- **Demo Fixtures Generator (`cortex_rental/fixtures/demo_data.py`)**: Idempotent generator creating a full cinema rental company ("Cortex Cinema Rentals"), customer ("Dune 3 Productions"), camera/optics catalog with real serial numbers, and live transactions across all lifecycle states.

**Added.**
- `bin/deploy.sh`: Turnkey deployment script with interactive prompts and `--with-fixtures` / `--skip-fixtures` flags.
- `cortex_rental/fixtures/demo_data.py`: Frappe bench fixture generator (`bench execute cortex_rental.fixtures.demo_data.provision_demo_data`).
- `test_demo_fixtures.py`: Unit tests for demo fixtures provisioning (87/87 tests passing).
- `public/js/cortex_shared/toastBus.js` & `CortexToast.vue`: Centralized reactive toast notifications system.
