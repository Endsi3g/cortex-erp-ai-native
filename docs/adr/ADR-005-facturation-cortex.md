# ADR-005 : facturation Cortex (taxes, acompte, facture finale, paiements)

Statut : accepté le 2026-09-30 (décisions du propriétaire du produit) · Remplace : le champ `tax_rate` forcé à 0 et les
cartes financières qui lisaient `Sales Invoice` / `Payment Entry`.

## Contexte

L'audit de 91 jours a montré que la logistique tient, mais qu'aucune facture, aucune taxe, aucun frais de retard n'était
produit. Le propriétaire d'une société n'a pas (et ne doit pas avoir) les rôles comptables d'ERPNext : `Item` est global, donc
partagé entre sociétés, et le cloisonnement des rapports financiers standards par société n'est pas garanti.
Décisions : **construire nos propres vues financières**; **facturer les deux moments** (acompte à la réservation et facture à
la clôture); **les frais de retard sont décidés par chaque société**.

## Décision

| Sujet | Choix |
| --- | --- |
| Où vivent les factures | `Cortex Rental Invoice` (+ lignes) et `Cortex Rental Payment`, DocTypes Frappe filtrés par société (`permission_query_conditions`). Le champ `erpnext_sales_invoice` n'est pas créé : la comptabilisation dans le grand livre ERPNext est **reportée** (voir Conséquences). |
| Réglages | `Cortex Finance Settings`, un enregistrement par société (créé au provisionnement et par patch) : TPS 5 %, TVQ 9,975 %, numéros de taxes, acompte (30 % par défaut), échéance, règle de retard **désactivée par défaut**. |
| Taxes | Calculées par le serveur sur le sous-total, TVQ non composée, arrondies au cent, par facture. `tax_rate` de la location devient un champ calculé. |
| Acompte | Facture `Deposit` émise à la réservation (une seule, idempotente). Payée en totalité, elle remplit le prérequis « paiement ou dépôt prêt » du contrat. Annulée automatiquement si la location est annulée et qu'aucun paiement n'a été reçu ; un acompte encaissé reste pour décision de la finance. |
| Facture finale | Émise à la clôture : lignes louées, frais de retard éventuels, **moins l'acompte facturé**; taxes sur le net. |
| Frais de retard | Jours entamés après le délai de grâce × tarif journalier × pourcentage, plafond optionnel, à partir de la dernière heure de retour enregistrée. |
| Paiements | Créés seulement (jamais modifiés ni supprimés); remboursement = paiement de type `Refund`. Montant validé sous verrou de ligne (pas de trop-perçu en parallèle), idempotence par `Idempotency-Key`, audit. |
| Vues | Cartes (facturé, encaissé, solde, en retard, TPS, TVQ), graphiques mensuels, rapports *Créances par client* et *Taxes perçues*, espace Finance sans aucun raccourci ERPNext comptable. |

## Conséquences

- Positif : chaque société voit uniquement ses chiffres; aucun rôle ERPNext large à accorder; les taux sont configurables.
- À décider : **journalisation comptable** (écritures dans ERPNext) quand un comptable externe ou un export l'exigera. Le
  modèle est prêt (factures et paiements complets); il manque le plan comptable par société et les comptes de revenus.
- Hors périmètre ici : dépôt de garantie distinct de l'acompte, notes de crédit, relances automatiques, envoi de la facture par courriel.
- Les factures émises sont des instantanés : changer les taux ne les modifie pas.
