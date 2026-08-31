<div align="center">

# CORTEX ERP

### *Système d'Exploitation Cloud et AI-Native pour Maisons de Location Audiovisuelle, Cinéma et Événementiel*

<p align="center">
  <a href="#vue-densemble"><strong>Vue d'Ensemble</strong></a> &nbsp;|&nbsp;
  <a href="#piliers-produit--valeur-métier"><strong>Piliers Produit</strong></a> &nbsp;|&nbsp;
  <a href="#composants-implémentés"><strong>Composants Implémentés</strong></a> &nbsp;|&nbsp;
  <a href="#les-7-lois-de-gouvernance-invariables"><strong>Gouvernance</strong></a> &nbsp;|&nbsp;
  <a href="#architecture-technique"><strong>Architecture Technique</strong></a> &nbsp;|&nbsp;
  <a href="#démarrage-rapide--commandes"><strong>Démarrage Rapide</strong></a> &nbsp;|&nbsp;
  <a href="#documentation-technique"><strong>Documentation</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Socle-Frappe%20%7C%20ERPNext%20v15-3B82F6?style=for-the-badge&logoColor=white" alt="Frappe/ERPNext" />
  <img src="https://img.shields.io/badge/Secteur-Audiovisuel%20%7C%20Cinéma%20%7C%20Broadcast-6366F1?style=for-the-badge&logoColor=white" alt="Secteur" />
  <img src="https://img.shields.io/badge/Agents-Python%20FastMCP%20%2B%20Onyx-8B5CF6?style=for-the-badge&logoColor=white" alt="FastMCP" />
  <img src="https://img.shields.io/badge/Base%20SoR-MariaDB%2010.11%2B-003545?style=for-the-badge&logoColor=white" alt="MariaDB" />
  <img src="https://img.shields.io/badge/Audit-Append--Only%20(Applicatif)-10B981?style=for-the-badge&logoColor=white" alt="Audit" />
</p>

---

<p align="center">
  <strong>Réconciliez le grand livre financier ERPNext, la disponibilité physique en temps réel et des agents IA autonomes sous supervision humaine stricte.</strong><br/>
  <em>Une plateforme unifiée conçue dès les fondations selon le paradigme Agent-Native First, pour prévenir les surréservations et les dérives transactionnelles par des verrous d'inventaire, des validations métier, des transactions et un audit append-only — voir « Statut de maturité » ci-dessous pour ce qui est prouvé vs. implémenté.</em>
</p>

---

</div>

<br/>

## Vue d'Ensemble

Les gestionnaires de parcs audiovisuels, d'équipements de tournage, d'éclairage et de captation opèrent sous une pression logistique constante : **surréservations critiques**, **perte ou casse d'accessoires**, **calculs manuels et complexes de consignation pour tiers** et **saisie chronophage de devis entrants**.

**Cortex ERP** élimine ces frictions en combinant la puissance de **Frappe Framework & ERPNext (v15+)**, une application métier propriétaire `cortex_rental`, une interface opérateur Desk enrichie de composants **Frappe UI (Vue 3)**, et un copilote IA relié par une passerelle sécurisée **Python FastMCP**.

<br/>

```
+---------------------------------------------------------------------------------------------------------+
|                                          CORTEX WORKFLOW HUB                                            |
+-------------------+-----------------------------+----------------------------+--------------------------+
| 1. INGESTION IA   | 2. INVENTAIRE ATOMIQUE      | 3. MOTEUR DE CONSIGNATION  | 4. CONTRÔLE & GATEKEEPER |
| Courriels et PDF  | Suivi unitaire par numéro   | Partage de revenus exact   | File d'approbations      |
| convertis en      | de série, verrous           | et bordereaux de versement | Journal d'audit immuable |
| soumission draft  | calendaires sans collision  | automatiques par unité     | append-only systématique |
+-------------------+-----------------------------+----------------------------+--------------------------+
```

<br/>

## Statut de maturité

> Ce README décrit à la fois la vision produit, l'architecture cible et
> ce qui est réellement implémenté. Ce tableau distingue les trois —
> voir `CHANGELOG.md` pour le détail et `HANDOFF.md` pour la checklist
> de validation avant tout pilote.

