# Connexion, création de compte et mise en route

Ce document décrit ce qui est réellement implémenté dans `apps/cortex_rental` pour l'accès des entreprises clientes. Le design de la page (deux panneaux, adaptatif, clair/sombre) est décrit dans `.claude/skills/cortex-login/SKILL.md`.

## Parcours

1. **Demande d'accès** (`/login#signup`, formulaire en 2 étapes) → `cortex_rental.api.v1.access.request_access`.
   - Étape 1 : personne et courriel professionnel. Étape 2 : entreprise et rôle. Le brouillon reste en mémoire si on revient en arrière.
   - Protections : champ piège (honeypot), limite de 8 demandes/heure, blocage optionnel des courriels grand public, liste de domaines autorisés.
2. **Vérification du courriel** : lien à usage unique (`/cortex-verify?token=…`), jeton stocké haché (sha256), expiration configurable (48 h par défaut), renvoi limité (60 s de délai, 5 renvois).
3. **Approbation**
   - `Manual` (défaut) : un administrateur approuve ou refuse depuis le DocType *Cortex Signup Request* (boutons Approuver / Refuser / Renvoyer).
   - `Automatic after email verification` : provisionnement immédiat après vérification.
4. **Provisionnement** (`services/tenant_provisioning.py`) : Company, utilisateur (jamais `System Manager`), rôles du propriétaire, *User Permission* sur la Company, règle de tarification par défaut (7 jours civils = 3 jours facturables), fiche *Cortex Onboarding*.
5. **Mot de passe** : courriel de bienvenue → `/update-password?key=…` (politique de robustesse de Frappe, limitation de débit).
6. **Connexion** → arrivée sur l'**Accueil Cortex** (`/app/cortex-home`, `public/js/cortex_desk.js` + `frappe.boot.cortex_home`). Tant que la mise en route n'est pas terminée, l'accueil affiche une carte « Terminez la mise en route » qui mène au workspace *Cortex Rental*.
7. **Mise en route** : bloc d'intégration natif (*Module Onboarding* « Bienvenue dans Cortex », six étapes : profil de l'entreprise, équipe, matériel, règle tarifaire, première location, assistant). Les écritures passent par des formulaires ERPNext et `api/v1/onboarding.py` (seul le propriétaire écrit).

## Mot de passe oublié

Flux Frappe (`reset_password`) : réponse identique que le compte existe ou non, limitation de débit, délai de 60 s avant renvoi, lien à usage unique vers `/update-password`. La page affiche « Vérifiez votre courriel » et permet de corriger l'adresse.

## Google et GitHub

Les boutons n'apparaissent que si un **Social Login Key** est activé avec un identifiant et un secret. Rien n'est configuré par défaut.

1. Créer l'application OAuth chez le fournisseur.
   - URI de redirection Google : `https://<site>/api/method/frappe.integrations.oauth2_logins.login_via_google`
   - URI de redirection GitHub : `https://<site>/api/method/frappe.integrations.oauth2_logins.login_via_github`
2. Desk → *Social Login Key* → `Google` / `GitHub` : renseigner *Client ID* et *Client Secret*, cocher *Enable Social Login*.
3. Laisser *Sign ups* à `Deny` : une connexion sociale ne sert qu'à un utilisateur déjà provisionné (une demande d'accès reste obligatoire).

Apple n'est pas implémenté.

## Courriel

Il faut un *Email Account* sortant par défaut et un worker/scheduler actif. Sans compte sortant, l'envoi échoue sans bloquer la demande : la fiche affiche `mail_status`, et l'administrateur obtient un lien de mot de passe à usage unique à transmettre manuellement.

## Image de marque

Le patch `apply_cortex_branding` règle le nom d'application, le logo, la favicon et retire le pied de page « Powered by ». Les gabarits de courriel sont sous `templates/emails/`.

## Destination après connexion

Plus d'application autonome : Cortex vit dans le Desk ERPNext. Le hook `boot_session` (lecture seule) place `cortex_home` dans `frappe.boot` ; `public/js/cortex_desk.js` envoie une personne qui arrive sur `/app` ou `/app/home` vers `/app/cortex-home`, une seule fois par chargement. Le patch `clear_default_app` retire l'ancien réglage `default_app`. Les pages `/login`, `/cortex-verify` et `/update-password` (Jinja) sont la seule version des écrans d'accès : un changement de texte, d'espacement ou de couleur se fait dans `public/css/cortex-login.css` + `www/login.html`.

## Administration de l'entreprise

Après la mise en route, le propriétaire gère son entreprise depuis le workspace *Administration* (règles tarifaires, équipe et rôles, import). Les règles vivent dans `services/administration.py` : profils de rôles sans droit d'administrateur système, propriétaire non modifiable, on ne peut pas se désactiver soi-même, une seule règle active par durée. Chaque changement est écrit au journal d'audit.

## Limites connues

- Français seulement : `translations/fr.csv` + patch `set_french_default` (langue du site et des utilisateurs sans choix explicite).
- Google/GitHub exigent de vraies clés OAuth.
- Le thème et le mode sombre de Desk lui-même ne sont pas modifiés ; seules les pages d'authentification suivent `prefers-color-scheme`.
- Après un changement de DocType (`mail_status`, etc.), exécuter `bench migrate`.
