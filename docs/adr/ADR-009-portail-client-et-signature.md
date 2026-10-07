# ADR-009 — Portail client, demandes, chèques et parcours de signature

**Statut :** portail de demandes et chèque livrés (v0.12.0); **acceptation avec consentement explicite livrée (v0.15.0)**.
**Date :** 2026-10-07

## Contexte
Phase 6 du plan de livraison : permettre à un client de soumettre une demande, de voir le matériel réellement
disponible et de suivre la réponse; offrir le paiement par chèque et, quand le fournisseur est configuré, en ligne;
définir le parcours de signature **avant** de promettre une signature juridiquement valide.

## Décisions livrées
1. **Une demande n'est pas une réservation.** `/demande/<identifiant>` crée une demande entrante
   (`Cortex Inbound Request`, canal « Web Portal »). Aucun matériel n'est bloqué, aucune facture créée.
2. **Portail activé par société** (`portal_requests_enabled`, `portal_slug` unique dans *Cortex Finance Settings*).
   Un portail désactivé ou inconnu répond comme s'il n'existait pas.
3. **Calendrier public sans quantité ni client** : statuts par jour (libre / limité / complet), même règle que la grille
   interne. Indicatif; la vérification qui fait foi reste celle du serveur à la réservation.
4. **Suivi par jeton** (`/suivi/<jeton>`) : seule l'empreinte SHA-256 est conservée; la page ne montre ni courriel ni
   téléphone, seulement l'état, la période, le matériel et le message que l'équipe écrit pour le client.
5. **Protections** : limite par adresse IP sur chaque appel, champ piège (robots), consentement obligatoire, plafond de
   50 demandes par société et par jour, texte nettoyé de toute balise, matériel limité aux équipements de la société.
6. **Chèque** : option par société (`accept_cheque`, `cheque_payable_to`). Le client « annonce » un chèque : la facture
   d'acompte est créée (sa référence se met au dos du chèque), l'équipe est prévenue, la liste « Chèques annoncés » de
   Finance suit les annonces. **Rien n'est marqué payé** : l'entreprise enregistre le paiement (mode « Chèque ») à la
   réception; l'acompte de la page du client passe alors à « payé » (rapprochement).
7. **Paiement en ligne** : inchangé (ADR-007), offert seulement si les clés Stripe et le secret du webhook de la société
   existent. Non essayé avec un vrai compte Stripe.

## Acceptation et signature : consentement explicite (décision de Kael, 2026-10-07 — remplace la condition d'avis juridique)
Pas d'avocat requis. À la place :
- **Conditions du contrat par société** (*Cortex Finance Settings* › « Contrat de location : conditions »). Un **modèle de départ** est fourni (`contract_terms.DEFAULT_TERMS`) et la société le **modifie librement** (bouton « Insérer le modèle par défaut » puis édition). La **version** augmente à chaque changement du texte.
- **Instantané** : le devis envoyé garde les conditions (texte, version, empreinte SHA-256) telles qu'à l'envoi; modifier le modèle ensuite ne change pas un devis déjà parti.
- **Consentement avant d'accepter** : le client voit les conditions sur le devis et doit cocher « J'ai lu et compris les conditions du contrat, et je les accepte. Mon nom ci-dessus vaut signature. » ; sans cette case, le serveur refuse l'acceptation (`check_acceptance`). La société peut désactiver cette exigence; les devis envoyés avant cette règle n'en exigent pas.
- **Preuves conservées** sur le partage : version et empreinte des conditions, date et heure, nom saisi, empreinte (SHA-256) de l'adresse IP et du navigateur liée au jeton, et trace d'audit (acteur « Customer »).
- **Limites honnêtes** : une case à cocher et un nom saisi sont une acceptation électronique simple; ce n'est pas une signature certifiée ni une vérification d'identité (le courriel n'est pas vérifié par lien). Le modèle de départ est un point de départ à adapter, pas un avis juridique. Aucun fournisseur de signature n'est intégré.

## Conséquences et limites
- Le courriel de confirmation au demandeur n'est pas envoyé (courriel sortant non éprouvé) : le lien de suivi s'affiche
  à l'écran et doit être conservé.
- Les demandes du portail n'entrent pas encore automatiquement dans l'extraction par IA.
- Le portail ne gère ni compte client, ni historique des demandes d'une même personne.
