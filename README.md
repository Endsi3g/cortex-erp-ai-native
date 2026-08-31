<div align="center">

# CORTEX ERP

### *L'ERP Cloud & AI-Native pour la Location Audiovisuelle, Cinéma & Événementiel*

<p align="center">
  <img src="https://img.shields.io/badge/Socle-Frappe%20%7C%20ERPNext%20v15-3B82F6?style=for-the-badge&logoColor=white" alt="Frappe/ERPNext" />
  <img src="https://img.shields.io/badge/Secteur-Audiovisuel%20%7C%20Cinéma-6366F1?style=for-the-badge&logoColor=white" alt="Secteur" />
  <img src="https://img.shields.io/badge/Agents-FastMCP%20%2B%20Onyx-8B5CF6?style=for-the-badge&logoColor=white" alt="FastMCP" />
  <img src="https://img.shields.io/badge/Release-v0.2.0-10B981?style=for-the-badge&logoColor=white" alt="v0.2.0" />
</p>

---

**Cortex** réconcilie la gestion d'un parc d'équipements au numéro de série, la comptabilité financière ERPNext en temps réel et des agents IA sous supervision humaine stricte.

</div>

<br/>

## Cortex en 30 secondes

1. **Zéro Surréservation** : Suivi unitaire de chaque caméra, optique et projecteur par numéro de série avec verrous de disponibilité temporels stricts.
2. **Ingestion IA Supervisée** : Conversion instantanée des listes de matériel et devis entrants en soumissions prêtes à valider par les opérateurs humains.
3. **Moteur de Consignation & P&L** : Calcul automatique des redevances propriétaires sans fuite de données et suivi financier en direct.

<br/>

---

## Les 4 Écrans Clés

| Écran | URL | Description |
|---|---|---|
| **Scanner Check-in** | `/app/cortex-checkin` | Réception ultra-rapide par scan (bip sonore Web Audio), diagnostic d'avarie (bris/manquants/quarantaine) et reçu imprimable. |
| **Disponibilité** | `/app/cortex-availability` | Grille calendaire interactive du parc d'équipements avec détection des conflits en temps réel. |
| **Composer de Devis** | `/app/cortex-transaction-composer` | Élaboration de devis express avec tarification dynamique (**règle 7 jours loués = 3 jours facturés**) et création de clients à la volée. |
| **P&L Financier** | `/app/cortex-accounting-pnl` | Compte de résultat hiérarchique en direct avec drill-down vers le Grand Livre ERPNext et export CSV instantané. |

<br/>

---

## Démarrage Rapide en 1 Commande

Le script universel `./bin/deploy.sh` prend en charge l'installation, les migrations MariaDB, la compilation des bundles Vue 3 et le chargement des données de test.

### Option A : Déploiement 1-Clic Complet (Installation de A à Z)
```bash
./bin/deploy.sh 1click --site cortex.local
```
*(Installe et configure automatiquement : Frappe Bench v15, ERPNext v15, cortex_rental, base MariaDB, bundles Vue 3, données de démo et lance la validation des tests).*

### Option B : Sur le Bench Frappe existant (la Tour)
```bash
./bin/deploy.sh tour --site cortex.local
```

### Option C : Via Docker Compose (Stack conteneurisée isolée)
```bash
./bin/deploy.sh docker
```

### Option D : Charger uniquement les données de démo
```bash
./bin/deploy.sh fixtures --site cortex.local
```
*(Crée automatiquement la société "Cortex Cinema Rentals", le client "Dune 3 Productions", le parc de caméras ARRI/Cooke et des locations prêtes pour la démo).*

<br/>

---

## Architecture Simplifiée

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Opérateurs & Desk UI                            │
│   Vue 3 SFC : Check-in Scanner • Disponibilité • P&L • Composer        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Appel API REST v1
┌───────────────────────────────────▼────────────────────────────────────┐
│              Cœur Frappe Framework & ERPNext v15 (Python)              │
│   • Gestion des contrats, stocks, prix (7j=3j), factures et P&L       │
│   • Audit log immuable & Sécurité multi-tenant stricte                │
└───────────────────▲───────────────────────────────┬────────────────────┘
                    │                               │
       Scopes & Rôles sécurisés           Transactions MariaDB 10.11+
                    │                               │
┌───────────────────┴───────────────┐       ┌───────▼────────────────────┐
│      Façade Python FastMCP        │       │   Base MariaDB (SoR)       │
│   (Connecteur d'outils pour IA)   │       │   Source unique de vérité  │
└───────────────────▲───────────────┘       └────────────────────────────┘
                    │
┌───────────────────┴───────────────┐
│     Copilote IA (Onyx / Gemini)   │
│   Extraction de devis & support   │
└───────────────────────────────────┘
```

<br/>

---

## Les 5 Règles d'Or de Cortex

1. **Source Unique de Vérité** : Humains et IA opèrent sur les mêmes données métier et les mêmes services Frappe.
2. **Sécurité dans le Code** : Les règles tarifaires, de caution et d'assurance sont écrites en Python, jamais confiées à un prompt.
3. **Multi-Tenant Absolu** : Isolation hermétique par société (`Company`). Zéro fuite de données inter-entreprises.
4. **Supervision Humaine** : L'IA prépare des brouillons ; seul un opérateur humain valide un contrat, une facture ou un crédit.
5. **Audit Immuable** : Toute action enregistre un événement d'audit inaltérable (acteur, horodatage, état avant/après).

<br/>

---

## Tests & Qualité de Code

```bash
# Lancer la suite complète de validation (87 tests unitaires + vérification DocTypes)
./bin/pre-claude-check.sh

# Lancer les tests pytest
PYTHONPATH=apps/cortex_rental:apps/cortex-mcp pytest apps/ -v
```

<br/>

---

## Documentation & Références

- [**Changelog & Historique des Vagues**](CHANGELOG.md)
- [**Guide de Transition & Commandes Tour (Handoff)**](HANDOFF.md)
- [**Release GitHub v0.2.0**](https://github.com/Endsi3g/cortex-erp-ai-native/releases/tag/v0.2.0)
- [**Documentation des Composants Frontend**](docs/design-system-component-contracts.md)
- [**Architecture du Scanner de Check-in**](docs/frontend/checkin-scanner.md)
- [**Politique de Sécurité**](SECURITY.md) & [**Guide de Contribution**](CONTRIBUTING.md)
