# Déployer Cortex en production

Guide d'exploitation pour mettre Cortex (application Frappe `cortex_rental` sur ERPNext 15) en service, le surveiller,
le sauvegarder et revenir en arrière. Tout ce qui est décrit ici a un fichier correspondant dans `infra/production/` ou
un outil dans `apps/cortex_rental/cortex_rental/ops/`.

> **Avant tout :** lancez `bench --site <site> execute cortex_rental.ops.predeploy.run`. Il refuse (échec) la mise en
> production tant qu'un point bloquant subsiste : mode développeur, mot de passe `Administrator` par défaut, comptes de
> démonstration actifs, correctifs non appliqués, etc.

## 1. Architecture cible

```
Internet ──TLS──► nginx (infra/production/nginx-cortex.conf)
                    ├─ /assets ........ fichiers construits (cache long)
                    ├─ /socket.io ..... serveur de sockets (présence, notifications en direct)
                    └─ tout le reste .. gunicorn (4 processus × 2 fils) ─► Frappe/ERPNext + cortex_rental
                                           │
        workers (short, long) ◄── Redis (cache + files) ◄── planificateur (bench schedule)
                                           │
                                       MariaDB 10.6+ (utf8mb4)
```

Processus supervisés (voir `infra/production/supervisor-cortex.conf`) : `cortex-web`, `cortex-worker-short`,
`cortex-worker-long`, `cortex-scheduler`, `cortex-socketio`. **Le planificateur est indispensable** : il exécute les
rappels horaires, l'expiration des retenues de devis, les sauvegardes et les journaux.

Dimensionnement de départ (≈ 40 utilisateurs simultanés) : 4 cœurs, 8 Go de RAM, disque SSD 50 Go. Voir § 7 pour les
mesures de charge.

## 2. Préparer le serveur

1. Debian/Ubuntu récent, utilisateur `frappe`, Python 3.11, Node 18+, MariaDB 10.6+, Redis, nginx, supervisor, `wkhtmltopdf`.
2. MariaDB : `character-set-server=utf8mb4`, `collation-server=utf8mb4_unicode_ci`, `innodb_buffer_pool_size` ≈ 50 % de la RAM.
3. Pare-feu : seuls 80 et 443 sont ouverts. MariaDB, Redis (13000/11000) et gunicorn (8000) écoutent **uniquement sur 127.0.0.1**.
4. Un nom de domaine et un certificat TLS (Let's Encrypt : `certbot --nginx`).

## 3. Installer

```bash
bench init --frappe-branch version-15 frappe-bench && cd frappe-bench
bench get-app erpnext --branch version-15
bench get-app https://github.com/Endsi3g/cortex-erp-ai-native      # ou le dépôt privé
bench new-site app.exemple.ca --admin-password '<mot de passe fort>' --install-app erpnext
bench --site app.exemple.ca install-app cortex_rental
bench --site app.exemple.ca set-config developer_mode 0
bench --site app.exemple.ca set-config host_name https://app.exemple.ca
bench --site app.exemple.ca set-config max_file_size 10485760
bench build --app cortex_rental
```

Copier `infra/production/site_config.production.json.example` comme référence des clés à définir (ne jamais y laisser
`cortex_rate_limit_factor`). Puis `bench setup production frappe` (ou installer les fichiers `infra/production/*`
à la main), et `sudo supervisorctl reload`.

### Configuration à faire dans l'application (par un System Manager)

| Quoi | Où | Pourquoi |
| --- | --- | --- |
| Courriel sortant par défaut | *Email Account* | Invitations, vérification d'adresse, rappels, devis |
| Clé de l'IA | *Cortex AI Settings* | Sans clé, l'assistant ne répond pas |
| Clés Stripe de chaque société | *Cortex Finance Settings* (par société) | Acompte en ligne; sans clés : instructions manuelles |
| Webhook Stripe | `https://app.exemple.ca/api/method/cortex_rental.api.v1.quote_share.stripe_webhook` | Confirmation signée des paiements |
| Politique de mot de passe, verrouillage après échecs, 2FA | *System Settings* | `predeploy` les signale |
| Rôles des premiers utilisateurs | Inscription entreprise ou *User* | Le propriétaire finit l'assistant de configuration |

### Mesure d'usage (PostHog)

Éteinte par défaut. Pour l'allumer, créer un projet PostHog puis, sur le serveur :

```bash
bench --site app.exemple.ca set-config posthog_key phc_…          # clé de projet (publique par conception)
bench --site app.exemple.ca set-config posthog_host https://us.i.posthog.com   # ou https://eu.i.posthog.com
bench --site app.exemple.ca clear-cache
```

- Capturé : clics, pages vues, erreurs JavaScript, performances, enregistrements de session. Rien d'envoyé sans clé valide.
- Personne : empreinte HMAC calculée avec `encryption_key` du site (jamais le courriel ni le nom). Groupe : la société.
- Enregistrements de session : champs de saisie et texte des données d'affaires (listes, tableaux, formulaires, messages de l'assistant) masqués.
  `posthog_capture_pii 1` lève ce masque : à décider avec le client pilote, par écrit (Loi 25), pas par défaut.
- `posthog_disabled 1` éteint la mesure sans retirer la clé. « Ne pas me suivre » du navigateur est respecté.
- À faire avant le pilote : informer les utilisatrices et utilisateurs du client (avis de confidentialité) ; il n'y a pas encore de réglage individuel dans Mon compte.

## 4. Vérifier avant d'ouvrir

```bash
bench --site app.exemple.ca execute cortex_rental.ops.predeploy.run          # 0 échec attendu
curl -s https://app.exemple.ca/api/method/cortex_rental.api.v1.health.ready  # {"status":"ok",...}
```

