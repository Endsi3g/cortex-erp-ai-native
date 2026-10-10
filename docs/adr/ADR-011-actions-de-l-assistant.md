# ADR-011 : actions de l'assistant — proposer, aperçu, approbation humaine, exécution

Statut : accepté le 2026-10-10 (réponses de Kael : aperçu + approbation; un site par client; approbateur = propriétaire) · Complète : ADR-006.

## Contexte

Kael veut un ERP « AI-native » où l'assistant agit partout (créer, modifier, plus tard changer colonnes, sections et catégories de pages),
pour toute société de location. Le contrat du produit reste « Cortex suggère, l'humain décide » (`AGENTS.md`).

## Décision

1. **Le modèle n'écrit jamais.** Il appelle un outil `propose_*` qui valide et calcule l'aperçu avec les services de l'écran
   (prix du serveur, droits, société) et garde la proposition dans `Cortex AI Action` (24 h).
2. **La personne décide dans la conversation.** `chat.decide_action` approuve ou refuse; seule la personne qui a demandé peut décider.
   L'exécution prend **ses droits** et passe par la même fonction que l'écran (`rentals.insert_quote`, `customers.insert_customer`).
3. **Revalidation à l'approbation.** Si l'aperçu a changé (prix, client, données), la proposition est périmée et rien n'est écrit.
4. **Une fois, avec verrou, dans un point de sauvegarde.** Un double clic n'exécute qu'une fois; un échec annule toute écriture partielle
   et est noté « Échec » (jamais présenté en succès). Chaque issue (proposée, exécutée, refusée, périmée, échouée) est au journal d'audit.
5. **Interrupteur du site `cortex_ai_actions`** (éteint par défaut) : les outils `propose_*` ne sont offerts au modèle qu'une fois
   l'affichage des boutons Approuver/Refuser validé dans la conversation.

## Conséquences et limites

- Livré (vague 1) : créer un client, créer un devis. Jamais essayé sur un Desk Frappe ni avec un vrai modèle.
- Non livré : les boutons Approuver/Refuser dans la conversation (décision de design à valider avec Kael), les autres actions métier,
  la modification de la structure (champs, sections, espaces de travail, catégories de pages), les modèles de secteur.
- Structure (vague 2, à concevoir) : un site par client rend sûr de créer des `Custom Field`, `Property Setter` et `Workspace` ;
  le propriétaire de la société approuve, avec un avant/après et une annulation.

## Addendum (phase 13) : modifier un champ, annuler

- **`update_field`** : une action générique mais bornée par **deux listes blanches** (`records.READABLE` pour lire, `records.EDITABLE` pour modifier, champ par champ). Jamais « n'importe quel champ » : un statut, un montant calculé, une société ou un champ en lecture seule ne s'y trouvent pas (un test échoue si on en ajoute un).
- **Avant/après** : l'aperçu montre la valeur lue au moment de proposer; l'empreinte de l'aperçu l'inclut, donc une valeur changée avant l'approbation rend la proposition périmée.
- **Annulation** : `ActionSpec.undo` + `actions.undo()`. Ce que `run` renvoie sous la clé `undo` (type, nom, champ, avant, après) est gardé dans `result_json`; l'annulation remet l'ancienne valeur **seulement si la valeur actuelle est encore « après »**, sous verrou, avec les droits de la personne; sinon elle refuse en disant pourquoi et la carte reste « Fait ». État final `Undone`; tout est au journal d'audit (`executed`, `undone`, `undo_failed`).
- Ce que cela ne fait pas : pas de modification de structure, de statut ni de montant; pas de suppression; l'annulation d'autres actions (devis créé, paiement) reste manuelle depuis l'écran concerné.
