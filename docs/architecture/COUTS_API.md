# Coûts des API externes et plafond de l'assistant IA

Recherche faite le 2026-10-05 sur les pages officielles des fournisseurs. **Les prix changent** : les valeurs ci-dessous
sont à revérifier avant de les figer dans une offre. Montants en dollars US sauf indication (Google et Resend facturent en USD).

## 1. Modèle IA : Gemini (source : ai.google.dev/gemini-api/docs/pricing)

| Modèle | Entrée / 1 M jetons | Sortie / 1 M jetons | Lot (batch) | Remarque |
| --- | --- | --- | --- | --- |
| `gemini-3.8-flash` (**retenu**) | 0,75 $ | 3,75 $ | 0,375 $ / 1,875 $ | « Plus intelligent des Flash », agents et outils. **Tarif affiché jusqu'au 31 déc. 2026** : à revérifier après. Cache de contexte : 0,075 $ entrée. |
| `gemini-3.7-flash` | 0,75 $ | 3,75 $ | 0,375 $ / 1,875 $ | Même prix que 3.8, donc aucune raison de le préférer. |
| `gemini-3.5-flash-lite` | 0,30 $ | 2,50 $ | 0,15 $ / 1,25 $ | Repli économique (champ « Modèle de repli »). |
| `gemini-3.1-flash-lite` | 0,25 $ | 1,50 $ | 0,125 $ / 0,75 $ | Le moins cher; réponses plus simples. |
| `gemini-2.5-pro` | 1,25 $ | 10,00 $ | 0,625 $ / 5,00 $ | Hérité; « accès limité » pour les nouveaux projets. |

L'identifiant `gemini-3.8-flash` **existe** (confirmé sur la page des modèles). Les jetons de réflexion sont facturés comme de la sortie
(la passerelle les compte déjà dans les jetons de sortie).

### Estimation du coût par société (hypothèses explicites)

Un tour de conversation = 2 appels au modèle (outil puis réponse) : environ 8 000 jetons en entrée (consigne, historique,
résultats d'outils) et 1 200 en sortie (réponse + réflexion).

- Coût par tour : 8 000 × 0,75 $/M + 1 200 × 3,75 $/M = 0,006 $ + 0,0045 $ ≈ **0,0105 $ (environ 1 cent)**.
- 20 personnes × 10 tours par jour × 22 jours = 4 400 tours/mois ≈ **46 $/mois**. Usage normal d'une petite équipe (5 personnes) : ≈ 12 $/mois.
- Avec `gemini-3.5-flash-lite` en repli : environ 3 fois moins cher.

### Plafond retenu (modifiable, par société, dans *Cortex AI Settings*)

- **60 $ US par société et par mois** (environ 6 % d'un abonnement de 1 000 $) : couvre ~5 700 tours; avertissement à 80 % (48 $), refus à 100 %.
- Les gros comptes se règlent dans le tableau « Plafonds par société ». Le coût réel est visible dans le rapport *Utilisation IA*.
- Réviser dès que 3 mois d'usage réel existent : le plafond doit rester très au-dessus de l'usage normal pour ne jamais gêner un client qui paie.

## 2. Paiement en ligne (acompte dans le portail) : Stripe Canada (source : stripe.com/en-ca/pricing)

- Cartes canadiennes : **2,9 % + 0,30 $ CA** par transaction réussie; cartes internationales +0,8 %; conversion de devise +2 %.
- Litige : 15 $ CA par litige. Aucuns frais d'installation ni mensuels.
- Exemple : acompte de 733,65 $ → frais ≈ 21,58 $ (2,9 %) + 0,30 $ ≈ 21,88 $. À répercuter ou absorber : **décision de prix** (consensus).
- Interac en ligne : non confirmé dans la documentation consultée; à vérifier avant de le promettre. En attendant, le portail affiche aussi des instructions de virement manuel configurables.

## 3. Courriel transactionnel (devis, invitations)

| Fournisseur | Prix | Quand |
| --- | --- | --- |
| Amazon SES | 0,10 $ / 1 000 courriels (à la carte), pièces jointes 0,12 $/Go | Le moins cher; configuration DNS plus technique. |
| Resend | Gratuit : 3 000/mois (100/jour); Pro 20 $/mois pour 50 000 | Le plus simple pour démarrer. |

Volume attendu : quelques centaines de courriels par société et par mois, donc **le palier gratuit de Resend suffit au début**; SES devient plus avantageux au-delà de ~50 000/mois.

## 4. Coût mensuel type par société (ordre de grandeur)

IA 12–46 $ + courriel < 1 $ + paiement 2,9 % + 0,30 $ par acompte encaissé. Le coût fixe par société reste donc très inférieur à 100 $ pour un abonnement de 1 000 $.

## 5. À décider par les cofondateurs (stratégie, prix : consensus)

1. Plafond par défaut (60 $ proposé) et ce qui se passe au plafond (refus, ou passage automatique au modèle économique).
2. Qui paie les frais de Stripe (client final ou société).
3. Courriel : Resend (simple) ou SES (moins cher à grande échelle).
