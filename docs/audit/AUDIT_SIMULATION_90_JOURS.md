# Audit complet : simulation de 91 jours, tests de charge et revue des écrans

Date : 2026-09-30 · Environnement : site de développement `cortex.local` (Frappe/ERPNext 15) · Société simulée :
« Simulation Plateau Montréal » (location de matériel de tournage).

## 1. Résumé en dix lignes

1. La simulation a rejoué **91 jours d'activité réelle** (appels de services en tant que vrais employés : comptoir,
   gestionnaire, propriétaire) : 610 devis, 273 réservations, 231 contrats approuvés, 150 sorties, 128 retours, 66 clôtures,
   25 retours en retard, 2 litiges.
2. **Intégrité des données : correcte** (zéro total à 0 $, zéro surréservation, zéro sortie sans scan, zéro retour
   supérieur à la quantité sortie) une fois les défauts ci-dessous corrigés.
3. La simulation et les tests de charge ont révélé **9 défauts réels**, dont 3 graves (double réservation de la dernière
   unité, approbations impossibles pour un vrai gestionnaire, numéros de série attribués sans tenir compte des dates). **Tous corrigés et testés.**
4. Le **flux principal est sain pour la logistique** (devis → réservation → contrat → sortie → retour → clôture). Le trou
   principal, l'argent (aucune facture, taxe ni frais de retard), a été **comblé le 2026-09-30** (§ 7, P0). Reste : versements de consignation automatiques.
5. Performance : correcte pour un plateau (p50 < 150 ms sauf la liste des locations, ~150–300 ms à cause de requêtes en
   cascade). Le serveur de développement à un seul processus plafonne à ~10 requêtes/s ; il faut mesurer avec Gunicorn avant la production.
6. L'interface est propre et en français (aucun texte anglais détecté dans 46 captures, zéro débordement horizontal),
   mais **l'écran mobile reste le point faible** (formulaires longs, listes trop pauvres, espaces non pertinents dans la barre latérale).
7. Quelques permissions restent à trancher par le fondateur produit (voir § 8) : accès du propriétaire à la comptabilité ERPNext.

## 2. Méthode

| Outil | Ce qu'il fait | Emplacement |
| --- | --- | --- |
| `dev_tools/simulate_company.py` | Société, 4 comptes, 36 équipements (~120 séries), 120 clients, boucle jour par jour, appels réels aux services, vérifications d'intégrité SQL | `bench execute cortex_rental.dev_tools.simulate_company.run --kwargs '{"days": 90, "reset": 1}'` |
| `dev_tools/charge_et_concurrence.py` | HTTP réel : course sur la dernière unité, décisions d'approbation simultanées, idempotence, lectures chronométrées, charge mixte 16 utilisateurs | `bench execute cortex_rental.dev_tools.charge_et_concurrence.run` |
| Captures Playwright | 23 pages × bureau (1440 px) et mobile (390 px), détection de texte anglais et de débordement | `docs/review/captures/` |
| Parcours de fumée | 57 routes × 2 formats, erreurs JS, réponses HTTP ≥ 400 | voir § 6 |

Limites : une seule société simulée, graine fixe (2026), des clients aléatoires (pas de saisonnalité), aucun paiement réel.

## 3. Chiffres de la simulation (91 jours, ~2 s de calcul par journée simulée)

| Événement | Nombre |
| --- | --- |
| Devis créés | 610 (121 perdus, 337 annulés au total) |
| Réservations acceptées / refusées (disponibilité) | 273 / 216 |
| Contrats demandés / approuvés / refusés / bloqués par prérequis | 273 / 231 / 8 / 34 |
| Sorties / retours / clôtures | 150 / 128 / 66 |
| Retours en retard / litiges | 25 / 2 |
| Approbations (base) | 201 approuvées, 5 refusées |
| Événements d'audit | 1 696 (≈ 3,6 par location) |

Latences côté service (ms) :

