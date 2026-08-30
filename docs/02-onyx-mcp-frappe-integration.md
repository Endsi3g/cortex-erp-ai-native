# Intégration Onyx, Façade FastMCP et APIs Métier Frappe / ERPNext

Ce document détaille l'architecture d'intégration entre la plateforme d'agents **Onyx**, la façade privée **FastMCP (Python)** et le socle ERP **Frappe Framework / ERPNext v15+**.

---

## 1. Topologie de Connexion et Sécurité

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          Plateforme Onyx Agents                        │
│   - Agent Ingestion (cortex-intake : Gemini 3.7 Flash)                 │
│   - Agent Disponibilité & Concurrence                                  │
│   - Agent Superviseur & Escalade (Claude 3.7 Sonnet)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Protocole MCP (Streamable HTTP / SSE)
                                    │ JSON-RPC typé & Validations Pydantic
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Façade FastMCP (`apps/cortex-mcp`)                    │
│   - Outils agent-safe : search_items, check_availability, quote_draft  │
│   - Injection du contexte entreprise (X-Company-ID)                   │
│   - Zéro accès SQL direct / Zéro commande bench directe                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Frappe REST API (Token auth)
                                    │ Endpoints whitelisted /api/method/...
┌───────────────────────────────────▼────────────────────────────────────┐
│                 Application Frappe `cortex_rental`                     │
│   - Scopes de sécurité : require_agent_scope(...)                      │
│   - Services Métier : Pricing, Availability, Consignment, State Machine│
│   - Journal d'Audit Immuable (Audit Event) & File Approbations         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Transactions InnoDB
┌───────────────────────────────────▼────────────────────────────────────┐
│                       MariaDB 10.11+ (SoR Unique)                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Outils FastMCP et Correspondances API Frappe

| Outil FastMCP | Endpoint Frappe Cible | Règle de Sécurité / Rôle |
|---|---|---|
| `search_rental_items` | `cortex_rental.api.v1.items.search_items` | Lecture catalogue uniquement (`agent:items:read`). |
| `search_customers` | `cortex_rental.api.v1.customers.search_customers` | Recherche comptes sans données sensibles de paiement. |
| `create_customer_draft` | `cortex_rental.api.v1.customers.create_customer_draft` | Création d'un prospect sans validation de crédit. |
| `check_inventory_availability` | `cortex_rental.api.v1.availability.check_availability` | Calcul temps réel sans verrou physique (`agent:availability:read`). |
| `create_quote_draft` | `cortex_rental.api.v1.quotes.create_quote_draft` | Création d'une soumission appliquant la règle 7j = 3j. |
| `submit_approval_request` | `cortex_rental.api.v1.approvals.submit_approval` | Transmission obligatoire d'une action sensible à l'opérateur. |
| `prepare_owner_statement` | `cortex_rental.api.v1.consignment.prepare_owner_statement` | Calcul du reversement avec anonymisation stricte du locataire. |

---

## 3. Barrière d'Approbation & Anti-Auto-Approbation

Tout agent exécuté par FastMCP porte le rôle `Agent Service Account` et active le flag `frappe.flags.in_agent_context = True`.

Toute tentative d'appel à la méthode `.approve()` sur une `Approval Request` ou de confirmation directe d'un contrat lèvera immédiatement une `frappe.PermissionError`.
