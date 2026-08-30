# Cortex Onyx — Configuration & Intégration des Agents

Espace de configuration des agents intelligents **Onyx** (Headless & Standard) pour Cortex ERP.

---

## 🔒 Invariants d'Intégration

- **Isolation physique** : Onyx est déployé dans son propre conteneur/cluster et ne communique avec Cortex qu'à travers la façade `apps/cortex-mcp` ou les contrats OpenAPI.
- **Zéro SQL direct** : Aucun accès SQL n'est consenti à Onyx.
- **Rôle de l'Agent** : L'agent prépare, extrait et propose ; seul l'opérateur humain valide et signe les actes ayant une conséquence contractuelle ou financière.

---

## 📂 Contenu

- `agents/` : Définitions déclaratives des agents et routage de modèles.
- `actions/` : Déclaration des outils MCP et endpoints accessibles.
- `prompts/` : Instructions système et consignes de conformité.
- `policies/` : Matrice des actions soumises à approbation humaine obligatoire.