| Action | p50 | p95 |
| --- | --- | --- |
| Créer un devis | 49 | 68 |
| Réserver | 113 | 184 |
| Demander un contrat | 24 | 32 |
| Approuver | 145 | 187 |
| Scanner une sortie | 24 | 55 |
| Enregistrer un retour | 101 | 146 |
| Clôturer | 47 | 62 |

Latences HTTP (500 locations, ~2 100 lignes) : liste de 20 locations 155 / 204 ms ; liste filtrée par état 281 / 366 ms ;
grille de disponibilité 7 j et 30 j ≈ 22 / 28 ms ; rapports 47 à 176 ms ; file d'approbations 18 ms ; démarrage de session 18 ms.
Charge mixte à 16 utilisateurs pendant 20 s : 10,5 requêtes/s, p50 338 ms, p95 3,2 s, zéro erreur (serveur de développement monoprocessus).

Croissance de la base : journal d'audit 1,7 Mo, lignes de location 1,6 Mo, historique des versions 0,9 Mo pour 91 jours. Même à 10×,
pas de souci de volume dans l'année.

## 4. Défauts réels trouvés, déjà corrigés

| # | Gravité | Défaut | Correction |
| --- | --- | --- | --- |
| 1 | **P0** | **Deux employés pouvaient réserver en même temps la dernière unité** (12 réservations sur 1 unité) : le verrou était libéré avant la validation en base. | Le verrou couvre maintenant la vérification + l'écriture + la validation ; nouvelle lecture cohérente après l'acquisition ; message clair si le verrou est occupé. Test : 12 tentatives → exactement 1 réussite. |
| 2 | **P0** | **Un gestionnaire réel ne pouvait pas approuver** (erreur de permission vide). | Droits DocType corrigés + garde serveur : la décision ne passe que par `approve()`/`reject()`, un humain, jamais l'auteur. |
| 3 | **P0** | **Numéros de série attribués sans regarder les dates** : refus en masse « il ne reste que 0 unité(s) » alors que le matériel était libre. | L'attribution ne compte que les réservations qui chevauchent la période. |
| 4 | P1 | Une clé d'idempotence rejouée en parallèle créait 6 locations. | Le doublon est annulé ; on renvoie la réponse du gagnant. Test : 6 envois → 1 location. |
| 5 | P1 | Le nom de la règle tarifaire (« 7 jours pour 3 ») entrait en collision dès la deuxième société. | Numérotation automatique `RULE-#####`. |
| 6 | P1 | Les gestionnaires ne pouvaient ni exécuter les rapports, ni exporter, ni imprimer un contrat. | Droits rapport / export / impression / courriel ajoutés par rôle. |
| 7 | P1 | Les rôles Cortex ne lisaient ni les clients, ni les numéros de série, ni les demandes entrantes ; le rapport « Activité des clients » exigeait un droit sur Client. | Droits ajoutés ; le rapport s'appuie sur la location. |
| 8 | P1 | Les rapports s'ouvraient vides : la société par défaut de la personne n'était pas la sienne. | Société par défaut = société de l'utilisateur (serveur et rapports). |
| 9 | P1 | **La grille de disponibilité ne s'affichait plus** (fonction de traduction absente dans la page) ; régression introduite par le passage au français. | Fonction déclarée ; page vérifiée sur bureau et mobile. |

Aussi corrigé : chiffres négatifs dans la grille (« -1 » quand deux locations se chevauchent dans la même journée),
formats québécois (1 782,50), valeurs d'état en anglais dans l'historique d'une location (« Contract à Checked Out »).

## 5. Ce qu'il faut **éviter** (constats de conception)

1. **Ne pas compter par jour calendaire** la disponibilité : un retour à 9 h et un départ à 14 h le même jour sont compatibles. La
   grille le simplifie (signalé « indicatif ») ; le serveur reste l'autorité. Ne jamais reprendre la grille comme règle.
