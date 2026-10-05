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
| Portée | **Accepter n'est pas réserver** : aucune écriture sur la location, aucun blocage de matériel, aucune facture. L'équipe réserve (disponibilité revérifiée sous verrou), puis le flux habituel (contrat approuvé par un humain) s'applique. |
| Audit et alertes | Événements `cortex.quote.shared` (équipe) et `cortex.quote.accepted|declined|changes_requested` (acteur « Customer »); notification à la personne qui a préparé le devis; activité en temps réel pour la société. |
| Abus | Réponse limitée par IP (120 par heure), consultation limitée (300 par heure), texte nettoyé et plafonné à 1 000 caractères, aucune information renvoyée pour un jeton inconnu. |
| Interface équipe | Boutons « Partager avec le client » et « Révoquer le lien » sur la location (devis), bandeau d'état (en attente, accepté, refusé, modification demandée, vu N fois). |

## Limites

- Le **courriel sortant** dépend du compte de messagerie du site : sur le banc de développement il n'est pas configuré, donc l'envoi échoue proprement (état « Failed ») et le lien reste utilisable à la main.
- Pas encore : paiement de l'acompte depuis le portail, signature électronique, confirmation par courriel au client après sa réponse, relance automatique avant expiration, portail avec compte (historique des devis du client).
