# ADR-009 — Portail client, demandes, chèques et parcours de signature

**Statut :** portail de demandes et chèque livrés (v0.12.0); **signature : définie, non livrée.**
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

## Parcours de signature : défini, non livré
Aucune « signature » n'est présentée au client tant que ce qui suit n'est pas décidé et validé par un juriste :
- **Ce qui est signé** : le contrat approuvé (version figée, empreinte SHA-256 du document), jamais un devis modifiable.
- **Preuves à conserver** : empreinte du document, identité déclarée (nom, courriel vérifié par lien à usage unique),
  horodatage serveur, adresse IP et agent utilisateur (empreintes), acceptation explicite du texte affiché, version du
  contrat, journal d'audit immuable. Le tout rattaché à la location.
- **Valeur juridique** : au Québec, la *Loi concernant le cadre juridique des technologies de l'information* admet la
  signature électronique si l'identité et l'intégrité du document peuvent être démontrées. Une simple case à cocher ne
  l'établit pas forcément : à valider avec un avocat avant d'utiliser le mot « signature » dans l'interface; sinon
  parler d'« acceptation ».
- **Hors portée de cette phase** : aucun fournisseur de signature (DocuSign, etc.) n'est intégré.

## Conséquences et limites
- Le courriel de confirmation au demandeur n'est pas envoyé (courriel sortant non éprouvé) : le lien de suivi s'affiche
  à l'écran et doit être conservé.
- Les demandes du portail n'entrent pas encore automatiquement dans l'extraction par IA.
- Le portail ne gère ni compte client, ni historique des demandes d'une même personne.
