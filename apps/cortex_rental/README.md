# Cortex Rental — application Frappe / ERPNext

Application métier de **Cortex** (Frappe Framework et ERPNext v15) : gestion d'un parc de location d'équipement, disponibilité calculée par le serveur, tarification (« 7 jours loués = 3 jours facturés » et règles par société), facturation TPS/TVQ, écritures comptables, consignation, portail de devis, assistant IA sous supervision humaine. Version : voir `cortex_rental/__init__.py`.

> Le contrat de l'interface et la vérité d'implémentation sont dans [`docs/frontend/CORTEX_UI_HANDOFF_V2.md`](../../docs/frontend/CORTEX_UI_HANDOFF_V2.md). ERPNext reste le système de référence : tout passe par des API Frappe qui vérifient les droits.

## Structure

```text
apps/cortex_rental/cortex_rental/
├── api/v1/            API Frappe whitelistées (méthodes explicites ; écritures en POST ; droits vérifiés)
│                      rentals, availability, approval_queue, billing, catalog, customers, chat, account,
│                      administration, onboarding, quote_share (portail), checkin/checkout, presence…
├── cortex_rental/doctype/   DocTypes (location, lignes, profil d'article, facture, paiement, écriture,
│                            demande d'approbation, évènement d'audit, session et message de chat, réglages IA…)
├── services/          Logique métier en Python pur ou sous Frappe
│   ├── pricing.py, availability.py, availability_summary.py, holds.py, locking.py
│   ├── transaction_state.py, approval_policy.py, billing.py, ledger.py, payments.py, consignment.py
│   ├── audit.py, defense.py (validation, frein de débit, en-têtes), health.py
│   └── ai/            passerelle IA : gateway, providers (Gemini, Anthropic), settings (niveaux Cortex),
│                      budget, tools (lecture et propositions), demo (mode démonstration honnête)
├── public/js/         Accueil IA et copilote (Vue 3, bundler de Frappe), grille de disponibilité,
│                      navigation, fil d'Ariane ; public/css/ : navigation, accueil, compte, mouvement
├── dev_tools/         Outils de vérification et de démonstration (développement seulement)
├── ops/predeploy.py   Contrôle pré-déploiement (échoue tant qu'un point bloquant subsiste)
├── patches/, fixtures/, translations/ (fr.csv), tests/
└── hooks.py
```

## Garde-fous implémentés

1. **Isolation par société** : toutes les lectures et écritures sont limitées à la société de la personne.
2. **Machine à états des locations** appliquée côté serveur, même pour une écriture directe.
3. **Approbation humaine** : un agent ne peut jamais approuver ; une personne ne décide pas de sa propre demande (auto-approbation du seul approbateur désactivée par défaut, activable avec avertissement et audit).
4. **Audit immuable** : les évènements ne se modifient ni ne se suppriment ; les messages de chat non plus.
5. **Assistant IA** : outils en lecture sous les droits de la personne, jamais d'écriture ni d'approbation ; clés de modèle chiffrées côté serveur ; budget mensuel par société comptant le coût réel du niveau utilisé.
6. **Défense** : validation des entrées (`safe_input`), frein de débit par utilisateur, vrais octets des images, 429 au verrouillage, test de contrat statique sur tous les endpoints.

## Modèles de l'assistant

Réglages *Cortex AI Settings* : clé Gemini (niveau *Rapide*), clé Anthropic (niveaux *Équilibré* et *Avancé*), identifiants et prix par million de jetons de chaque niveau, budget mensuel, plafond et modèle économique. Sans clé, l'assistant fonctionne en mode démonstration. Moteur choisi par `cortex_chat_provider` (`gateway` par défaut, `onyx`, `mock`).

## Mettre à jour et vérifier

```bash
bench build --app cortex_rental
bench --site <site> migrate
bench --site <site> clear-cache

cd apps/cortex_rental
ruff check . && ruff format --check .
python3 -m pytest cortex_rental/tests -q -p no:cacheprovider
```

Outils sur bench (développement) : `cortex_rental.dev_tools.simulate_company.run`, `jeu_de_demo.run`, `fuzz_endpoints`, `charge_et_concurrence`, `isolation_http`, `verifier_approbations`. Ne jamais les lancer sur un site de production.
