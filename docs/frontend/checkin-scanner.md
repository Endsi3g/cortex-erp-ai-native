# Cortex Check-in Scanner & Réception Matérielle

`/app/cortex-checkin` — le troisième écran métier majeur de Cortex (après Disponibilité et Transaction Composer), dédié à la réception en entrepôt/comptoir, à la numérisation ultra-rapide des équipements retournés, au diagnostic technique d'avarie et à la clôture de contrat.

---

## 📁 Architecture des Fichiers

```text
apps/cortex_rental/cortex_rental/
├── api/v1/checkin.py                               # get_active_transactions, lookup_scan, submit_checkin
├── services/checkin.py                             # search_active_transactions, lookup_scan_target, complete_checkin, process_checkin
├── cortex_rental/page/cortex_checkin/
│   ├── cortex_checkin.json                         # Définition Desk Page
│   └── cortex_checkin.js                           # Chargeur dynamique du bundle Vue 3
├── cortex_rental/doctype/
│   ├── cortex_check_in/                            # DocType parent (CHK-YYYY-XXXXX)
│   ├── cortex_check_in_item/                       # DocType enfant (avaries, sévérité, coûts, disposition)
│   └── cortex_rental_transaction/
│       └── cortex_rental_transaction.js            # Bouton "Effectuer le Check-in" sur le formulaire Desk
└── public/js/cortex_checkin/
    ├── CortexCheckin.vue                           # Application Vue 3 continue en 3 étapes
    └── cortex_checkin.bundle.js                    # Entry point mount Frappe
```

---

## ⚡ Flux Continu en 3 Étapes (Sans modale bloquante)

1. **Étape 1 : Live Scan & Colisage** :
   - Champ de scan rapide avec focus automatique et rétroaction audio Web Audio API (synthétisée, sans asset externe).
   - Détection automatique et zéro latence des numéros de série scannés.
   - Support des équipements en vrac / non-sérialisés avec steppers incrémentaux `+1` / `-1` et bouton "Max".
   - Bascule instantanée vers le diagnostic en cas d'anomalie signalée.

2. **Étape 2 : Diagnostics & Revue des Écarts (Bris / Manquants)** :
   - Fiche d'inspection technique dédiée pour chaque article non conforme.
   - Qualification : Sévérité (Cosmetic / Functional / Blocking), Type d'avarie (Choc, Optique, Électronique, Liquide, etc.), Estimation des coûts de réparation et notes d'atelier.
   - Destination de stock (Disposition) : `Return to Stock` $\rightarrow$ `Active`, `Quarantine` $\rightarrow$ `Quarantine`, `Repair` $\rightarrow$ `Under Repair`, `Missing` $\rightarrow$ `Missing`, `Write-off` $\rightarrow$ `Decommissioned`.

3. **Étape 3 : Bilan, Relevé de Restitution & Clôture** :
   - Synthèse chiffrée (sains, atelier, manquants, coûts totaux).
   - Arbitrage de clôture : Retour complet / Solde de dossier avec perte $\rightarrow$ transition automatique vers `Returned`, ou Réception partielle $\rightarrow$ maintien en `Checked Out`.
   - Bon de retour imprimable instantanément (`@media print`) avec récapitulatif complet et signature opérateur.

---

## 🔒 Sécurité et Invariants Produit

- **Multi-Tenant (`PRD-NFR-001`)** : Strictement scopé par `Company` via `get_company_context()`.
- **Rôles Humains Obligatoires** : Restreint à `HUMAN_STAFF_ROLES` via `require_human_staff_role()`.
- **Idempotence (`PRD-ARCH-001`)** : Toute soumission utilise `with_idempotency()` avec clé unique client.
- **Audit Append-Only (`PRD-ARCH-003`)** : Émission systématique de l'événement d'audit `cortex.check_in.completed`.
