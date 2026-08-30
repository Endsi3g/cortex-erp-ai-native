# Registre des Décisions d'Architecture (Architecture Decision Records & Open Questions)

- **Branche** : `feat/PRD-ARCH-001-monorepo`
- **PRD IDs** : `PRD-ARCH-001`, `PRD-NFR-001`, `PRD-AI-001`, `PRD-INV-001`
- **Dernière mise à jour** : 2026-08-29

---

## 🏛️ Décisions Validées & Arbitrages

| ID | Domaine | Décision | Statut |
|---|---|---|:---:|
| **OQ-01** | Transport Serveur MCP | **Streamable HTTP** privé pour `cortex-mcp` en production ; `stdio` réservé au dev local. | 🟢 Acceptée |
| **OQ-02** | Stockage des Preuves | **Stratégie hybride** : Upload direct S3/MinIO signé (quarantine) pour gros fichiers ; Laravel proxy pour emails et PDF légers. | 🟢 Acceptée |
| **OQ-03** | Cache, Queues & Verrous | **Valkey 8** pour dev, staging et production. | 🟢 Acceptée |
| **OQ-04** | Cycle de Vie & Tokens Agents | **Service Accounts** par agent/environnement avec tokens courts renouvelables ; aucun token statique par tenant. | 🟢 Acceptée |

---

### OQ-01 : Transport du Serveur MCP (`apps/cortex-mcp`)
- **Décision** : Utiliser **Streamable HTTP** comme transport de production entre Onyx et `cortex-mcp`.
- **Réseau** : Endpoint privé sur `https://mcp.cortex.internal/mcp`, accessible uniquement à Onyx et aux outils d’exploitation autorisés (non exposé publiquement).
- **Authentification** : Identité de workload + token de service court ou mTLS.
- **Streaming** : SSE peut être utilisé à l’intérieur du transport Streamable HTTP seulement pour les réponses longues ; le protocole HTTP+SSE autonome historique est déprécié et n’est pas utilisé.
- **Développement local** : `stdio` autorisé pour lancer le serveur MCP localement depuis un client de test.
- **Endpoints & Contrôles** :
  - `POST /mcp` : Messages client $\rightarrow$ serveur.
  - `GET /healthz` : Health check liveness.
  - `GET /readyz` : Readiness check.
  - Validation de `Origin`, timeout de tool call, rate limit interne par service account et propagation du correlation ID vers Laravel.
- **Justification** : Services découplés, standard MCP moderne, observabilité, mise à l'échelle et sécurité réseau.
- **Statut** : 🟢 Décision acceptée.

---

### OQ-02 : Stockage des Preuves d’Ingestion (S3 / MinIO)
- **Décision** : **Stratégie hybride** adaptée au risque et à la taille des fichiers :
  1. **Laravel Proxy (Validation immédiate)** : Courriels bruts (`.eml`), PDF de contrats/assurances et documents administratifs légers. Ingestion $\rightarrow$ validation MIME réelle + hash SHA-256 immédiat + enregistrement dans `audit_events` $\rightarrow$ stockage objet privé.
  2. **URL Pré-signée S3/MinIO (Direct Upload)** : Photos de retour/check-in, vidéos de dommages et gros fichiers de migration. Upload direct du client vers le préfixe `uploads/quarantine/...` avec TTL de 5 à 10 minutes (aucun ACL public).
- **Finalisation obligatoire en tâche de fond** : Un worker Laravel (`FinalizeEvidenceUpload`) vérifie la taille réelle, le type MIME par contenu, calcule le hash SHA-256, lance le scan antivirus, rattache le `company_id` et déplace l'objet vers `evidence/{company_id}/{hash}` en émettant l'événement `evidence.ingested`.
- **Accès Agent** : Onyx ne reçoit jamais d'URL S3 durable. Il reçoit un `evidence_id`, une URL signée à durée très courte (5 min), le texte extrait/sanitisé et le hash de provenance.
- **Paramètres de stockage** :
  ```env
  FILESYSTEM_DISK=s3
  AWS_BUCKET=cortex-private
  AWS_USE_PATH_STYLE_ENDPOINT=true
  CORTEX_UPLOAD_PRESIGN_TTL_SECONDS=600
  CORTEX_UPLOAD_MAX_DOCUMENT_MB=25
  CORTEX_UPLOAD_MAX_IMAGE_MB=20
  CORTEX_UPLOAD_MAX_VIDEO_MB=500
  CORTEX_EVIDENCE_QUARANTINE_PREFIX=uploads/quarantine
  CORTEX_EVIDENCE_FINAL_PREFIX=evidence
  CORTEX_EVIDENCE_HASH_ALGORITHM=sha256
  ```
- **Statut** : 🟢 Décision acceptée.

---

### OQ-03 : Cache & Verrous Atomiques (Valkey 8)
- **Décision** : **Valkey 8** est le standard unique pour dev, staging et production.
- **Rôles dans Cortex** :
  - **Cache** : Recherches d'items, configuration de policies, sessions opérateurs.
  - **Queues** : OCR, extraction PDF, génération de rapports, scans antivirus, jobs de finalisation.
  - **Verrous distribués** : Tentatives de réservation, assignation de serial numbers, payouts consignation, idempotence des factures.
  - **Rate limiting** : Endpoints API Laravel, outils MCP et interfaces agents.
- **Règle d'or de protection transactionnelle** : Valkey ne remplace JAMAIS PostgreSQL. La garantie finale d'intégrité d'inventaire et financière repose sur la transaction SQL + verrou pessimiste (`lockForUpdate`) + contrainte DB + revalidation juste avant écriture + idempotency key + audit log immuable.
- **Configuration Docker / Prod** :
  ```yaml
  valkey:
    image: valkey/valkey:8.0.2-alpine
    command:
      - valkey-server
      - --appendonly
      - "yes"
      - --save
      - "900 1"
      - --save
      - "300 10"
      - --save
      - "60 10000"
  ```
- **Statut** : 🟢 Décision acceptée.

---

### OQ-04 : Cycle de Vie & Rotation des Tokens d'Agents
- **Décision** : **Service accounts distincts par agent et par environnement**, avec scopes minimaux et tokens courts renouvelés automatiquement. Aucun token statique par tenant.
- **Résolution du Tenant** : Le `company_id` est STRICTEMENT déterminé et validé côté serveur par Laravel (contexte utilisateur authentifié, mapping de service account, session signée). Zéro `company_id` libre accepté depuis un prompt, un paramètre MCP ou un header non signé.
- **Identités types** :
  - `svc-cortex-onyx-intake-prod` : Scopes `agent:items:read`, `agent:customers:read`, `agent:availability:read`, `agent:pricing:calculate`, `agent:quote-drafts:create`, `agent:customer-drafts:create`, `agent:approvals:create`.
  - `svc-cortex-onyx-availability-prod` : Scopes `agent:items:read`, `agent:availability:read`.
  - `svc-cortex-onyx-reporting-prod` : Scopes `agent:consignment-reports:read`, `agent:reports:generate`.
- **Interdictions universelles pour tout agent** :
  - `agent:approval:approve`
  - `agent:contracts:activate`
  - `agent:invoices:finalize`
  - `agent:payments:create`
  - `agent:credits:issue`
  - `admin:*`
  - `db:*`
- **Transition MVP** : Token Sanctum de 7 jours géré dans un secret manager et roté automatiquement en attendant la mise en place du broker de workload OIDC / mTLS.
- **Statut** : 🟢 Décision acceptée.
