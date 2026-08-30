# Politique de Securite — Cortex ERP

La securite des donnees transactionnelles et l'etancheite multi-tenant de nos clients sont au coeur de la conception de Cortex ERP.

---

## Modele de Menace & Invariants de Securite

1. **Isolation Multi-Tenant Absolue** :
   - Aucun utilisateur, operateur ou agent IA ne doit pouvoir acceder, lire ou muter les enregistrements d'une autre entreprise (`company_id`).
   - Tout modele de donnees herite du trait `BelongsToCompany` et valide la presence du `company_id` des la creation.

2. **Garde-fous IA & Controle des Agents** :
   - Les agents Onyx et façades MCP ne disposent d'aucun acces SQL direct a la base PostgreSQL.
   - Les actions a impact financier (confirmation de contrat, facturation, versement de consignation) sont verrouillees par des Policies et une porte d'approbation humaine (`approval_requests`).

3. **Immutabilite de l'Audit** :
   - Les evenements enregistres dans `audit_events` sont en ecriture seule (*append-only*). Toute tentative de mise a jour ou de suppression leve une exception `ImmutableRecordException`.

---

## Signalement d'une Vulnerabilite

Si vous decouvrez une faille de securite dans Cortex ERP :

1. **Ne creez pas d'issue publique sur GitHub.**
2. Envoyez un rapport detaille par courriel a : **security@cortexerp.com**.
3. Incluez :
   - La description de la vulnerabilite.
   - Les etapes pour reproduire la faille.
   - L'impact potentiel sur le cloisonnement multi-tenant ou l'audit.

Notre equipe s'engage a accuser reception sous **24 heures ouvrees** et a publier un correctif dans les plus brefs delais.
