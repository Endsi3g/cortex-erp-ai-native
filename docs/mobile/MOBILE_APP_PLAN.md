# Plan de l'application mobile Cortex (propriétaire et gestionnaire)

> Statut : **plan seulement**, rien n'est construit. Décision du propriétaire du produit : on planifie maintenant, on
> construit après la stabilisation du bureau.

## 1. Objectif

Une application courte et rapide, connectée au même ERP (ERPNext/Frappe reste le système de référence), qui permet à un
**propriétaire** et à un **gestionnaire** de gérer leur journée depuis le téléphone :

1. Voir ce qui presse : départs du jour, retours attendus ou en retard, approbations, litiges.
2. **Décider** : approuver ou refuser un contrat (décision humaine seulement, comme au bureau).
3. Vérifier la disponibilité d'un équipement sur une période.
4. Ouvrir une location, appeler le client, voir l'historique.
5. Faire une sortie ou un retour avec le lecteur de codes (caméra).
6. Poser une question à l'assistant (il propose, l'humain décide).

Hors périmètre du mobile (reste au bureau) : comptabilité, catalogue en masse, règles tarifaires, import, administration.

## 2. Constats qui dictent le plan (captures et simulation de 91 jours)

| Constat | Conséquence pour le mobile |
| --- | --- |
| Le Desk sur 390 px fonctionne mais reste dense : listes à deux colonnes, formulaires longs (l'historique fait ~5 900 px de haut). | Écrans dédiés, une tâche par écran, pas de formulaire Desk complet. |
| `list_rentals` prend ~150 ms pour 20 lignes (requêtes en cascade par ligne) et ~290 ms filtrée. | Nouveaux points d'accès « résumé » : une seule requête SQL, champs minimaux. |
| La grille de disponibilité envoie tout le parc pour la période (30 j = ~22 ms) : acceptable. | Réutiliser `availability.get_matrix`, affichage 3 jours par défaut. |
| Le bureau a un filtre par société et des droits par rôle testés (approbations, permissions). | Le mobile n'invente aucun droit : il appelle les mêmes API protégées. |

## 3. Choix technique : PWA d'abord, Capacitor ensuite

**Recommandation : une seule base de code web (PWA), empaquetée avec Capacitor seulement quand il le faut.**

| Option | Poids | Installable | Caméra / push | Verdict |
| --- | --- | --- | --- | --- |
| **PWA** (manifest + service worker) | ~150–300 Ko de JS | Oui (Android, iOS 16.4+ « Ajouter à l'écran d'accueil ») | Caméra oui ; push web oui (iOS seulement une fois installée) | **Phase 1** |
| **Capacitor** qui charge la même PWA | + coque native ~5–10 Mo | App Store et Google Play | Plugins natifs stables (caméra, push, biométrie) | **Phase 3**, même code |
| React Native / Flutter | Nouvelle base de code | Oui | Oui | Écarté : duplique le travail et sépare du web |
| Cordova | Ancien | Oui | Oui | Écarté : Capacitor le remplace |

Pile de la PWA : **Vue 3 + Vite** (déjà connu de l'équipe, le retrait de Vite concernait le Desk, pas une application mobile
distincte), **vue-router**, **Pinia** minimal, **vite-plugin-pwa** (Workbox), CSS sobre reprenant `cortex-tokens.css`.
Objectif de poids : page de démarrage < 200 Ko compressés, premier affichage < 1,5 s sur 4G.

> Note de gouvernance : `AGENTS.md` dit que Vite et la SPA séparée sont retirés *du produit Desk*. Une application mobile
> distincte est une nouvelle surface. **Décision à confirmer par le fondateur produit** avant la phase 1 (voir § 9).

## 4. Connexion à l'ERP

- **Même origine** que le Desk (`/m`) ou sous-domaine `m.`, servie par l'application Frappe : pas de second serveur.
- **Authentification** : connexion par la session Frappe (cookie `HttpOnly`, `SameSite=Lax`) pour la PWA ; pour Capacitor,
  jeton d'API par appareil (clé/secret révocable, stocké dans le trousseau natif), jamais dans `localStorage`.
  Révocation depuis « Équipe et rôles ». Déverrouillage biométrique local optionnel.
- **Rôles** : le mobile affiche seulement ce que les rôles permettent (`api/v1/session.py` expose déjà les capacités).
  Propriétaire = toutes les actions ; gestionnaire = sans administration.
- **Cloisonnement** : toujours la société de l'utilisateur côté serveur (`get_company_context`). Le client n'envoie jamais
  un identifiant de société de confiance.
- **Approbations** : le mobile n'affiche « Approuver » que pour un humain avec le rôle requis ; la règle « l'auteur ne peut
  pas approuver sa propre demande » reste imposée par le serveur (vérifiée par le test de concurrence).

## 5. Écrans (maximum 6 onglets utiles)

1. **Aujourd'hui** : cartes Départs, Retours, En retard, Approbations (chiffre noir ; accent seulement pour l'important).
2. **Approbations** : liste → détail (client, période, total, prérequis) → Approuver / Refuser avec motif.
3. **Locations** : recherche, filtre par état, fiche courte (client, dates, lignes, total, état, historique).
4. **Disponibilité** : grille 3 jours, recherche, détail d'une cellule.
5. **Sortie / Retour** : scan caméra des numéros de série, confirmation, écart signalé.
6. **Assistant** : conversation courte avec cartes de proposition (jamais d'action sans approbation).

Règles de design : zones tactiles ≥ 44 px, texte ≥ 16 px, une action principale par écran, français du Québec, sombre
et clair, aucune donnée inventée (états vides et erreurs explicites).

## 6. API nécessaires (à créer ou alléger côté serveur)

| Besoin | Existant | À faire |
| --- | --- | --- |
| Tableau « Aujourd'hui » | cartes de nombres du Desk | `mobile.today` : 1 appel, comptes + 5 prochaines lignes |
| Liste des locations | `rentals.list_rentals` (lent, N+1) | `mobile.rentals` : 1 requête SQL, champs minimaux, pagination par curseur |
| Fiche location | `rentals.get_rental` | Version légère + `audit` séparé à la demande |
| Approbations | `approval_queue.*` | Réutiliser tel quel |
| Disponibilité | `availability.get_matrix` | Réutiliser ; ajouter agrégation par jour côté serveur |
| Sortie / retour | `operations.*`, `process_checkin` | Réutiliser ; lecture par caméra côté client |
| Assistant | `chat.*` | Réutiliser (voir décision moteur IA) |
| Notifications | — | File d'événements + Web Push (VAPID) puis FCM/APNs via Capacitor |

Toute écriture passe par ces API Frappe avec permissions ; clé d'idempotence (`Idempotency-Key`) sur les créations et
décisions, désormais sûre en parallèle (corrigée).

## 7. Hors ligne et réseau instable

- Lecture : cache du service worker (stale-while-revalidate) pour Aujourd'hui, Locations récentes et Disponibilité.
- Écriture : **pas de file d'écritures hors ligne au départ** (risque de décisions périmées). Les boutons sont désactivés
  hors ligne avec un message clair. À revoir en phase 4 pour les retours au comptoir (file signée et horodatée).
- Jamais de « succès » affiché sans réponse du serveur.

## 8. Phases et critères de sortie

| Phase | Contenu | Critère de sortie |
| --- | --- | --- |
| 0 — Fondations (1 sem.) | API `mobile.*`, jetons d'appareil, décision Vite/SPA | p95 < 120 ms sur 500 locations ; tests d'autorisation |
| 1 — PWA lecture + décision (2 sem.) | Aujourd'hui, Approbations, Locations, Disponibilité, installation | Lighthouse PWA ≥ 90, démarrage < 1,5 s en 4G, axe sans violation |
| 2 — Sortie/Retour + assistant (2 sem.) | Scan caméra, assistant, notifications push web | Parcours complet de sortie et retour sans clavier |
| 3 — Capacitor (1 sem.) | iOS et Android, push natif, biométrie, publication privée (TestFlight / piste interne) | Installation sur 3 appareils réels |
| 4 — Consolidation | Hors ligne ciblé, mesures d'usage, retours des premiers clients | Décision sur la publication publique |

## 9. Décisions attendues

1. Confirmer qu'une SPA mobile séparée (Vue + Vite) est acceptable malgré le retrait de Vite du Desk.
2. Notifications : quels événements comptent (approbation demandée, retour en retard, litige) ?
3. Comptes Apple Developer et Google Play à ouvrir au nom de l'entreprise (nécessaire avant la phase 3).
4. Vidéos d'accueil / démonstration : quels liens, pour les intégrer au guide de démarrage ?

## 10. Risques

- iOS : push web seulement après installation ; vérifier tôt sur appareil réel.
- Règles des boutiques d'applications (une coque qui ne fait qu'encapsuler un site peut être refusée) : prévoir les
  fonctions natives (caméra, biométrie, push) comme valeur propre.
- Dérive entre Desk et mobile : le mobile ne contient aucune règle métier, seulement des appels d'API.
