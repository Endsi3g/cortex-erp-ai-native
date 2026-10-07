<div align="center">

# CORTEX ERP

### *L'ERP de location d'équipement audiovisuel, cinéma et événementiel — natif ERPNext, assisté par IA, supervisé par des humains*

<p align="center">
  <img src="https://img.shields.io/badge/Socle-Frappe%20%7C%20ERPNext%20v15-3B82F6?style=for-the-badge&logoColor=white" alt="Frappe/ERPNext" />
  <img src="https://img.shields.io/badge/Interface-100%25%20fran%C3%A7ais%20(Qu%C3%A9bec)-6366F1?style=for-the-badge&logoColor=white" alt="Français" />
  <img src="https://img.shields.io/badge/IA-Cortex%20Rapide%20%7C%20%C3%89quilibr%C3%A9%20%7C%20Avanc%C3%A9-8B5CF6?style=for-the-badge&logoColor=white" alt="Modèles Cortex" />
  <img src="https://img.shields.io/badge/Release-v0.11.0-10B981?style=for-the-badge&logoColor=white" alt="v0.11.0" />
</p>

</div>

**Cortex** réunit la gestion d'un parc d'équipements, la facturation québécoise (TPS/TVQ), la comptabilité à partie double et un assistant IA qui **prépare** le travail sans jamais décider à la place des gens. ERPNext/Frappe reste le système de référence : Cortex est construit avec les éléments natifs d'ERPNext (espaces, cartes, graphiques, rapports, listes, formulaires, calendrier), sans application séparée.

## Cortex en 30 secondes

1. **Zéro surréservation** : disponibilité calculée par le serveur, verrou de réservation par article, devis qui retiennent le matériel (retenue qui expire seule).
2. **Du devis à la facture** : devis → réservation → contrat approuvé par un humain → sortie → retour (par numéro de série) → facture avec acompte → paiement, avec écritures comptables équilibrées et un journal d'audit qui ne se modifie jamais.
3. **Assistant IA honnête** : il lit vos données sous vos droits, propose, et ouvre des questionnaires guidés. Il n'approuve, ne confirme et n'écrit rien tout seul. Sans modèle configuré, il le dit (mode « Démonstration »).
4. **Plusieurs sociétés, zéro fuite** : isolation stricte par société, vérifiée par des tests de charge, de concurrence et d'abus.

## Ce que vous trouvez dans l'application

| Zone | Contenu |
|---|---|
| **Accueil — Assistant IA** (`/app/cortex-home`) | Conversation, trois questionnaires guidés (nouvelle location, disponibilité, approbations), historique, choix du modèle Cortex, fil d'Ariane. |
| **Opérations** | Tableau de bord, locations (liste, kanban, calendrier, Gantt), grille de disponibilité interactive, approbations, sorties et retours par scan. |
| **Parc** | Catalogue et tarifs (règles de prix, ex. « une semaine = 3 jours »), numéros de série et leur état, consignation et versements aux propriétaires. |
| **Clients et finance** | Clients (fiche 360°), factures, paiements, taxes, écritures comptables, créances, utilisation du parc. |
| **Portail de devis** (`/devis/<jeton>`) | Le client accepte, refuse ou demande une modification sans compte ; l'acompte se paie en ligne (Stripe) ou par instructions manuelles. |
| **Administration** | Mon compte (profil, sécurité, appareils, notifications), équipe et rôles, règles tarifaires, réglages de l'IA et budget, journal d'audit, configuration guidée à l'arrivée. |

## L'assistant IA

- **Modèles Cortex** : *Rapide* (Gemini), *Équilibré* (Claude Sonnet 5.5), *Avancé* (Claude Opus 5.5) et *Luna* (OpenAI GPT-6 Luna, désactivé par défaut). Chaque niveau a son identifiant et ses prix par million de jetons dans les réglages (*Cortex AI Settings*) ; il n'est offert que si la clé de son fournisseur existe. Le budget mensuel de la société compte le coût réel du niveau utilisé. Les clés restent côté serveur.
- **Mode démonstration** : sans clé, l'assistant répond à quatre demandes (disponibilité, retards de retour, approbations en attente, catalogue) avec de vraies données, et l'affiche clairement.
- **Garde-fous** : outils en lecture sous les droits de la personne, aucune écriture ni approbation par l'IA, plafond de budget avec bascule vers un modèle économique, historique masquable (les messages restent au journal).
- Détails et limites : [`docs/frontend/CORTEX_UI_HANDOFF_V2.md`](docs/frontend/CORTEX_UI_HANDOFF_V2.md).

## Démarrage rapide

