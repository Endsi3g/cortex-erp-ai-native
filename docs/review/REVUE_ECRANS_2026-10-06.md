# Revue des écrans — 2026-10-06

Document de travail pour la revue avec Kael. Les captures sont dans `captures/2026-10-06/revue/` (`bureau/` à 1440 px,
`mobile/` à 390 px), regroupées dans le PDF `REVUE_ECRANS_2026-10-06.pdf` (une page par écran, avec son adresse).
Données : simulation de 91 jours, compte propriétaire `sim.proprio@cortex.test` (aucune donnée réelle).

Les écrans de l'assistant de configuration (onboarding) sont déjà validés : `captures/2026-10-06/onbv2-*.png`.

## Ordre de revue proposé (du plus important au moins important)

1. Tableau de bord, Locations (liste, fiche, nouvelle), Disponibilité (grille, tiroir, nouveau devis)
2. Approbations (liste, fiche), Sorties et retours, Portail de devis du client
3. Clients (liste, fiche 360°), Catalogue (liste, fiche), Séries
4. Finance : factures, paiements, rapports, réglages financiers, consignation
5. Administration : Profil, Statistiques, Mes approbations, Activité, Sécurité, Notifications, Société et rôles, Équipe et règles, Règles tarifaires, Journal d'audit
6. Connexion, demande d'accès, mot de passe oublié, assistant IA, espaces IA/Catalogue/Opérations/Finance

## Défauts que j'ai remarqués en préparant les captures (à trancher ensemble)

| # | Écran | Constat | Piste |
| --- | --- | --- | --- |
| 1 | Tableau de bord, graphique « Locations par mois » | Les mois de l'axe sont en anglais (Oct, Dec, Apr, Aug) et les nombres en format anglais (`300.00`) | Traduire les libellés des graphiques natifs et formater en français |
| 2 | Fiche d'une location, section Activité | Le journal natif affiche des phrases techniques (« à [ "SIM-MON-TER-002" ] », « null », « a édité ceci ») | Masquer ou réécrire les phrases de champs techniques (séries, état) ; le dossier relié en haut dit déjà l'essentiel |
| 3 | Consignation › Versements (et propriétaires) | Le fil d'Ariane affiche l'identifiant brut « consignment payout »; le bouton dit « Ajouter Versement De Consignation » | Libellés français propres (fil d'Ariane et bouton) |
| 4 | Tableau de bord | Le guide vidéo « à venir » prend beaucoup de place avant les chiffres | Réduire (une ligne) tant qu'aucune vidéo n'existe |
| 5 | Réglages de l'IA (`cortex-ai-settings`) | Refusé au propriétaire d'une société (réservé aux System Manager) : voulu pour la clé d'API, mais le lien existe dans « Équipe et règles » | Retirer le lien pour les propriétaires, ou séparer « budget de la société » de « clé globale » |
| 6 | Consignation | Écrans vides dans la simulation (aucun propriétaire de matériel consigné simulé) | Prévoir des exemples dans le jeu de démonstration |

Rien d'autre n'a été trouvé de manière automatique : aucune erreur JavaScript, aucun débordement horizontal (bureau et
mobile) sur les écrans capturés. Cela ne remplace pas votre œil : dites-moi ce qui n'est pas « parfait ».

## Reprise

Chaque décision de la revue sera notée ici (écran, décision, date) puis reportée dans `docs/frontend/CORTEX_UI_HANDOFF_V2.md`.
