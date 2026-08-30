# Cortex Rental — Application Frappe Propriétaire

Application métier Frappe / ERPNext dédiée à la gestion de parcs de location audiovisuelle, cinéma et événementiel, avec moteur de calcul de disponibilité temps réel, tarification canonique (7j = 3j), consignation tiers et passerelle pour agents IA.

---

## 🏛️ Structure de l'Application

```text
apps/cortex_rental/
├── cortex_rental/
│   ├── api/v1/                            # Endpoints REST pour la passerelle FastMCP & Onyx
│   │   ├── items.py                       # Recherche catalogue articles & profils
│   │   ├── customers.py                   # Recherche clients & création de brouillons
│   │   ├── availability.py                # Calcul temps réel de disponibilité
│   │   ├── quotes.py                      # Ingestion & création de brouillons de devis
│   │   ├── approvals.py                   # Soumission de demandes d'approbation humaine
│   │   ├── consignment.py                 # Calcul & relevés de reversement propriétaires
│   │   └── health.py                      # Healthcheck du service
│   │
│   ├── cortex_rental/doctype/             # Définitions DocTypes Frappe (Python + JSON)
│   │   ├── cortex_rental_transaction/     # Hub transactionnel de location (Quote -> Closed)
│   │   ├── cortex_rental_transaction_item/# Lignes d'équipements de la transaction
│   │   ├── cortex_rental_item_profile/    # Caractéristiques location associées à Item ERPNext
│   │   ├── cortex_consignment_owner/      # Profil propriétaire consignateur tiers
│   │   ├── cortex_consignment_payout/     # Relevé de versement immuable (anonymisé)
│   │   ├── cortex_approval_request/       # File d'approbation humaine (anti auto-approbation agent)
│   │   ├── cortex_audit_event/            # Journal d'audit append-only immuable
│   │   ├── cortex_inbound_request/        # Ingestion structurée de courriels & PDF
│   │   ├── rental_item/                   # DocType matériel
│   │   └── rental_pricing_rule/           # Règles tarifaires par durée
│   │
│   ├── services/                          # Services métier Python purs
│   │   ├── pricing.py                     # Règle canonique 7j = 3j & calcul des lignes
│   │   ├── availability.py                # Moteur de disponibilité & verrous calendaires
│   │   ├── consignment.py                 # Split propriétaire avec purge de l'identité locataire
│   │   ├── transaction_state.py           # Machine à états & synchronisation ERPNext
│   │   └── audit.py                       # Enregistrement structuré des mutations d'audit
│   │
│   ├── permissions/                       # Scopes et hooks de sécurité multi-tenant
│   │   └── agent_scopes.py                # Validation des scopes agents & contexte X-Company-ID
│   │
│   ├── hooks.py                           # Hooks Frappe, doc_events et permission_queries
│   └── tests/                             # Suite de tests d'acceptation
│       └── test_demo_scenario.py          # Scénario démo 9 étapes & 4 barrières de sécurité
│
└── pyproject.toml                         # Configuration package & Pytest
```

---

## 🔒 Les 4 Barrières de Sécurité Implémentées

1. **Règle Tarifaire Canonique (7j = 3j)** : Implémentée dans `PricingService` et testée.
2. **Immutabilité de l'Audit (`Audit Event`)** : Les méthodes `before_save` et `on_trash` lèvent systématiquement une `PermissionError` sur toute tentative de modification ou suppression.
3. **Barrière d'Approbation Agent** : Les agents portant le rôle `Agent Service Account` ou exécutés sous `frappe.flags.in_agent_context = True` ont l'interdiction stricte d'approuver une `Approval Request`.
4. **Anonymisation Consignation** : `ConsignmentService` et `ConsignmentPayout` purgent et interdisent formellement toute clé d'identité du locataire (`customer_name`, `renter_email`, etc.) dans les snapshots de reversement.

---

## 🧪 Exécution des Tests

```bash
# Lancer les tests unitaires de cortex_rental
PYTHONPATH=apps/cortex_rental python3 -m unittest discover -s cortex_rental/tests/
```