Le script `bin/deploy.sh` (Linux/macOS) et `bin/deploy.ps1` (Windows) installent ou mettent à jour l'application, appliquent les migrations, construisent les bundles et chargent les données de démonstration.

```bash
# Installation complète (Frappe Bench v15, ERPNext v15, cortex_rental, données de démo)
./bin/deploy.sh 1click --site cortex.local

# Sur un bench existant
./bin/deploy.sh tour --site cortex.local

# Pile Docker isolée
./bin/deploy.sh docker

# Données de démonstration seulement
./bin/deploy.sh fixtures --site cortex.local
```

Après une mise à jour du code : `bench build --app cortex_rental`, `bench --site <site> migrate`, `bench --site <site> clear-cache`, puis redémarrage.

### Données de démonstration (développement seulement)

```bash
bench --site cortex.local execute cortex_rental.dev_tools.simulate_company.run      # société simulée sur ~91 jours
bench --site cortex.local execute cortex_rental.dev_tools.jeu_de_demo.run           # devis, réservations et 3 approbations en attente
bench --site cortex.local execute cortex_rental.dev_tools.jeu_de_demo.reinitialiser # repartir de zéro
```

Ces outils refusent de s'exécuter hors d'un site de développement. **Jamais en production.**

### Mise en production

Guide d'exploitation, sauvegardes et retour arrière : [`docs/ops/DEPLOIEMENT.md`](docs/ops/DEPLOIEMENT.md). Avant toute mise en service : `bench --site <site> execute cortex_rental.ops.predeploy.run` (il échoue tant qu'un point bloquant subsiste).

## Architecture simplifiée

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Desk ERPNext : espaces, listes, formulaires, rapports, pages Cortex │
│  Accueil IA et grille de disponibilité en Vue 3 (bundler de Frappe)  │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ API Frappe whitelistées (droits vérifiés)
┌─────────────────────────────────▼────────────────────────────────────┐
│  cortex_rental (Frappe/ERPNext v15, Python)                          │
│  Machine à états des locations • tarification • disponibilité        │
│  facturation TPS/TVQ • écritures • audit immuable • multi-société    │
│  Passerelle IA : outils sous les droits de la personne, budget       │
└──────────────┬───────────────────────────────────────┬───────────────┘
               │                                       │
     Fournisseurs de modèles                  MariaDB (source de vérité)
     (Gemini, Anthropic) — clés côté serveur  + Redis (cache, files)
```

## Les règles d'or

1. **Source unique de vérité** : humains et IA passent par les mêmes services Frappe.
2. **Les règles sont dans le code**, pas dans un prompt (prix, disponibilité, approbations, droits).
3. **Isolation par société** : aucune lecture ni écriture entre sociétés.
4. **Supervision humaine** : l'IA propose ; une personne autorisée approuve un contrat ou un paiement, jamais sa propre demande (auto-approbation désactivée par défaut).
5. **Audit immuable** : chaque action laisse une trace (qui, quand, avant/après).
6. **Honnêteté de l'interface** : pas de confiance, de disponibilité, de réponse de modèle ou de réussite inventées ; ce qui est une démo ou indisponible est dit.

## Tests et qualité

```bash
cd apps/cortex_rental
ruff check . && ruff format --check .
python3 -m pytest cortex_rental/tests -q -p no:cacheprovider   # certains tests exigent un bench et sont ignorés sans lui
```

Le contrat des API est vérifié statiquement (méthodes explicites, écritures en POST, appels sans compte limités à une liste fermée). Des outils de vérification sur bench sont dans `apps/cortex_rental/cortex_rental/dev_tools/` (fuzz des endpoints, charge et concurrence, isolation entre sociétés, longueurs, approbations, onboarding). Rapports : [`docs/audit/`](docs/audit/).

## Documentation

- [Contrat UI et vérité d'implémentation (document canonique)](docs/frontend/CORTEX_UI_HANDOFF_V2.md)
- [Index de la documentation](docs/README.md) · [Journal des changements](CHANGELOG.md) · [Passation](HANDOFF.md)
- [Déploiement en production](docs/ops/DEPLOIEMENT.md) · [Courriel (Amazon SES)](docs/ops/COURRIEL_SES.md) · [Coûts d'API](docs/architecture/COUTS_API.md)
- [Décisions d'architecture (ADR)](docs/adr/) · [Revue des écrans](docs/review/REVUE_ECRANS_2026-10-06.md)
- [Releases](https://github.com/Endsi3g/cortex-erp-ai-native/releases) · [Sécurité](SECURITY.md) · [Contribuer](CONTRIBUTING.md)
