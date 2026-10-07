# ADR-007 : portail de devis (lien partageable et lien envoyé par courriel)

Statut : accepté le 2026-10-05 (décision du propriétaire du produit : les deux, un lien partageable et un lien par courriel).

## Contexte

Le client doit pouvoir consulter son devis et répondre sans créer de compte, que l'équipe lui envoie le lien par courriel
ou le copie dans un message. La réponse ne doit jamais contourner la vérification de disponibilité ni l'approbation humaine.

## Décision

| Sujet | Choix |
| --- | --- |
| Lien | `/devis/<jeton>` : jeton aléatoire de 43 caractères; **seule l'empreinte SHA-256 est conservée** (`Cortex Quote Share.token_hash`). Le lien complet n'est montré qu'une fois, à la création. |
| Canaux | « Lien à copier » ou « Courriel » (modèle `cortex_quote_share`, répondre-à = la personne de l'équipe). Si le courriel ne part pas, le lien est quand même affiché pour être envoyé à la main. |
| Contenu | **Instantané** du devis à l'envoi (lignes, taxes, total, acompte à la réservation), calculé par le serveur; notes internes exclues. |
| Validité | 14 jours par défaut (1 à 60). Expiré, révoqué ou **devis modifié depuis l'envoi** : le client voit un message clair et ne peut plus répondre. |
| Réponses | Accepter (nom requis), refuser, demander une modification (message requis). Une seule réponse par lien, sous verrou de ligne. |
| Réservation après acceptation | Par défaut **à la main** : alerte en direct avec bouton « Réserver » (et « Ouvrir »), notification, bandeau et bouton « Réserver maintenant » sur la location. Réglage par société *Réserver automatiquement quand le client accepte* (désactivé par défaut) : le serveur tente la réservation **au nom de la personne qui a envoyé le devis** (ses droits, disponibilité revérifiée sous verrou, audit « Réservation automatique »). Si impossible, l'équipe est avertie avec la raison. |
| Acompte en ligne | Après l'acceptation, bouton « Payer l'acompte par carte » (Stripe Checkout, **clés Stripe de la société**, chiffrées) et instructions de paiement manuel configurables. La facture d'acompte est créée au besoin (idempotent). Un paiement n'est enregistré que sur **webhook signé** (secret de la société, fenêtre de 5 min), une seule fois par session; le retour du navigateur ne prouve rien. Écritures comptables et audit habituels. |
| Portée | **Accepter n'est pas réserver** : aucune écriture sur la location, aucun blocage de matériel, aucune facture. L'équipe réserve (disponibilité revérifiée sous verrou), puis le flux habituel (contrat approuvé par un humain) s'applique. |
| Audit et alertes | Événements `cortex.quote.shared` (équipe) et `cortex.quote.accepted|declined|changes_requested` (acteur « Customer »); notification à la personne qui a préparé le devis; activité en temps réel pour la société. |
| Abus | Réponse limitée par IP (120 par heure), consultation limitée (300 par heure), texte nettoyé et plafonné à 1 000 caractères, aucune information renvoyée pour un jeton inconnu. |
| Interface équipe | Boutons « Partager avec le client » et « Révoquer le lien » sur la location (devis), bandeau d'état (en attente, accepté, refusé, modification demandée, vu N fois). |

## Limites

- Le **courriel sortant** dépend du compte de messagerie du site : sur le banc de développement il n'est pas configuré, donc l'envoi échoue proprement (état « Failed ») et le lien reste utilisable à la main.
- Le paiement Stripe est **testé avec une session simulée et un webhook signé**, pas avec un vrai compte Stripe (aucune clé disponible) : à recetter en mode test Stripe avant la production. Frais : voir `docs/architecture/COUTS_API.md`. Pas de Stripe Connect : chaque société utilise son propre compte Stripe.
- Pas encore : signature électronique, confirmation par courriel au client après sa réponse, relance automatique avant expiration, portail avec compte (historique des devis du client).