| Domaine | Statut | Validation requise |
|---|---|---|
| App Frappe `cortex_rental` | Structure et code complets | Installation sur un bench Frappe réel (jamais fait dans ce dépôt — voir `HANDOFF.md` §2) |
| DocTypes (16) | Définis, schémas validés en CI | Migration réelle (`bench migrate`) et tests Frappe |
| Services métier Python | Implémentés, testés en mode mock (sans Frappe) | Tests d'intégration MariaDB réels |
| Disponibilité & verrouillage | Logique + verrou Redis/Valkey implémentés | Tests de concurrence multi-worker réels (jamais exécutés) |
| Consignation | Logique + anonymisation implémentées | Réconciliation avec un rapport client pilote réel |
| Audit (`Cortex Audit Event`) | Immutabilité applicative (`before_save`/`on_trash`) | Durcissement DB/permissions (voir note ci-dessous) + tests de contournement |
| MCP (`apps/cortex-mcp`) | Façade créée, scopes agent implémentés | Auth réelle + test d'intégration Onyx réel |
| Onyx | Décision (self-hosted) + widget d'intégration codés | Déploiement staging séparé, jamais fait |
| Docker / bench | Config corrigée (tag `frappe/bench:latest`) | `make up` n'a jamais démarré un bench complet jusqu'au bout dans ce dépôt |
| CI/CD | Pipeline Python réel, vert sur chaque commit | Scans de sécurité approfondis, pas seulement lint/tests |
| Production | Non démarrée | Sécurité, backups, restore, monitoring — tout reste à faire |

<br/>

---

## Piliers Produit & Valeur Métier

### I. Catalogue & Disponibilité Atomique au Numéro de Série
- **Traçabilité unitaire exhaustive** : Chaque caméra, optique de cinéma, projecteur ou module est identifié par son numéro de série unique avec l'historique complet de ses cycles de location et de sa maintenance.
- **Verrouillage d'inventaire multi-couche** : La soumission (`quote`) ne bloque jamais l'inventaire. La réservation (`reservation`) déclenche un verrou Redis/Valkey par équipement + une revalidation de disponibilité avant écriture, et le contrat (`contract`) scelle l'engagement. Cette coordination n'a pas encore été éprouvée sous charge concurrente réelle (pas de bench live) — voir « Statut de maturité ».
- **Accessoires dynamiques et kits** : Configuration standardisée des kits (corps caméra, platines, optiques, alimentations) avec contrôle des composants lors des mouvements.

### II. Moteur de Consignation & Partage de Revenus
- **Gestion des équipements de propriétaires tiers** : Affectation des unités consignées à des propriétaires (`Cortex Consignment Owner`) avec taux de redevance individualisé.
- **Calcul automatique des redevances** : Dès qu'une transaction portant sur un numéro de série consigné est clôturée et facturée, le moteur calcule la part du propriétaire.
- **Bordereaux de reversement (`Cortex Consignment Payout`)** : Génération de relevés détaillés et sécurisés, avec anonymisation stricte de l'identité du locataire.

### III. Copilote IA Supervisé & Ingestion Omnicanale
- **Extraction structurée des demandes entrantes** : Ingestion multimodale à haut débit (courriels, listes PDF de tournage, scans) transformée instantanément en objets métier typés (`Cortex Inbound Request`).
- **Autonomie strictement supervisée** : L'IA ne valide jamais un contrat, ne confirme aucun escompte, ne finalise aucune facture et n'émet aucun remboursement sans approbation humaine dans la file d'attente dédiée (`Cortex Approval Request`).

### IV. Comptoir de Départ, Retour & Traçabilité Fin-en-Fin
- **Comptoir de départ (Check-out)** : Validation instantanée par lecture de code-barres / QR code des numéros de série et accessoires.
- **Contrôle qualité & Quarantaine (Check-in)** : Détection imm### 1. Application Frappe Métier (`apps/cortex_rental`)
- **Écrans & Pages Frappe Desk (Vue 3 SFC / esbuild)** :
  - **Scanner Check-in & Retours (`/app/cortex-checkin`)** : Réception matérielle par scan direct (Web Audio cues), inspection d'avarie structurée (sévérité, type de dommage, frais estimés) et bilan de clôture avec reçu de restitution imprimable.
  - **Matrice de Disponibilité (`/app/cortex-availability`)** : Vue calendaire temps réel du parc d'équipements avec filtres et détection des conflits.
  - **Composer de Transaction (`/app/cortex-transaction-composer`)** : Élaboration de devis en temps réel, calcul de tarification dynamique (règle 7j=3j) et création de clients à la volée.
  - **P&L Financier (`/app/cortex-accounting-pnl`)** : Compte de résultat hiérarchique avec drill-down vers le Grand Livre ERPNext, export CSV direct et impression/PDF épurée.