`health.health` répond « le processus est vivant » (pour l'orchestrateur); `health.ready` vérifie la base, le cache, les
migrations et le planificateur (HTTP 503 si la base ou le cache sont inutilisables, `degraded` si seul le
planificateur ou les migrations posent problème). Aucune version ni nom de serveur n'est exposé.

Surveiller : `ready` toutes les minutes (alerte si ≠ `ok` pendant 3 minutes), le journal d'erreurs *Error Log*, l'espace
disque, la taille de la file Redis `short`/`long`, le nombre d'erreurs 5xx (nginx) et de 429 (limites de débit).

## 5. Mettre à jour (sans interruption longue)

```bash
cd frappe-bench
bench --site app.exemple.ca backup --with-files          # toujours avant
git -C apps/cortex_rental pull
bench --site app.exemple.ca migrate                      # applique les correctifs (patches.txt)
bench build --app cortex_rental
sudo supervisorctl restart cortex-web cortex-worker-short cortex-worker-long cortex-scheduler
bench --site app.exemple.ca execute cortex_rental.ops.predeploy.run
```

Les correctifs sont idempotents et se rejouent sans risque. Une fenêtre de maintenance (`bench --site … set-config
maintenance_mode 1`) n'est nécessaire que si un correctif touche beaucoup de lignes.

## 6. Sauvegarder et restaurer

- **Quotidien** : `infra/production/backup.sh` (base + fichiers, chiffrement GPG optionnel, rétention 30 jours, sommes
  de contrôle). Planifier avec cron à 02:30 et **copier hors du serveur** (autre région).
- **La clé `encryption_key` du site se sauvegarde séparément** : sans elle, les secrets chiffrés (clés d'API, Stripe) sont
  illisibles après restauration.
- **Restaurer** : `bench --site app.exemple.ca restore <base.sql.gz> --with-public-files <fichiers.tar> --with-private-files <privés.tar>`
  puis `bench --site app.exemple.ca migrate`. **Essai fait le 2026-10-06** : sauvegarde de `cortex.local` par `backup.sh` (somme de contrôle vérifiée), restauration dans un site neuf, 592 locations de part et d'autre. **Refaites un essai de restauration trimestriel** sur un serveur à part : une
  sauvegarde qu'on n'a jamais restaurée n'est pas une sauvegarde.

## 7. Charge et limites mesurées

Mesures du 2026-10-06 (détail dans `docs/audit/STRESS_TEST_2026-10-06.md`) sur 4 cœurs avec gunicorn 4×2 : 65 requêtes/s
à 40 utilisateurs simultanés sans temps de réflexion (0 échec, p95 1,2 s), 4 courses de concurrence correctes, 0 erreur
5xx sur 6 210 requêtes hostiles, 0 fuite entre sociétés sur 101 contrôles, intégrité comptable parfaite sur 91 jours simulés.

Limites de débit en place (réglables dans `services/defense.py` et les décorateurs) :

| Où | Limite |
| --- | --- |
| Toute requête d'API, par personne | 900 / minute |
| Visiteur (sans compte), par adresse IP | 120 / minute |
| Demande d'accès / renvoi de vérification | 8 et 10 / heure |
| Portail de devis : réponse / paiement | 120 et 20 / heure |
| Actions sensibles (invitation, logo, photo, fin de configuration, déconnexions…) | 20 à 120 / heure et par personne |
| Connexion (nginx) | 10 / minute et par adresse IP |

## 8. Sécurité : ce qui est en place et ce qui reste à votre charge

**En place** : en-têtes `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` et HSTS (derrière HTTPS);
vérification des vrais octets des images téléversées (un fichier renommé n'est pas accepté); SVG refusé; toutes les
requêtes externes ont un délai d'attente; webhook Stripe signé et plafonné à 1 Mo; erreurs de saisie en 417 clair, jamais
de trace d'exécution; isolation entre sociétés vérifiée par HTTP (101 contrôles, aucune fuite); journal d'audit immuable.

**À votre charge** : TLS et renouvellement des certificats; mises à jour du système et de Frappe/ERPNext; surveillance et
alertes; sauvegardes hors site et essai de restauration; 2FA pour les propriétaires (recommandé); revue périodique des
comptes actifs; politique de conservation des journaux; une revue de sécurité externe avant d'accueillir des clients
payants (ce projet n'a pas fait l'objet d'un test d'intrusion indépendant).

## 9. Retour arrière

1. `sudo supervisorctl stop cortex-web cortex-worker-short cortex-worker-long cortex-scheduler`
2. `git -C apps/cortex_rental checkout <version précédente>` puis `bench build --app cortex_rental`
3. Si un correctif de données a été appliqué : `bench --site … restore <sauvegarde d'avant la mise à jour>`
4. `sudo supervisorctl start …` puis `predeploy.run` et `health.ready`.

## 10. Dépannage rapide

| Symptôme | Cause probable | Action |
| --- | --- | --- |
| `ready` → `degraded`, `scheduler:false` | Planificateur arrêté ou désactivé | `supervisorctl start cortex-scheduler`; `bench --site … enable-scheduler` |
| `ready` → `migrations:false` | Mise à jour sans `migrate` | `bench --site … migrate` |
| 429 chez des utilisateurs normaux | Limite trop basse ou boucle côté client | Journal nginx/Redis; ajuster `USER_PER_MINUTE` |
| Courriels non reçus | Pas de compte sortant ou SES hors bac à sable | `docs/ops/COURRIEL_SES.md` |
| Assistant muet | Clé IA absente ou plafond mensuel atteint | *Cortex AI Settings*, rapport *Utilisation IA* |
