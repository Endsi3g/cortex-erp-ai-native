# ADR-006 : passerelle IA (Gemini, modèle configurable) et écritures comptables

Statut : accepté le 2026-09-30 (décisions du propriétaire du produit) · Remplace : Onyx comme moteur par défaut · Complète : ADR-005.

## Contexte

Les clients paieront plus de 1 000 $ par mois : l'assistant doit être fiable, contrôlé en coût et facile à faire évoluer.
Décisions : **passerelle IA interne** (voir `docs/architecture/AI_ENGINE_DECISION.md`), **Gemini** comme modèle, avec un
changement de version aussi simple que possible; **plafond de coût à déterminer**; **écritures comptables** pour les
comptables.

## A. Passerelle IA (`services/ai/`)

| Sujet | Choix |
| --- | --- |
| Modèle | Champ « Modèle » de `Cortex AI Settings` (défaut `gemini-3.8-flash`). Passer à une version plus récente = changer ce champ. Un « modèle de repli » optionnel n'est utilisé que si le principal répond 404 chez le fournisseur. |
| Fournisseur | Interface `LLMProvider`; `GeminiProvider` (API REST `generateContent`, appel de fonctions, signatures de réflexion conservées entre les tours). Le préfixe de l'identifiant choisit le fournisseur; un autre fournisseur = une classe de plus. |
| Clé | Champ `Password` chiffré des réglages, sinon `gemini_api_key` de la configuration du site. Envoyée en en-tête par le serveur, jamais au navigateur, jamais dans l'URL. |
| Outils | `search_rental_items`, `check_inventory_availability`, `search_customers`, `list_rentals`, `list_pending_approvals`, `finance_summary`, `create_quote_draft` (proposition, ne crée rien). Chacun s'exécute **avec les droits de la personne connectée** et dans sa société; la liste par agent reste `services/tool_policy.py`. Aucun outil n'écrit, ne confirme ni n'approuve. |
| Budget | `Cortex AI Usage` (un enregistrement par appel : jetons, coût, société, personne); plafond mensuel en dollars et/ou en jetons, par défaut et par société (`Cortex AI Budget`). **0 = aucun plafond** (valeur livrée : le plafond reste à déterminer). Avertissement à 80 % dans la réponse, refus à 100 %. |
| Coût | Calculé avec les prix par million de jetons saisis dans les réglages (0 par défaut : sans prix, seuls les jetons sont comptés). |
| Moteur | Clé de site `cortex_chat_provider` : `gateway` (défaut), `onyx` (ancien moteur, conservé une version) ou `mock` (développement). |
| Panne | Message clair en français (clé absente, clé refusée, modèle introuvable, service occupé, budget atteint); rien n'est présenté comme réussi. Les jetons déjà consommés restent comptés. |
| Rapport | *Utilisation IA* (mois × modèle × personne). |

## B. Écritures comptables (`services/ledger.py`)

Journal à partie double propre à Cortex (`Cortex Journal Entry` + lignes), généré par le serveur à chaque facture émise,
paiement et remboursement; **équilibré** (validation), **immuable** (correction = écriture inverse), filtré par société.
Plan de comptes configurable par société dans `Cortex Finance Settings` (défauts : 1100 Comptes clients, 1000 Encaisse et banque, 2400
Acomptes clients, 2310 TPS, 2320 TVQ, 4000 Revenus de location, 4100 Frais de retard). Rapports *Journal comptable* et
*Balance de vérification*; patch de reprise pour les factures et paiements existants.

Vérifié sur la simulation de 91 jours : 542 écritures, 0 déséquilibrée, clients du grand livre = soldes des factures
(63 660,77 $), écarts encaisse et taxes à 0, aucune facture ni paiement sans écriture.

## Conséquences et limites

- Le **nom exact du modèle** `gemini-3.8-flash` est une hypothèse du propriétaire : à confirmer chez Google. Sans clé API, l'assistant répond
  par un message de configuration; les appels réels au fournisseur n'ont pas été exécutés ici (tests avec un fournisseur simulé).
- Le **plafond de coût** et les **prix** sont à saisir; tant qu'ils sont à 0, aucun refus n'est appliqué.
- Le grand livre d'ERPNext n'est toujours pas alimenté : le journal Cortex sert de source au comptable (export de rapport). Un
  plan comptable propre à chaque comptable se règle dans les réglages financiers.
- Hors périmètre : dépôt de garantie distinct, notes de crédit, relances automatiques, recherche documentaire.
