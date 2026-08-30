# Cortex FastMCP — Façade Privée pour Agents Onyx

Passerelle sécurisée en **Python FastMCP** connectant les agents IA de la plateforme Onyx aux APIs métier du Frappe Bench / ERPNext de Cortex.

---

## 🔒 Principes d'Isolation & Sécurité

1. **Zéro Accès SQL Direct** : Onyx et FastMCP ne requêtent jamais MariaDB ou Redis directement.
2. **Méthodes Métier Étroites** : FastMCP n'appelle que les endpoints whitelisted `/api/method/cortex_rental.api.v1.*`.
3. **Multi-Tenant Strict** : Chaque appel transmet l'entête `X-Company-ID` et vérifie le contexte de l'entreprise.
4. **Validation Typée Pydantic** : Tous les arguments et réponses sont validés selon des schémas stricts.

---

## 🛠️ Outils Exposés

| Outil FastMCP | Endpoint Frappe Appelé | Description |
|---|---|---|
| `search_rental_items` | `cortex_rental.api.v1.items.search_items` | Recherche catalogue matériel (caméras, optiques, lumières). |
| `search_customers` | `cortex_rental.api.v1.customers.search_customers` | Recherche de comptes de production et clients. |
| `create_customer_draft` | `cortex_rental.api.v1.customers.create_customer_draft` | Création de fiche prospect / brouillon sans ligne de crédit. |
| `check_inventory_availability` | `cortex_rental.api.v1.availability.check_availability` | Calcul de disponibilité temps réel avec verrous de conflits. |
| `create_quote_draft` | `cortex_rental.api.v1.quotes.create_quote_draft` | Génération de devis avec règle 7j = 3j (sans bloquer le stock). |
| `submit_approval_request` | `cortex_rental.api.v1.approvals.submit_approval` | Soumission d'actions engageantes à la file humaine. |
| `prepare_owner_statement` | `cortex_rental.api.v1.consignment.prepare_owner_statement` | Calcul du split propriétaire avec anonymisation du locataire. |

---

## 🚀 Démarrage Local

```bash
# Installation en mode éditable
pip install -e ".[dev]"

# Lancement du serveur FastMCP
python -m cortex_mcp.server

# Exécution des tests
pytest apps/cortex-mcp/tests/
```
