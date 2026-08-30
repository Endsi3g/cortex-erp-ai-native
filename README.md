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
  <img src="https://img.shields.io/badge/Audit-Append--Only%20Immuable-10B981?style=for-the-badge&logoColor=white" alt="Audit" />
</p>

---

<p align="center">
  <strong>Réconciliez le grand livre financier ERPNext, la disponibilité physique en temps réel et des agents IA autonomes sous supervision humaine stricte.</strong><br/>
  <em>Une plateforme unifiée conçue dès les fondations selon le paradigme Agent-Native First, garantissant zéro surréservation et zéro dérive transactionnelle.</em>
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

---

## Piliers Produit & Valeur Métier

### I. Catalogue & Disponibilité Atomique au Numéro de Série
- **Traçabilité unitaire exhaustive** : Chaque caméra, optique de cinéma, projecteur ou module est identifié par son numéro de série unique avec l'historique complet de ses cycles de location et de sa maintenance.
- **Verrous atomiques d'inventaire** : La soumission (`quote`) ne bloque pas l'inventaire. La réservation (`reservation`) pose un verrou atomique sur le stock disponible, et le contrat (`contract`) scelle définitivement l'engagement.
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
- **Contrôle qualité & Quarantaine (Check-in)** : Détection immédiate des articles manquants ou endommagés, bascule automatique en atelier/réparation et enregistrement des preuves probantes.

<br/>

---

## 🏛️ Composants Implémentés dans le Dépôt

### 1. Application Frappe Métier (`apps/cortex_rental`)
- **DocTypes Clés** :
  - `Cortex Rental Transaction` : Hub transactionnel de location gérant la machine à états (`Quote` $\rightarrow$ `Reservation` $\rightarrow$ `Contract` $\rightarrow$ `Checked Out` $\rightarrow$ `Returned` $\rightarrow$ `Closed`) et synchronisant les documents ERPNext natifs (`Quotation`, `Sales Order`, `Sales Invoice`).
  - `Cortex Rental Transaction Item` : Table enfant pour les lignes d'équipements de la transaction.
  - `Cortex Rental Item Profile` : Profil de location rattaché à l'Item ERPNext (taux journalier, valeur de remplacement, caution).
  - `Cortex Consignment Owner` & `Cortex Consignment Payout` : Moteur de calcul de reversement propriétaire avec **anonymisation stricte du locataire**.
  - `Cortex Approval Request` : File d'approbation humaine avec **barrière stricte interdisant l'auto-approbation par un agent**.
  - `Cortex Audit Event` : Journal d'audit append-only immuable (`before_save` et `on_trash` protégés).
  - `Cortex Inbound Request` : Ingestion structurée omnicanale.
- **Services Métier Python** :
  - `PricingService` : Application de la règle canonique **7 jours calendaires = 3 jours facturables**.
  - `AvailabilityService` : Calcul de disponibilité temporelle et détection de conflits.
  - `ConsignmentService` : Split propriétaire et purge des données de contact client.
  - `TransactionStateService` : Validation des transitions d'états et synchronisation ERPNext.
  - `AuditService` : Enregistrement immuable des événements d'audit.
- **Endpoints REST Métier Versionnés** (`/api/method/cortex_rental.api.v1.*`) :
  - `items.py`, `customers.py`, `availability.py`, `quotes.py`, `approvals.py`, `consignment.py`, `health.py`.

### 2. Façade Python FastMCP (`apps/cortex-mcp`)
- Serveur FastMCP exposant des outils typés Pydantic pour Onyx :
  - `search_rental_items`
  - `search_customers`
  - `create_customer_draft`
  - `check_inventory_availability`
  - `create_quote_draft`
  - `submit_approval_request`
  - `prepare_owner_statement`

### 3. Configuration Onyx & Prompts (`apps/cortex-onyx`)
- Définition déclarative des agents (`cortex-intake`, `cortex-availability`, `rental-copilot`), prompts système, schémas JSON et politiques d'escalade.

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
| **6** | **Multi-Tenant Absolu** | Cloisonnement strict des données par entreprise (`company` / `X-Company-ID`). Zéro fuite de données inter-compagnies. |
| **7** | **Autonomie Supervisée** | L'IA propose, optimise et rédige des brouillons ; le responsable humain engage et confirme. |

</div>

<br/>

---

## Architecture Technique

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cortex Operator Interface                         │
│  - Frappe Desk Standard : Navigation, Workspaces, Reports, Timeline & Audit │
│  - Frappe UI (Vue 3) : Matrice Disponibilité, Scanner Check-in, Hub Approvals│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Application Frappe `cortex_rental`                       │
│  - DocTypes : Rental Transaction, Consignment Owner, Payout, Approval, Audit│
│  - Services Métier Python : Availability, Pricing (7j=3j), Consignment, SoR │
│  - Endpoints REST Métier : `/api/method/cortex_rental.api.v1.*`              │
└──────────────────────▲───────────────────────────────┬──────────────────────┘
                       │                               │
    Frappe REST API    │ Authentification              │ Transactions SQL
    Token + X-Company  │ Scopes stricts                │ Multi-tenant strict
                       │                               │
┌──────────────────────┴───────────────┐       ┌───────▼──────────────────────┐
│     Façade MCP `apps/cortex-mcp`     │       │       MariaDB 10.11+         │
│  - FastMCP (Python / Pydantic)       │       │  - Source unique de vérité   │
│  - Validation Zod/Pydantic stricte   │       │  - Tables DocTypes & Audit   │
│  - Zéro accès SQL / Bench direct     │       │  - Isolation par `company`   │
└──────────────────────▲───────────────┘       └──────────────────────────────┘
                       │
┌──────────────────────┴───────────────┐
│          Plateforme Onyx             │
│  - Agents IA (Gemini / Claude)       │
│  - Ingestion emails & brouillons     │
└──────────────────────────────────────┘
```

<br/>

---

## 🚀 Démarrage Rapide & Commandes

```bash
# 1. Validation complète avant revue (Ruff, compilation syntaxique, pytest)
./bin/pre-claude-check.sh

# 2. Exécution des tests unitaires backend & FastMCP
PYTHONPATH=apps/cortex_rental:apps/cortex-mcp python3 -m unittest discover -s apps/cortex_rental/cortex_rental/tests/
PYTHONPATH=apps/cortex_rental:apps/cortex-mcp python3 -m unittest discover -s apps/cortex-mcp/tests/

# 3. Démarrage de l'environnement Docker local
make up

# 4. Logs des services
make logs-bench
make logs-mcp
```

<br/>

---

## Documentation Technique

<div align="center">

[Guide d'Implémentation Frappe / ERPNext](docs/07-frappe-erpnext-implementation-guide.md) &nbsp;|&nbsp;
[Intégration FastMCP et APIs Frappe](docs/02-onyx-mcp-frappe-integration.md) &nbsp;|&nbsp;
[ADR-003 : Replatforming Frappe / ERPNext](docs/adr/ADR-003-frappe-erpnext-migration.md) &nbsp;|&nbsp;
[Principes d'Architecture AI-Native](docs/01-ai-native-architecture.md) &nbsp;|&nbsp;
[Workflow de Développement Gemini -> Claude](docs/05-workflow-gemini-claude.md) &nbsp;|&nbsp;
[Politique de Sécurité](SECURITY.md) &nbsp;|&nbsp;
[Guide de Contribution](CONTRIBUTING.md)

</div>
