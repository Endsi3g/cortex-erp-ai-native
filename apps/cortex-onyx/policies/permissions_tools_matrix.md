# Matrice des Permissions & Outils MCP — Cortex ERP

Ce document formalise les frontières de sécurité, les droits d'accès aux outils MCP et les capacités de mutation pour chaque acteur (agents IA et opérateurs humains) au sein de l'écosystème **Cortex**.

---

## 🏛️ 1. Principes Fondamentaux de Sécurité

1. **Moindre Privilège (Least Privilege) :** Chaque agent IA ne dispose que du sous-ensemble strict d'outils MCP nécessaire à sa mission.
2. **Façade MCP Unique :** Aucun agent n'accède à la base de données PostgreSQL ou aux files Redis directement. Tout transit se fait par `apps/cortex-mcp`.
3. **Multi-Tenant Absolu :** Tout appel MCP est automatiquement injecté avec le `company_id` issu du jeton JWT authentifié. Les requêtes cross-tenant sont rejetées avec une erreur HTTP 403.
4. **Non-Répudiation & Audit :** Chaque appel à un outil MCP modifiant l'état (`create_quote_draft`, `create_customer_draft`, `submit_approval_request`) produit un événement immuable dans la table `audit_events`.

---

## 📊 2. Matrice d'Accès aux Outils MCP

| Outil MCP | Endpoint Laravel Associé | Agent Intake | Agent Availability | Agent Copilot | Opérateur Humain |
|---|---|:---:|:---:|:---:|:---:|
| `search_rental_items` | `GET /api/v1/rental-items` | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui |
| `search_customers` | `GET /api/v1/customers` | ✅ Oui | ❌ Non | ✅ Oui | ✅ Oui |
| `check_inventory_availability` | `POST /api/v1/inventory/check-availability` | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui |
| `get_rental_transaction` | `GET /api/v1/rental-transactions/{id}` | ❌ Non | ❌ Non | ✅ Oui | ✅ Oui |
| `create_customer_draft` | `POST /api/v1/customers/draft` | ✅ Oui | ❌ Non | ✅ Oui | ✅ Oui |
| `create_quote_draft` | `POST /api/v1/rental-transactions/quote-draft` | ✅ Oui | ❌ Non | ✅ Oui | ✅ Oui |
| `submit_approval_request` | `POST /api/v1/approvals` | ✅ Oui | ❌ Non | ✅ Oui | ✅ Oui |

---

## 🔒 3. Matrice des Mutations Métier & Règles de Validation

| Action Métier | Agent Intake | Agent Availability | Opérateur Humain | Mécanisme de Sécurité |
|---|:---:|:---:|:---:|---|
| **Création d'un brouillon de devis (`quote draft`)** | ✅ Autonome | ❌ Interdit | ✅ Autonome | Créé avec statut `draft`, ne réserve aucun inventaire. |
| **Création d'une fiche client provisoire (`customer draft`)** | ✅ Autonome | ❌ Interdit | ✅ Autonome | Créé avec statut `draft_unverified`, exige validation KYC. |
| **Confirmation de réservation (`reservation`)** | ❌ Interdit | ❌ Interdit | ✅ Exclusif | Bloque l'inventaire dans le calendrier. Exige approbation humaine. |
| **Signature de contrat (`contract`)** | ❌ Interdit | ❌ Interdit | ✅ Exclusif | Exige compte client validé, preuve d'assurance et modalité de paiement. |
| **Finalisation de facture (`invoiced`)** | ❌ Interdit | ❌ Interdit | ✅ Exclusif | Verrouillage comptable et fiscal irréversible. |
| **Sortie d'entrepôt (`checked_out`)** | ❌ Interdit | ❌ Interdit | ✅ Exclusif | Scan physique des numéros de série par l'équipe logistique. |
| **Application d'un rabais commercial > 15%** | ❌ Interdit (Escalade) | ❌ Interdit | ✅ Requiert `Manager` | Déclenche automatiquement une `approval_request`. |
| **Attribution de matériel en consignation** | ℹ️ Suggestion seule | ℹ️ Lecture seule | ✅ Validation humaine | Calcul automatique de la commission propriétaire par numéro de série. |

---

## 🛡️ 4. Garde-Fous Techniques Implémentés

- **Validation des Schemas Zod :** Tout payload entrant dans le serveur MCP est rigoureusement validé par Zod avant d'être transmis à Laravel.
- **Sanitisation des Textes Libres :** Les champs de texte provenant de l'extérieur (emails, notes) sont échappés pour neutraliser toute tentative de code injection ou de format string exploit.
- **Isolation des Sessions MCP :** Les connexions MCP sont stateless avec transmission systématique des en-têtes d'audit (`X-Cortex-Agent-Id`, `X-Cortex-Trace-Id`).
