# ADR-004 : Consolidation du catalogue location — suppression de `Rental Item`

## Statut
Accepté

## Contexte

Deux DocTypes couvraient le même concept métier (« profil de location d'un
article catalogue ») de façon incompatible :

- **`Rental Item`** (`rental_item.json`) : DocType autonome, non lié à
  l'ERPNext `Item`. Champs : `company`, `item_name`, `code`, `item_group`,
  `is_serialized`, `total_quantity`, `daily_rate`, `weekly_rate`,
  `replacement_value`, `description`.
- **`Cortex Rental Item Profile`** (`cortex_rental_item_profile.json`) :
  profil rattaché à un `Item` ERPNext existant via `item_code` (Link),
  avec `category`, `daily_rate`, `replacement_value`, `deposit_required`,
  `prep_hours`, `is_consignment_allowed`, `required_accessories`.

Audit du code réel (`grep` sur `apps/cortex_rental`) : **`Rental Item`
n'est référencé nulle part** — aucun service, aucun endpoint `api/v1/*`,
aucun test ne le lit ni ne l'écrit. Seul `search_items_handler`
(`api/v1/items.py`) est réellement exercé, et il interroge exclusivement
`Cortex Rental Item Profile`. `Rental Item` est un premier brouillon
(comme l'était le module `api/` non-versionné supprimé précédemment),
jamais branché, jamais supprimé.

## Décision

1. **`Cortex Rental Item Profile` devient l'unique DocType canonique** du
   catalogue locatif Cortex. Il respecte le principe PRD « réutiliser
   ERPNext seulement si le concept est réellement équivalent » : `Item`
   porte l'identité du produit (nom, groupe, unité), `Cortex Rental Item
   Profile` porte les attributs spécifiques à la location.
2. **`Rental Item` est supprimé** (DocType, permission hook,
   `permission_query_conditions`). Rien ne le référence après cet ADR.
3. **Les deux champs utiles de `Rental Item` migrent vers `Cortex Rental
   Item Profile`** — ils manquaient et sont requis par le PRD §4
   (« Non sérialisé : disponibilité par quantité ») :
   - `is_serialized` (Check, défaut 1) : si faux, l'article n'a pas de
     `Serial No` individuels ; sa disponibilité se calcule par quantité
     totale, pas par comptage de numéros de série.
   - `total_quantity` (Int) : taille de flotte pour les articles non
     sérialisés uniquement (ignoré si `is_serialized = 1`, où la vérité
     vient du comptage réel des `Serial No`).
4. `AvailabilityService.check()` branche désormais sur `is_serialized` :
   sérialisé → comptage `Serial No` (inchangé, déjà corrigé en
   Phase 5) ; non sérialisé → `total_quantity - reserved_qty` (les
   statuts quarantaine/réparation/manquant par unité individuelle ne
   s'appliquent pas à un article non sérialisé, par construction).

## Conséquences

### Positives
- Un seul DocType catalogue, aligné sur `Item` ERPNext au lieu d'un
  doublon isolé — cohérent avec l'invariant « pas de duplication de
  règles ».
- Disponibilité correcte pour les articles non sérialisés (câbles,
  connecteurs, consommables), auparavant non modélisés du tout.

### Négatives / Précautions
- `total_quantity` reste un champ déclaratif manuel (pas de synchronisation
  avec un `Bin`/grand livre de stock ERPNext). Suffisant pour le pilote ;
  une intégration stock ERPNext complète pour les articles non sérialisés
  reste un chantier ouvert, pas traité ici.
- Toute donnée réelle éventuellement saisie dans `Rental Item` avant cet
  ADR n'est pas migrée automatiquement (aucune n'existe dans ce repo —
  DocType jamais utilisé en pratique).
