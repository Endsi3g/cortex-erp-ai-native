# Décision : moteur IA maison léger ou Onyx ?

> Question posée : vaut-il mieux créer un système IA complet dans Cortex, ou continuer avec Onyx (avec sa pile) ?
> Réponse courte : **remplacer Onyx par une passerelle IA maison, mince, dans l'application Frappe existante.**
> Garder la façade MCP seulement pour des agents externes. Réintroduire un moteur de recherche documentaire (Onyx ou autre)
> plus tard, si, et seulement si, la recherche dans des documents devient un vrai besoin.

## 1. Ce que l'on a aujourd'hui (faits vérifiés dans le dépôt)

- La conversation passe par `api/v1/chat.py` → `services/chat_session.py` (~440 lignes) → `services/onyx_chat_client.py`
  (~280 lignes) qui appelle Onyx par HTTP avec un **persona** et des **outils** identifiés par des **numéros** lus dans la
  configuration du site.
- Onyx est un produit complet : d'après `infra/onyx/README.md`, il faut son propre backend, une base Postgres, OpenSearch,
  Redis, MinIO et un serveur de modèles d'inférence, **indépendants** de MariaDB/Valkey de Frappe.
- Cortex n'utilise d'Onyx que deux choses : un **persona** (instructions) et l'**appel d'outils** (via la façade MCP
  `apps/cortex-mcp`, ~300 lignes). La recherche dans des documents, les connecteurs et l'indexation (ce qui justifie la pile) **ne sont pas
  utilisés**.
- Sur l'environnement de développement actuel, **Onyx n'est pas configuré** : la conversation ne peut donc pas répondre
  pour de vrai. L'accueil IA et le copilote affichent l'état « indisponible » au lieu d'inventer une réponse (comportement voulu).
- Les frontières de sécurité sont déjà **dans Frappe**, pas dans Onyx : les agents ne décident jamais, une demande d'approbation
  exige un humain, l'auteur ne peut pas approuver sa propre demande, journal d'audit immuable, clés d'idempotence.

## 2. Options comparées

| Critère | A. Continuer avec Onyx | B. Passerelle maison mince (recommandée) | C. « Système IA complet » maison |
| --- | --- | --- | --- |
| Services à exploiter | Frappe + 6 à 7 services Onyx | **Aucun de plus** | Aucun de plus, mais beaucoup de code |
| Coût et pannes en production | Élevés (mémoire, mises à jour, sauvegardes, versions d'Onyx) | Faible | Moyen |
| Ce qu'on utilise réellement | ~10 % du produit | 100 % | 100 % |
| Sécurité et permissions | Indirectes (jeton → API Frappe) | **Directes** : outil = fonction Python exécutée avec l'utilisateur connecté | Directes |
| Latence | Saut réseau supplémentaire | Un seul saut vers le fournisseur du modèle | Idem B |
| Choix du modèle | Dicté par la configuration d'Onyx | Interchangeable (adaptateur par fournisseur) | Idem B |
| Recherche documentaire (PDF, contrats) | **Incluse** | Non, à ajouter plus tard | À construire (coûteux) |
| Effort initial | Déjà fait, mais non configuré | ~1 à 2 semaines | Plusieurs mois |
| Risque | Complexité opérationnelle, dépendance | Faible si on reste mince | Élevé (réinventer) |

Conclusion : le coût d'Onyx est payé en entier, la valeur utilisée est faible. Un « système complet » (option C) ne se justifie
pas non plus : il faut éviter de reconstruire ce que les fournisseurs de modèles offrent déjà (appel d'outils, sorties
structurées). **Option B : mince et bien bornée.**

## 3. Architecture recommandée

```
Accueil IA / Copilote / Mobile
        │  (POST chat.send, flux d'événements)
        ▼
api/v1/chat.py            ← inchangé pour les interfaces
services/chat_session.py  ← inchangé : sessions, messages, audit, transformation des réponses
services/ai_gateway.py    ← NOUVEAU (remplace onyx_chat_client.py)
   ├─ adaptateur fournisseur (Anthropic / Gemini / modèle local) — interface unique `complete(messages, tools)`
   ├─ registre d'outils : fonctions Python déclarées avec leur portée
   │     lecture : disponibilité, recherche de location, file d'approbations, état du parc
   │     proposition : « préparer un devis », « proposer une réservation » (jamais d'écriture définitive)
   └─ boucle outil : le modèle demande un outil → exécution sous l'utilisateur → résultat → réponse
```

Règles non négociables (déjà dans le projet, à conserver telles quelles) :

1. Un outil s'exécute **avec l'utilisateur connecté** (ses rôles, sa société) ; aucun compte de service tout-puissant.
2. Les outils d'écriture **créent une proposition** ou une demande d'approbation ; seule une personne approuve.
3. Chaque appel d'outil est audité (`Cortex Agent Tool Call`), avec clé d'idempotence pour les écritures.
4. Aucune clé de fournisseur dans le navigateur : appels serveur seulement, clés dans la configuration du site.
5. Réponses déclarées « simulées » quand le modèle est indisponible ; jamais de succès inventé.
6. Limites de débit et de coût par société, plafond d'étapes par tour (évite les boucles).

## 4. Et MCP ?

La façade `apps/cortex-mcp` **reste utile** pour des agents externes (un assistant de bureau d'un client, un outil de
développement). Mais l'interne n'a pas besoin de passer par MCP : appeler directement les fonctions évite un saut et des
erreurs de sérialisation. Les deux partagent le même registre d'outils pour ne pas diverger.

## 5. Plan de migration (sans casser l'existant)

1. Introduire `AIGateway` derrière l'interface `OnyxChatClient` existante (même signature) : `chat_session.py` ne change pas.
2. Implémenter un premier adaptateur (un seul fournisseur) + 4 outils de lecture + 1 outil de proposition.
3. Ajouter les tests : permissions par rôle, refus d'écriture directe, audit, idempotence, panne du fournisseur.
4. Basculer par paramètre du site (`cortex_ai_engine = gateway | onyx | mock`), garder Onyx désactivé mais présent une version.
5. Retirer `infra/onyx` et les identifiants numériques quand la passerelle est stable.
6. Mesurer : latence p50/p95, taux d'outils refusés par permission, coût par conversation.

## 6. Quand reconsidérer Onyx (ou un moteur de recherche)

- Si les clients veulent interroger **leurs documents** (contrats PDF, fiches techniques) en langage naturel.
- Si l'équipe préfère adopter un produit complet plutôt que maintenir une petite passerelle.
  Dans ce cas, le mettre **derrière** la passerelle comme un outil de recherche de documents, pas comme le cerveau du système.

## 7. Risques de l'option recommandée

- Il faut maintenir l'adaptateur de chaque fournisseur (petit, mais réel). Mitigation : une seule interface et des tests de contrat.
- Le modèle peut mal utiliser un outil : les droits et les approbations du serveur bornent déjà les dégâts.
- Pas de mémoire longue ni de recherche documentaire au départ : assumé, voir § 6.

## 8. Décisions attendues

1. Fournisseur de modèle principal et plafond de coût mensuel par société.
2. Le modèle local (`qwen3:8b` mentionné dans `infra/onyx/README.md`) reste-t-il une option de secours ?
3. Le premier périmètre de l'assistant : lecture seule + devis proposés, ou aussi tâches de relance ?
