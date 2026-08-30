# ADR-003 : Replatforming vers Frappe Framework & ERPNext sur MariaDB

- **Statut** : Accepté
- **Date** : 2026-08-29
- **Auteurs** : Équipe d'Architecture Cortex
- **PRD IDs** : `PRD-ARCH-001`, `PRD-NFR-001`, `PRD-AI-001`, `PRD-CON-001`, `PRD-TRX-001`, `PRD-RET-001`
- **Cadre de Référence** : *ERPNext Desk UI/UX, Frappe UI & Python FastMCP Integration*

---

## 1. Contexte & Problématique

Cortex avait initialement envisagé une base Laravel / Aureus ERP. Cependant, l'analyse comparative opérationnelle pour le secteur de la location audiovisuelle a démontré la supériorité d'un socle **Frappe Framework / ERPNext** :

1. **Maturité ERP complète** : ERPNext inclut nativement une chaîne comptable éprouvée (plans comptables, TVA, facturation, écritures de journal), un CRM, la gestion des stocks avec numéros de série et lots, et un système de permissions granulaire par rôle et document.
2. **UI/UX Desk standard + Frappe UI** : Interface Desk puissante avec recherche universelle Awesomebar (`Cmd+K`), timeline d'audit native par formulaire, et extensibilité via Frappe UI (Vue 3 / Tailwind) pour les vues haute intensité (scanner, planning).
3. **Maintien strict des 7 règles AI-natives** : Ingestion validée, source de vérité unique, audit append-only immuable, barrière d'approbation humaine, multi-tenant strict et passerelle d'agents isolée.

---

## 2. Décision d'Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Frappe Desk UI / UX & Frappe UI (Vue 3)              │
│   - Workspaces configurables (Comptoir, Entrepôt, Direction, IA Hub)   │
│   - Awesomebar Universelle (Cmd+K) & Navigation DocTypes               │
│   - Timeline d'activités, historique des révisions & preuves           │
│   - Pages Vue 3 dédiées : Matrice Disponibilité & Scanner Check-in     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Application Frappe `cortex_rental`                  │
│   - Hub Transactionnel : Cortex Rental Transaction                     │
│   - DocTypes Métier : Rental Item Profile, Consignment Owner & Payout  │
│   - Sécurité & Audit : Approval Request, Audit Event (Append-only)     │
│   - Moteur Tarifaire (7j = 3j), Disponibilité & Synchronisation ERPNext│
└───────────────────▲────────────────────────────────┬───────────────────┘
                    │                                │
    Appels REST /   │ Authentification               │ Transactions
    Token API       │ Par Compagnie                  │ SQL Strictes
                    │ (X-Company-ID)                 │
┌───────────────────┴────────────────┐   ┌───────────▼───────────────────┐
│       Onyx & Façade FastMCP        │   │    MariaDB 10.11+ (Source SoR)│
│  - Python FastMCP (apps/cortex-mcp)│   │   - Schéma relationnel Frappe │
│  - Ingestion emails & brouillons   │   │   - Table `tabAudit Event`    │
│  - Validation Zod/Pydantic stricte │   │   - Isolation par `company`   │
│  - Zéro accès direct BD / Bench    │   │   - Redis / Valkey pour queues│
└────────────────────────────────────┘   └───────────────────────────────┘
```

### 2.1 Moteur de Base de Données MariaDB 10.11+
- Frappe Framework et ERPNext sont optimisés pour **MariaDB 10.11+** avec le moteur InnoDB et la collation utf8mb4.
- Garantit l'ACIDité complète, la compatibilité 100% avec les patches et migrations officielles de Frappe, et le verrouillage transactionnel au niveau ligne (`SELECT ... FOR UPDATE`) pour le calcul de disponibilité.

### 2.2 Application Modulaire `cortex_rental` (Zéro Fork ERPNext)
- Aucune modification du code source d'ERPNext. Toutes les spécificités de location vivent dans l'application `apps/cortex_rental`.
- Utilisation des `hooks.py`, `doc_events`, `override_doctype_class` et `custom_fields` pour enrichir les DocTypes natifs.

### 2.3 Correspondance et Hub des DocTypes

| Concept Cortex | Implémentation Frappe / ERPNext | Rôle & Interaction |
|---|---|---|
| **Transaction de Location** | DocType `Cortex Rental Transaction` | Hub maître (`Quote` $\rightarrow$ `Reservation` $\rightarrow$ `Contract` $\rightarrow$ `Checked Out` $\rightarrow$ `Returned` $\rightarrow$ `Closed`) synchronisant les documents ERPNext (`Quotation`, `Sales Order`, `Sales Invoice`). |
| **Profil Matériel Location** | DocType `Cortex Rental Item Profile` | Lié à l'Item ERPNext (`daily_rate`, `replacement_value`, `required_accessories`, `prep_hours`). |
| **Numéro de Série & Suivi** | Extension `Serial No` ERPNext | Enrichi avec `custom_rental_status`, `custom_consignment_owner`, `custom_consignment_rate`. |
| **Propriétaire Consignateur** | DocType `Cortex Consignment Owner` | Profil tiers propriétaire et coordonnées de facturation. |
| **Relevé Propriétaire Tiers** | DocType `Cortex Consignment Payout` | Snapshot financier immuable sans identité du locataire. |
| **File d'Approbation IA** | DocType `Cortex Approval Request` | Validation humaine obligatoire interdisant toute auto-approbation par un compte agent. |
| **Journal d'Audit Immuable** | DocType `Cortex Audit Event` | Journal append-only avec interdiction stricte de modification ou suppression (`before_save`, `on_trash`). |
| **Demande Entrante Structurée** | DocType `Cortex Inbound Request` | Réception et extraction IA de courriels et demandes de soumission. |

### 2.4 Multi-Tenancy par Compagnie
- Les données sont isolées au niveau logique par le champ `company` présent sur chaque DocType.
- Des `Permission Query Hooks` et `User Permissions` Frappe empêchent toute fuite de données entre locataires.

### 2.5 Façade MCP Python & Onyx
- Le serveur MCP est implémenté en Python FastMCP (`apps/cortex-mcp`).
- Il communique via les méthodes API whitelisted de Frappe (`/api/method/cortex_rental.api.v1.*`) avec des jetons d'API (`api_key` / `api_secret`) et l'entête `X-Company-ID`.
- L'agent Onyx ne possède aucun accès direct à MariaDB, Redis ou la CLI Frappe Bench.

---

## 3. Conséquences

### Avantages :
1. **Écosystème Standard et Éprouvé** : MariaDB 10.11+ et Frappe v15 forment un socle robuste et maintenable.
2. **Backend 100% Python** : Unification des compétences entre l'application Frappe `cortex_rental`, la façade FastMCP et les scripts d'évaluation d'agents.
3. **Expérience Opérateur Optimale** : Richesse de Desk pour le backoffice combinée à la fluidité de Frappe UI (Vue 3) pour le comptoir de location.