2. **Ne pas laisser un « succès » sans transaction validée** : tout verrou doit englober l'écriture *et* la validation.
3. **Ne pas accorder de rôle ERPNext large au propriétaire** (Accounts Manager, Item Manager) : `Item` est global, donc partagé entre sociétés.
4. **Ne pas exposer dans la barre latérale des espaces que le rôle ne peut pas ouvrir** (le propriétaire voit Comptabilité, Vente, Stock, mais reçoit un refus).
5. **Ne pas multiplier les cartes colorées** : les chiffres restent noirs, l'accent sert seulement à ce qui exige une action.
6. **Ne pas supprimer d'événements d'audit** (le journal immuable a d'ailleurs bloqué le nettoyage des tests : comportement voulu).
7. **Ne pas mesurer sur le serveur de développement** pour décider de la capacité.

## 6. Ce qu'il faut **retirer** ou masquer

| Élément | Raison |
| --- | --- |
| Espaces sans usage pour un loueur (Qualité, Assistance/Support, Outils, Intégrations, Personnalisations avancées) pour les non-administrateurs | Bruit, refus de droits, peu d'utilité ; demande du propriétaire : **garder** Accueil, Cortex Rental, Comptabilité, Vente, Stock, Qualité, Assistance, Utilisateurs, Site Web et Paramètres (à confirmer, voir § 8) |
| Bouton flottant « Copilote » avec raccourci ⌘J sur téléphone | Recouvre les listes ; désormais rond et sans raccourci (fait) |
| Fil d'Ariane « Cortex IA > Location » | Mauvais espace (corrigé : Cortex Rental) |
| Champs techniques dans la fiche location (taux de taxe à 0, liens Devis/Commande ERPNext jamais remplis) | Induisent en erreur tant que la facturation n'existe pas |
| Chaînes anglaises stockées (« Camera Bodies », « Checked Out ») visibles dans les filtres de rapports | À traduire à l'affichage ou à renommer les valeurs |

## 7. Ce qu'il faut **améliorer**, par priorité

### P0 — le flux d'argent : **traité le 2026-09-30** (voir `docs/adr/ADR-005-facturation-cortex.md`)
Décisions du propriétaire du produit : vues financières maison, acompte **et** facture finale, frais de retard décidés par la société.

| Constat initial | Maintenant |
| --- | --- |
| Taxes forcées à 0 | TPS 5 % + TVQ 9,975 % calculées par le serveur, par société (`Cortex Finance Settings`), champs TPS/TVQ sur la location |
| Aucune facture | Facture d'acompte à la réservation (30 % par défaut, modifiable) et facture finale à la clôture, moins l'acompte déjà facturé |
| Case « paiement prêt » sans montant | L'acompte payé en totalité remplit le prérequis du contrat ; paiements complets avec solde et état |
| Aucun frais de retard | Règle par société (désactivée par défaut) : délai de grâce, % du tarif journalier, plafond |
| Cartes financières sur ERPNext (toujours à 0, inaccessibles au propriétaire) | Cartes, graphiques et rapports Cortex (*Créances par client*, *Taxes perçues*) filtrés par société |

Nouvelle simulation de 91 jours avec facturation (mêmes règles, frais de retard activés à 100 % du tarif, plafond 3 jours) :

| Mesure | Résultat |
| --- | --- |
| Factures émises | 218 acomptes + 73 finales |
| Paiements enregistrés | 252 (92 % des acomptes payés le jour même ; 80 % des finales payées, 10 % à moitié, 10 % impayées) |
| Facturé / encaissé / à recevoir | 269 780 $ / 206 120 $ / 63 661 $ |
| TPS / TVQ perçues | 11 732 $ / 23 406 $ |
| Frais de retard facturés | 16 703 $ (26 retours en retard) |
| Factures échues et non payées | 45 |
| Soldes incohérents, taxes incohérentes, totaux de location incohérents | **0 / 0 / 0** |
| Locations closes sans facture finale, réservées sans acompte, écart de rapprochement | **0 / 0 / 0** |
| Latences | réservation p50 51 ms / p95 219 ms (avec facture d'acompte) ; paiement p50 37 ms ; clôture p50 69 ms (avec facture finale) |

Tests de concurrence rejoués après l'ajout de la facturation : dernière unité 12 tentatives → 1 réussite ; approbation simultanée → 1 décision ; idempotence → 1 location.

Reste ouvert dans ce chantier : dépôt de garantie distinct de l'acompte, notes de crédit, relances automatiques, envoi de la facture par courriel, écritures dans le grand livre ERPNext (à décider, voir l'ADR).

### P1 — robustesse
6. **Liste des locations** : requêtes en cascade (client, profil, séries, retours pour chaque ligne). Créer un point d'accès « résumé » (1 requête) ; nécessaire aussi pour le mobile.
7. **Préconditions de contrat** : 34 contrats bloqués (compte client, assurance, paiement). Afficher *avant* la demande ce qui manque et permettre de le régler d'un écran.
8. **Refus de disponibilité (44 % des tentatives de réservation dans la simulation)** : proposer immédiatement des alternatives (le point d'accès `get_alternatives` existe) au lieu d'annuler le devis.
9. **Sorties ignorées / série introuvable (24)** : message guidant le comptoir (autre série disponible, série en réparation, autre société).
10. **Approbations** : notification (courriel/push) au gestionnaire dès la demande ; aujourd'hui il doit ouvrir la file.

### P2 — ergonomie et design
11. **Mobile** : liste des locations réduite à « client + état » ; ajouter dates et total. Formulaire : sections repliées par défaut, historique à part. (→ application mobile, `docs/mobile/MOBILE_APP_PLAN.md`.)
12. **Accueil Cortex Rental** : guide de démarrage encore ouvert alors que la société est active ; le masquer automatiquement quand les étapes sont faites. Ajouter les **vidéos** (champ prévu, liens à fournir).
13. **Graphique par mois** : étiquettes clairsemées ; étiquettes du graphique par jour qui se chevauchent à la fin.
14. **Colonnes de liste** tronquées (dates coupées) : élargir ou afficher la date seule.
15. **Accueil IA** : retiré de l'arrivée pour l'instant ; conserver la page (elle plaît), mais tant que le moteur IA n'est pas en place, afficher clairement « assistant indisponible » (déjà le cas).

### P3 — dette
16. `removeChild` intermittent lors de navigations rapides entre espaces avec graphiques (comportement de Frappe, observé sans nos scripts).
17. Société de démo : la création de société journalise « Parent Department: All Departments » (données d'installation Frappe manquantes).
18. Le champ `owner` du rapport « Relevé propriétaire » est obligatoire mais rien n'aide à choisir : proposer la liste des propriétaires de consignation.

## 8. Décisions à prendre (questions pour le fondateur produit)

1. **Comptabilité et stock ERPNext pour le propriétaire** : les donner (rôles `Accounts` / `Stock`) expose `Item` global et des rapports financiers dont le cloisonnement par société n'est pas garanti. Recommandation : **ne pas donner ces rôles**, construire nos propres vues financières (cartes, graphiques, rapports filtrés par société) et masquer les espaces ERPNext non autorisés. À confirmer.
2. **Taxes et facturation** : commencer par TPS/TVQ + facture à la clôture ? Acompte à la réservation ?
3. **Frais de retard** : règle exacte (tarif, délai de grâce, plafond).
4. **Vidéos du guide de démarrage** : liens à intégrer (aucune vidéo inventée n'a été ajoutée).

## 9. Ce que cet audit ne prouve pas

- Pas de test avec un vrai modèle IA (Onyx n'est pas configuré ; voir `docs/architecture/AI_ENGINE_DECISION.md`).
- Pas de courriels (aucun compte sortant configuré), pas de connexion Google/GitHub réelle (clés OAuth à fournir).
- Une seule société, pas de test d'isolation entre deux sociétés *actives en parallèle* en HTTP (les tests d'isolation existants ciblent le code et les requêtes de permission).
- Les mesures de charge viennent d'un serveur de développement monoprocessus.
