# Ce qui rend Cortex différent : paris de conception

Ce document décrit des **choix de conception** que le code applique aujourd'hui. Il ne contient aucune affirmation de marché que nous n'avons pas vérifiée (concurrents, parts, prix). À revoir avec les premiers clients.

## 1. Un seul geste, partout

Quand une demande de devis arrive, le matériel est retenu dans la disponibilité tout de suite, la grille le montre (hachuré), l'équipe est avertie, et le client répond sur un lien sans compte. L'acceptation avertit l'équipe et propose « Réserver » ; la réservation reste vérifiée par le serveur. Rien n'est ressaisi.

## 2. Honnête par construction

La retenue n'est pas une garantie, une absence de données est montrée comme telle, aucune cote de risque n'est inventée, l'IA ne confirme ni n'approuve rien : elle lit et propose, sous les droits de la personne.

## 3. Comptabilité fiable sans effort

Chaque facture, paiement et remboursement écrit une écriture à partie double, immuable et équilibrée, par société. La balance de vérification doit toujours s'équilibrer.

## 4. Décisions de parc, pas seulement du suivi

Le rapport *Utilisation du parc* dit quoi racheter et quoi retirer; la fiche client 360° dit qui doit de l'argent; les rappels disent ce qui exige une action aujourd'hui.

## 5. Pensé pour le Québec

Français (Québec) partout, TPS/TVQ, factures et dates québécoises.

## À valider

- La durée de retenue par défaut (72 h) et les rappels avec de vrais clients.
- Les frais de dommages (taxes) avec un comptable.
- Les envois réels (courriel, Stripe, modèle IA) : non testés avec de vrais comptes.
