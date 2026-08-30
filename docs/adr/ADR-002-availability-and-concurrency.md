# ADR-002 : Stratégie de Calcul de Disponibilité et Gestion de la Concurrence

## Statut
Accepté

## Contexte
Cortex ERP doit fournir une surface d'API de lecture à haute performance permettant aux opérateurs du comptoir et aux agents Onyx (via MCP) de vérifier instantanément la disponibilité de matériel sur une fenêtre calendaire donnée (`POST /api/v1/cortex/availability/check`).

Les règles métier de location établissent que :
- Les soumissions (`quote`), factures (`invoiced`) et annulations (`cancelled`) **ne bloquent pas** l'inventaire.
- Les réservations (`reservation`), contrats confirmés (`contract`) et matériels sortis (`checked_out`) **bloquent** l'inventaire.

Une problématique critique réside dans la gestion des conflits d'inventaire et des accès concurrents (deux agents ou opérateurs consultant le même équipement au même moment).

## Décision

1. **Calcul pur en lecture (Read-Only Projection) :**
   - Le service `AvailabilityService` effectue une projection temporelle pure en mémoire à partir des lignes de transactions bloquantes en base de données.
   - L'endpoint `POST /api/v1/cortex/availability/check` est strictement idempotent et **n'acquiert aucun verrou pessimiste**, ne modifie aucune donnée et ne réserve aucun créneau.

2. **Séparation claire entre Consultation (Read) et Mutation (Write) :**
   - La vérification de disponibilité retourne l'état à l'instant $T$. Deux requêtes simultanées peuvent légitimement observer que le stock restant est de 1 unité.
   - La prévention des sur-engagements (double-booking) est déléguée à l'étape de **mutation** (passage à l'état `reservation` ou `contract`).

3. **Stratégie de Verrouillage à la Mutation (Travaux Futurs / PRD-INV-003) :**
   - Lors de la création ou confirmation d'une réservation, le service de transaction utilisera :
     1. Un verrou distribué Redis atomique par équipement (`rental:lock:item:{company_id}:{item_id}`) avec TTL court (ex: 5s).
     2. Une re-vérification de disponibilité sous transaction PostgreSQL avec `SELECT ... FOR UPDATE`.
     3. La création atomique de la ligne et l'assignation des numéros de série.

## Conséquences

### Positives
- **Performance & Scalabilité :** Les requêtes de consultation des agents et des écrans UI sont ultra-rapides et ne créent aucun goulot d'étranglement ou interblocage (deadlock) en base de données.
- **Simplicité du contrat d'API :** L'API de lecture est sans effet de bord, facilitant les tests de contrat et la consommation par les LLMs Onyx.

### Négatives / Précautions
- Une réponse positive de disponibilité ne constitue pas une garantie d'obtention si un autre acteur valide une réservation avant l'utilisateur. Les agents doivent être conçus pour gérer l'échec éventuel lors de la soumission de réservation.
