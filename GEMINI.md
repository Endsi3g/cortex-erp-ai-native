# Instructions Générales du Projet — Cortex ERP AI-Native

Bienvenue sur le dépôt de **Cortex**, l'ERP cloud AI-native pour maisons de location audiovisuelle et événementielle, basé sur **Frappe Framework** et **ERPNext**.

---

## 🏛️ Architecture & Découpage du Répertoire

- `apps/cortex_rental` : Application Frappe propriétaire contenant le domaine métier location, les DocTypes spécialisés, services Python, validations, workflows et interfaces Frappe UI (Vue 3).
- `apps/cortex-mcp` : Façade MCP privée en Python FastMCP (Pydantic, HTTPX) connectée aux APIs métier Frappe pour Onyx.
- `apps/cortex-onyx` : Configuration des agents Onyx, prompts système, RAG et politiques d'action.
- **ERPNext / Frappe Framework** : Socle ERP open-source standard (Desk UI, comptabilité, CRM, gestion de stock, facturation).
- **MariaDB 10.11+** : Source unique de vérité transactionnelle du Frappe Bench.
- **Redis / Valkey** : Gestion des queues d'arrière-plan Frappe, cache et verrous de disponibilité atomiques.
- **S3 / MinIO / R2** : Stockage immuable des photos, documents PDF et preuves d'audit.
- **API Frappe Métier Versionnée** : Seule et unique voie d'écriture (`/api/method/cortex_rental.api.v1.*`) pour les agents, l'UI et les intégrations.

---

## 🔒 7 Règles Produit Non Négociables

1. **Ingestion structurée :** Extraction $\rightarrow$ JSON typé $\rightarrow$ validation $\rightarrow$ objets métier. Aucun agent ne décide depuis une capture d’écran ou du texte non validé.
2. **Source unique de vérité :** Humains et agents utilisent les mêmes données métier, les mêmes Services Python et les mêmes Policies Frappe.
3. **Sécurité dans le code :** Les règles de location, prix (7j = 3j), assurance, contrat, consignation et permissions sont dans le code/policy système Python, jamais uniquement dans un prompt.
4. **Audit append-only systématique :** Toute mutation produit un événement `Audit Event` contenant : acteur (`actor_type`, `actor_id`), action, entité, état avant/après, preuve, politique, request_id et date. Les événements d'audit sont strictement immuables et protégés contre toute modification ou suppression (`before_save`, `on_trash`).
5. **Supervision des actes sensibles :** Toute action agent sensible passe par `Approval Request`. Un agent ne peut jamais approuver sa propre demande (`frappe.flags.in_agent_context = True` lève une `PermissionError`).
6. **Multi-tenant absolu :** Aucun accès cross-company n’est acceptable. Toute requête, job, export, recherche RAG ou appel MCP doit être scopé par `company` (`X-Company-ID`).
7. **Autonomie supervisée :** Les agents peuvent lire, extraire et créer des brouillons (`Quote`, `Customer Draft`) ; ils ne confirment pas les contrats, ne finalisent pas les factures, n’émettent pas de crédit et n’envoient pas de document client sans approbation humaine.

---

## 📖 Vocabulaire Métier Canonique

- `quote` : soumission / devis ; ne bloque pas l’inventaire.
- `reservation` : réservation bloquant l’inventaire, non confirmée.
- `contract` : contrat confirmé et prêt à sortir ; nécessite compte, assurance et caution validés.
- `checked_out` : équipement sorti hors-location (bon de livraison / scan).
- `invoiced` : facture de location émise et comptabilisée dans ERPNext.
- `serial number` : unité suivie individuellement avec état de disponibilité et propriétaire.
- `consignment` : équipement d’un tiers ; % reversé au propriétaire par numéro de série sans révélation de l'identité locataire.

---

## 🏷️ PRD IDs Obligatoires

- `PRD-ARCH` : Architecture API-first, services communs, journal d'audit immuable.
- `PRD-CON` : Consignation et commissions propriétaires sans fuite de données.
- `PRD-INV` : Profils de location, accessoires, verrous et calcul de disponibilité temporelle.
- `PRD-TRX` : Transactions de location maîtresse et synchronisation comptable ERPNext.
- `PRD-CLI` : Gestion des clients, vérification solvabilité/assurance et onboarding.
- `PRD-RET` : Retours d'équipements, check-in scanner et gestion des manquants/bris.
- `PRD-AI` : Agents Onyx et passerelle FastMCP Python.
- `PRD-MIG` : Migration et import de données legacy.
- `PRD-NFR` : Exigences non fonctionnelles, sécurité multi-tenant, performance.

---

## 🔄 Workflow Obligatoire : Gemini → Claude

Tout travail suit le cycle en 10 étapes :
1. Créer une issue avec un ID PRD.
2. Créer une branche : `feat/PRD-XXX-description`.
3. Donner à Gemini un ticket atomique de génération/implémentation.
4. Exécuter `./bin/pre-claude-check.sh` localement (Ruff, Mypy/Pyright, Pytest).
5. Committer les changements Gemini séparément.
6. Donner à Claude le prompt de revue avec le diff Git réel.
7. Appliquer les corrections arbitrées par l'opérateur humain.
8. Relancer `./bin/pre-claude-check.sh`.
9. Tester le flux UI dans Cortex (Desk / Frappe UI).
10. Ouvrir une PR avec le template standardisé.
