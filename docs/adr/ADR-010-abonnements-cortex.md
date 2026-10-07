# ADR-010 — Abonnements Cortex (Stripe)

**Statut :** codé et testé par événements simulés (v0.13.0); **désactivé par défaut; jamais éprouvé avec un vrai compte Stripe.**
**Date :** 2026-10-07

## Contexte
Phase 7 du plan de livraison : facturer l'usage de Cortex par société (prix de base demandé : 1 000 $ par mois),
émettre les factures automatiquement, puis vendre des modules et des niveaux d'IA par société, sans mélanger
l'abonnement à Cortex et les paiements de location que les sociétés encaissent de leurs clients.

## Décisions
1. **Deux Stripe distincts.** Abonnement Cortex = compte Stripe de la **plateforme** (*Cortex Subscription Settings*,
   réservé à *System Manager*). Acompte de location = clé Stripe de **chaque société** (ADR-007). Deux webhooks
   (`subscriptions.subscription_webhook` et `quote_share.stripe_webhook`), deux secrets de signature.
2. **Désactivé par défaut, sans effet tant qu'il l'est.** Facturation éteinte : aucune restriction, aucun frais.
3. **Aucun prix supposé.** L'activation est refusée par le serveur tant que manquent : clé secrète, secret du webhook,
   identifiant de prix Stripe du plan de base, **case « prix de base confirmé par un humain »**; chaque option offerte
   exige son identifiant `price_…` et sa confirmation. Les prix vivent dans Stripe (objets *Price*); Cortex n'envoie
   jamais un montant : Checkout reçoit seulement des identifiants de prix.
4. **Les droits viennent de Stripe, via le webhook signé.** Le navigateur n'écrit jamais l'état. Chaque événement est
   enregistré (*Cortex Stripe Event*) et traité **une fois**; un événement plus ancien que le dernier appliqué est
   ignoré (Stripe ne garantit pas l'ordre). Modules et niveaux d'IA acquis = prix de l'abonnement reconnus dans le
   catalogue. Un prix inconnu ne donne aucun droit.
5. **Application côté serveur.** Niveaux d'IA : `resolve_tier` refuse un niveau non acquis et `chat.status` le montre
   « Non inclus ». Module `portal` : un portail non acquis répond comme inexistant. Ajout d'un module = une clé dans
   `MODULES` et un appel `allows_module`.
6. **Retard de paiement :** l'accès reste pendant que Stripe relance (état « Paiement en retard »), puis Stripe annule
   et l'accès tombe. Facturation par Stripe (mode abonnement, prélèvement automatique, factures émises par Stripe).
7. **Sociétés exemptées** (liste dans les réglages) : démonstration, partenaires, clients existants à ménager; sans
   elles, activer la facturation retirerait l'accès aux sociétés sans abonnement.
8. **Propriétaire seulement** : état, achat (Checkout) et gestion (portail Stripe) exigent le droit de gérer l'équipe.

## À configurer par une personne avant l'activation (rien de ceci n'est supposé)
- Créer dans Stripe : un produit/prix mensuel de base (1 000 $ est le prix demandé, **à confirmer**, devise CAD ou USD),
  puis un prix par option offerte; saisir les identifiants `price_…` et cocher les confirmations.
- Ajouter l'adresse du webhook dans Stripe et saisir son secret; événements à envoyer :
  `checkout.session.completed`, `customer.subscription.created|updated|deleted`, `invoice.paid`,
  `invoice.payment_failed`.
- Décider : enveloppe d'IA incluse (0 = aucune), prix et existence des options, traitement des dépassements d'IA
  (**non automatisé**), taxes (Stripe Tax ou saisie), sociétés exemptées.

## Limites
- Non essayé avec Stripe : formats d'API et champs (`current_period_end` sur l'abonnement ou sur ses lignes selon la
  version d'API) gérés des deux façons mais à confirmer sur un compte de test.
- Pas de facturation des dépassements d'IA, ni d'essai gratuit configurable, ni de rabais.
- Le coût réel de l'IA consommée n'est pas refacturé : le budget mensuel par société existe déjà (ADR-006).
