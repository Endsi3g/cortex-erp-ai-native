# ADR-008 : un devis retient le matériel dans la disponibilité

Statut : accepté le 2026-10-06 (décision du propriétaire du produit : « un devis qui n'apparaît pas dans la disponibilité serait un tueur »).

## Contexte

Jusqu'ici un devis ne bloquait rien : deux clients pouvaient recevoir un devis pour la même dernière unité, et la grille de
disponibilité ne montrait pas les devis en cours.

## Décision

| Sujet | Choix |
| --- | --- |
| Retenue | À la création d'un devis (par l'écran, l'API, une demande entrante ou l'assistant), le contrôleur de la location prend une **retenue** : `hold_status` = Active, `hold_until` = maintenant + durée de la société (72 h par défaut). |
| Sûreté | La retenue est prise **sous le verrou de réservation de chaque article**, avec la disponibilité réelle (réservations **et** autres retenues) : deux devis ne retiennent jamais la même dernière unité. |
| Matériel insuffisant | Le devis est créé quand même (on peut négocier) mais **sans retenue**, avec la quantité libre indiquée (`hold_status` = Insufficient). Rien n'est promis en silence. |
| Expiration | Calculée à la lecture (`hold_until > NOW()`), donc **sans tâche planifiée pour la justesse**. Un rappel horaire prévient 24 h avant. |
| Partage du devis | Envoyer le devis au client prolonge la retenue jusqu'à l'expiration du lien (revérifiée, jamais raccourcie). |
| Réservation | Inchangée et seule garante : la retenue du devis lui-même ne compte jamais contre lui (`exclude_transaction`); les retenues des **autres** devis comptent. |
| Interface | La grille montre les unités retenues (hachurées, distinctes des réservées), une chronologie « Sur la période » liste dossiers et retenues; le formulaire du devis affiche la retenue avec « Libérer » et « Reprendre la retenue ». |
| Réglages | `Cortex Finance Settings` : *Un devis retient le matériel* (activé par défaut) et *Durée de la retenue*. |

## Conséquences

- Un devis concurrent pour le même matériel est averti tout de suite (« 1 libre sur 5 demandé(s) »), et la grille montre pourquoi.
- Une personne autorisée peut libérer une retenue (bouton) pour redonner le matériel aux autres.
- Limites : la retenue n'est pas une garantie (seule la réservation l'est); la grille reste indicative; pas encore de file d'attente automatique quand une retenue expire.