- **DocTypes Clés** :
  - `Cortex Rental Transaction` : Hub transactionnel de location gérant la machine à états (`Quote` $\rightarrow$ `Reservation` $\rightarrow$ `Contract` $\rightarrow$ `Checked Out` $\rightarrow$ `Returned` $\rightarrow$ `Closed`), appliquée de façon inconditionnelle dans `validate()` (pas seulement via l'API). Synchronise `Quotation`/`Sales Order` ERPNext.
  - `Cortex Rental Transaction Item` : Table enfant pour les lignes d'équipements de la transaction.
  - `Cortex Rental Item Profile` : Profil de location rattaché à l'Item ERPNext (taux journalier, valeur de remplacement, caution).
  - `Consignment Owner` & `Consignment Payout` : Moteur de calcul de reversement propriétaire avec **anonymisation stricte du locataire** (allowlist + denylist unifiées, voir services).
  - `Approval Request` : File d'approbation humaine avec **barrière stricte interdisant l'auto-approbation par un agent**, branchée sur la vraie transition de transaction.
  - `Audit Event` : Journal d'audit append-only **au niveau applicatif** (`before_save`/`on_trash` immuables).
  - `Cortex Inbound Request`, `Cortex Evidence Reference`, `Cortex Extraction Run` : pipeline d'ingestion structurée, hash SHA-256 et validation JSON Schema réelle de l'extraction.
  - `Cortex Agent Run`, `Cortex Agent Tool Call` : journalisation structurée de chaque appel d'outil agent.
  - `Cortex Idempotency Record` : déduplication des écritures via `Idempotency-Key`.
  - `Cortex Check-In`, `Cortex Check-In Item` : retours partiels, déclarations de perte/bris, quarantaine et remise en stock.
- **Services Métier Python** (`services/`) :
  - `pricing.py` : Application de la règle canonique **7 jours calendaires = 3 jours facturables**.
  - `availability.py` : Disponibilité temps réel, distinction sérialisé/non-sérialisé, exclusion quarantaine/réparation.
  - `locking.py` : Verrou Redis/Valkey par (company, item_code) + revalidation de disponibilité avant écriture.
  - `consignment.py` : Split propriétaire, allowlist de snapshot + purge des données locataire.
  - `transaction_state.py` : Machine à états, appliquée de façon inconditionnelle (`validate()`).
  - `checkin.py` : Recherche optimisée par lots, résolution instantanée de codes/QR et traitement atomique audité des réceptions.
  - `audit.py`, `agent_telemetry.py`, `idempotency.py`, `evidence.py`, `extraction.py`.
- **Endpoints REST Métier Versionnés** (`/api/method/cortex_rental.api.v1.*`) :
  - `items.py`, `customers.py`, `availability.py`, `quotes.py`, `approvals.py`, `consignment.py`, `intake.py`, `checkin.py`, `accounting.py`, `health.py`.
- **Générateur de Fixtures de Démo** (`cortex_rental/fixtures/demo_data.py`) :
  - Provisioning idempotent de société cinéma (*Cortex Cinema Rentals*), clients, catalogue caméra/optiques avec numéros de série réels et transactions actives.

### 2. Façade Python FastMCP (`apps/cortex-mcp`)
- Serveur FastMCP exposant des outils typés Pydantic pour Onyx (aucun n'accepte de paramètre `company` — le tenant est fixé côté déploiement MCP, jamais choisi par l'agent) :
  - `search_rental_items`, `search_customers`, `create_customer_draft`
  - `check_inventory_availability`, `create_quote_draft`, `submit_approval_request`
  - `prepare_owner_statement`
  - `register_evidence`, `record_structured_extraction`

### 3. Onyx (self-hosted, service séparé)
- Onyx tourne en dehors de ce dépôt, self-hosted (backend + Postgres/OpenSearch/Redis/MinIO propres à Onyx) — voir `infra/onyx/README.md`.
- Configuration déclarative des agents Cortex (`apps/cortex-onyx`) : `cortex-intake`, `cortex-availability`, `rental-copilot`, prompts système, schémas JSON, politiques d'escalade.
- Intégration visuelle dans Cortex via le widget `<onyx-chat-widget>` embarqué dans `www/onyx-assistant.html`.

<br/>

---

## Les 7 Lois de Gouvernance Invariables

<div align="center">

| Numéro | Règle Fondamentale | Énoncé Canonique |
|:---:|---|---|
| **1** | **Ingestion Structurée** | Tout document entrant est converti en données typées. L'IA ne prend aucune décision sur du texte brut. |
| **2** | **Source Unique de Vérité** | Opérateurs et agents opèrent exclusivement dans le grand livre transactionnel MariaDB / Frappe. |
| **3** | **Sécurité dans le Code** | Les règles de prix (7j = 3j), de caution et de validation vivent dans le code système Python, jamais dans un prompt. |
| **4** | **Audit Append-Only** | Toute mutation produit un enregistrement inaltérable avec acteur, heure, avant/après et preuve. |
| **5** | **Supervision des Actes Sensibles** | Toute action engageante passe par la file d'approbation. Un agent ne s'auto-approuve jamais. |
| **6** | **Multi-Tenant Absolu** | Company résolue **côté serveur** depuis l'identité authentifiée (`User Permission` Frappe) ; `X-Company-ID` n'est qu'un indice, jamais une source de vérité. Zéro fuite de données inter-compagnies. |
| **7** | **Autonomie Supervisée** | L'IA propose, optimise et rédige des brouillons ; le responsable humain engage et confirme. |

</div>

<br/>

---

## Architecture Technique

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cortex Operator Interface                         │
│  - Frappe Desk Standard : Navigation, Workspaces, Reports, Timeline & Audit │
│  - Frappe UI (Vue 3) : Matrice Disponibilité, Scanner Check-in, P&L, Composer│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Application Frappe `cortex_rental`                       │
│  - DocTypes : Rental Transaction, Consignment Owner, Payout, Approval, Audit│
│  - Services Métier Python : Availability, Pricing (7j=3j), Consignment, SoR │
│  - Endpoints REST Métier : `/api/method/cortex_rental.api.v1.*`              │
└──────────────────────▲───────────────────────────────┬──────────────────────┘
                       │                               │
   Auth : session/API key/service   │            Transactions SQL
   Autz : rôles + scopes + policies │            Multi-tenant strict
   Tenant : résolue côté serveur ; X-Company-ID = │
   indice validé, jamais source de vérité         │
┌──────────────────────┴───────────────┐       ┌───────▼──────────────────────┐
│     Façade MCP `apps/cortex-mcp`     │       │       MariaDB 10.11+         │
│  - FastMCP (Python / Pydantic)       │       │  - Source unique de vérité   │
│  - Validation Zod/Pydantic stricte   │       │  - Tables DocTypes & Audit   │
│  - Zéro accès SQL / Bench direct     │       │  - Isolation par `company`   │
└──────────────────────▲───────────────┘       └──────────────────────────────┘
                       │
┌──────────────────────┴───────────────┐
│    Plateforme Onyx (self-hosted,     │
│    service séparé — infra/onyx/)     │
│  - Agents IA (Gemini par défaut,     │
│    Claude en escalade)               │
│  - Ingestion emails & brouillons     │
└──────────────────────────────────────┘
                       ▲
                       │ widget <onyx-chat-widget>
                       │ (client-side, Shadow DOM)
┌──────────────────────┴───────────────┐
│  www/onyx-assistant.html (Cortex)    │
│  Intégration visuelle uniquement —   │
│  aucun contournement des scopes API  │
└──────────────────────────────────────┘
```

<br/>

---

## 🚀 Démarrage Rapide & Déploiement

### 1. Script de Déploiement Universel (`./bin/deploy.sh`)

```bash
# Déploiement sur le Bench natif (la Tour) avec injection interactive des fixtures :
./bin/deploy.sh tour --site cortex.local

# Déploiement de la stack complète via Docker Compose :
./bin/deploy.sh docker

# Injection seule des données de démo (société, parc caméras, sorties actives) :
./bin/deploy.sh fixtures --site cortex.local
```

### 2. Validation & Tests de Développement

```bash
# Validation complète avant revue (Ruff, syntaxes Python, schémas DocTypes, 87 tests unitaires)
./bin/pre-claude-check.sh

# Exécution des tests Python (pytest ou unittest)
PYTHONPATH=apps/cortex_rental:apps/cortex-mcp pytest apps/ -v
```

> ⚠️ Aucune de ces commandes Docker n'a été exécutée avec succès jusqu'au
> bout dans le sandbox de développement de cette session (espace disque
> insuffisant pour un bench Frappe complet). Voir `HANDOFF.md` §2 pour
> l'état exact et la marche à suivre. Les tests `pytest` ci-dessus, eux,
> tournent réellement sans bench (mode dégradé sans Frappe) et passent.

<br/>

---

## Avant tout pilote — ce qui reste à prouver

Le code ci-dessus est écrit et testé en mode mock (sans Frappe). Rien
de ce qui suit n'a été prouvé contre une stack réelle dans ce dépôt :

- [ ] `make up` démarre un bench Frappe complet et un site Cortex est créé.
- [ ] Tous les DocTypes migrent sans erreur (`bench migrate`).
- [ ] Deux confirmations de réservation simultanées sur le même `Serial No` : une seule réussit.
- [ ] `quote` ne bloque jamais l'inventaire ; `reservation`/`contract`/`checked_out` bloquent réellement.
- [ ] `contract` échoue si compte client / assurance / paiement ne sont pas prêts.
- [ ] Un agent ne peut pas contourner les endpoints métier via l'API DocType générique.
- [ ] Un agent/utilisateur du tenant A ne voit jamais les données du tenant B (`test_multitenant_isolation.py` sur bench réel).
- [ ] `Audit Event` résiste à `frappe.db.set_value()`/`frappe.db.sql()` direct, pas seulement aux DocType hooks.
- [ ] Un `Consignment Payout` reste inchangé si le taux de consignation change après coup.
- [ ] Un `Owner Statement` ne contient jamais de PII locataire, y compris dans les exports/logs.
- [ ] Deux appels MCP avec la même `Idempotency-Key` ne créent pas deux brouillons.
- [ ] Le widget Onyx respecte session/tenant/CSP en conditions réelles.
- [ ] Backups MariaDB et fichiers restaurables.

Checklist complète et marche à suivre : `HANDOFF.md`. Priorité
recommandée pour la suite : isolation tenant, réservation concurrente,
calcul de consignation — les trois risques les plus coûteux à corriger
tardivement.

<br/>

---

## Documentation Technique

<div align="center">

[Changelog (correctifs sécurité/correction)](CHANGELOG.md) &nbsp;|&nbsp;
[Handoff opérationnel](HANDOFF.md) &nbsp;|&nbsp;
[Matrice de compatibilité](docs/compatibility-matrix.md) &nbsp;|&nbsp;
[Déploiement Onyx self-hosted](infra/onyx/README.md) &nbsp;|&nbsp;
[Guide d'Implémentation Frappe / ERPNext](docs/07-frappe-erpnext-implementation-guide.md) &nbsp;|&nbsp;
[Intégration FastMCP et APIs Frappe](docs/02-onyx-mcp-frappe-integration.md) &nbsp;|&nbsp;
[ADR-001 : Source de vérité](docs/adr/ADR-001-system-of-record.md) &nbsp;|&nbsp;
[ADR-002 : Disponibilité & concurrence](docs/adr/ADR-002-availability-and-concurrency.md) &nbsp;|&nbsp;
[ADR-003 : Replatforming Frappe / ERPNext](docs/adr/ADR-003-frappe-erpnext-migration.md) &nbsp;|&nbsp;
[ADR-004 : Consolidation catalogue](docs/adr/ADR-004-rental-item-catalog-consolidation.md) &nbsp;|&nbsp;
[Principes d'Architecture AI-Native](docs/01-ai-native-architecture.md) &nbsp;|&nbsp;
[Politique de Sécurité](SECURITY.md) &nbsp;|&nbsp;
[Guide de Contribution](CONTRIBUTING.md)

</div>
