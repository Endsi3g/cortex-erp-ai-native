# Courriel sortant avec Amazon SES

Décision (2026-10-05) : **Amazon SES** pour les courriels transactionnels (devis envoyés aux clients, invitations, vérifications).
Prix : 0,10 $ par 1 000 courriels (à la carte); voir `docs/architecture/COUTS_API.md`.

Frappe envoie par SMTP : il suffit de configurer un *Compte courriel sortant* avec les identifiants SMTP de SES. Aucun code à changer.

## Mise en place (une fois par environnement)

1. **Région** : `ca-central-1` (Montréal) pour garder les données au Canada.
2. **Domaine** : dans SES, vérifier le domaine d'envoi (ex. `devis.exemple.ca`) et publier **DKIM**, **SPF** et **DMARC** dans le DNS. Sans cela, les devis finissent dans les pourriels.
3. **Sortir du mode test (sandbox)** : demander l'accès production à SES (sinon l'envoi est limité aux adresses vérifiées).
4. **Identifiants SMTP** : créer des identifiants SMTP SES (pas la clé d'accès AWS) : serveur `email-smtp.ca-central-1.amazonaws.com`, port 587, TLS.
5. Dans Frappe : *Compte courriel* → nouveau compte sortant : adresse d'envoi du domaine vérifié, serveur SMTP ci-dessus, utilisateur et mot de passe SMTP, « Utiliser TLS » coché, « Compte d'envoi par défaut » coché.
6. Tester : depuis une location au statut Devis, « Partager avec le client » → Courriel. L'état d'envoi s'affiche sur le lien de devis (Envoyé / Échec).

## Bonnes pratiques

- Une adresse d'envoi par environnement (production, essais) pour ne pas mélanger la réputation.
- Surveiller les rebonds et plaintes dans SES; un taux de plaintes élevé suspend le compte.
- L'adresse « répondre à » du devis est celle de la personne de l'équipe qui l'envoie : le client lui répond directement.

## État actuel

Le banc de développement n'a pas de messagerie sortante : l'envoi échoue proprement (état « Échec ») et le lien reste à copier à la main. **Aucun envoi réel n'a été testé** : à valider avec un compte SES.
