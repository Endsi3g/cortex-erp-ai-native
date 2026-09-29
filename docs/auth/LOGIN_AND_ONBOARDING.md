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
6. **Connexion** → redirection automatique vers `/app/cortex-company-setup` tant que la mise en route n'est pas terminée (`boot_session` + gestionnaire `startup` dans `cortex_host.js`, une fois par session).
7. **Mise en route** (`/app/cortex-company-setup`) : profil de l'entreprise, équipe (invitations avec préréglages de rôles), catalogue, règles de location. Seul le propriétaire peut écrire ; toute écriture passe par `api/v1/onboarding.py`.

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

## Application autonome `/cortex` (Vue 3 + frappe-ui)

- **Build et service** : `npm run build:spa` (dossier `public/frontend`) → `dist-spa/` et `www/cortex.html` ; `www/cortex.py` fournit `csrf_token` et `user`, `hooks.website_route_rules` renvoie tout `/cortex/<chemin>` vers cette page. En développement : `bench --site <site> set-config ignore_csrf 1` (site de développement seulement) puis `npm run dev` (le plugin frappe-ui proxifie `/api`, `/assets`, `/login`, `/app`).
- **Écrans d'accès Vue** : `/cortex/login`, `/cortex/forgot-password`, `/cortex/login-link`, `/cortex/request-access` (`src/features/auth`). Ils utilisent `Button` et `FormControl` de frappe-ui, les mêmes API que les pages Frappe (`login`, `reset_password`, `send_login_link`, `request_access`) et `cortex_rental.api.v1.access.login_options` (invité) pour les boutons Google/GitHub et le lien par courriel. Après une connexion réussie la page est rechargée (nouveau jeton CSRF).
- **Destination après connexion** : hook `add_to_apps_screen` + `System Settings.default_app = cortex_rental` (patch `set_default_app`, sans écraser un choix existant). Le contexte de session indique `onboarding.needed` : un propriétaire d'entreprise est dirigé une fois par session vers `/cortex/company-setup`.
- **Deux versions du login** : `/login` (Jinja, servi aussi aux personnes du Desk et aux liens de courriel) et `/cortex/login` (Vue). Un changement de texte, d'espacement ou de couleur se fait dans les deux : `public/css/cortex-login.css` + `www/login.html` d'un côté, `src/features/auth/auth.css` + vues de l'autre.

## Limites connues

- Textes personnalisés en français seulement (`?lang=en` n'affecte que les chaînes de Frappe).
- Google/GitHub exigent de vraies clés OAuth.
- Le thème et le mode sombre de Desk lui-même ne sont pas modifiés ; seules les pages d'authentification suivent `prefers-color-scheme`.
- Les Pages Desk `cortex-*` existent encore à côté de `/cortex` (suppression à valider).
- La connexion à deux facteurs n'est pas gérée dans l'écran Vue : un lien renvoie vers `/login`.
- Après un changement de DocType (`mail_status`, etc.), exécuter `bench migrate`.
