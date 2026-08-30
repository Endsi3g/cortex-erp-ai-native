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

3. **Stratégie de Verrouillage à la Mutation (implémentée — voir
   `services/locking.py` et `CortexRentalTransaction.transition_to`) :**
   - Lors de la confirmation d'une réservation ou d'un contrat, le service de transaction :
     1. Acquiert un verrou distribué Redis/Valkey atomique par équipement (`rental:lock:item:{company}:{item_code}`) avec TTL court (5s).
     2. Re-vérifie la disponibilité sous ce verrou (`AvailabilityService.check`, en excluant la transaction courante de son propre décompte via `exclude_transaction`).
     3. Ne commet le changement d'état (`self.save()`) que si la re-vérification confirme la disponibilité.
   - Stack réelle : **MariaDB/InnoDB** (pas PostgreSQL — voir `infra/docker/docker-compose.dev.yml` et les DocTypes JSON, dont l'`engine` a été corrigé de `PostgreSQL` à `InnoDB`). Une future itération peut ajouter un `SELECT ... FOR UPDATE` InnoDB en complément du verrou Redis si le volume de contention l'exige ; ce n'est pas fait dans cette passe.

## Conséquences

### Positives
- **Performance & Scalabilité :** Les requêtes de consultation des agents et des écrans UI sont ultra-rapides et ne créent aucun goulot d'étranglement ou interblocage (deadlock) en base de données.
- **Simplicité du contrat d'API :** L'API de lecture est sans effet de bord, facilitant les tests de contrat et la consommation par les LLMs Onyx.

### Négatives / Précautions
- Une réponse positive de disponibilité ne constitue pas une garantie d'obtention si un autre acteur valide une réservation avant l'utilisateur. Les agents doivent être conçus pour gérer l'échec éventuel lors de la soumission de réservation.
