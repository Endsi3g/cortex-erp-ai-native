# Vrai bench ERPNext dans le bac à sable (Docker)

Pourquoi : tout ce qui est livré doit tourner sur un vrai Desk, pas seulement dans des tests « sans Frappe ». Ce montage a été
fait le 2026-10-10 (voir « Phase 12 » du handoff). **Les chemins `/tmp/...` sont ceux de cette session** : adaptez-les.

1. **Docker** : `dockerd --iptables=false --ip-masq=false --bridge=none &` (le démon n'est pas lancé par défaut). `github.com` est refusé
   par le proxy et Docker Hub direct renvoie 429 : tirer les images par le miroir de Google :
   `docker pull mirror.gcr.io/library/mariadb:10.6 mirror.gcr.io/library/redis:7 mirror.gcr.io/frappe/erpnext:v15`.
2. **Conteneurs** (réseau `host`) : `mdb` (MariaDB, mot de passe root `root`), `rds` (Redis), `fb` (`frappe/erpnext:v15`, `--user root --entrypoint sleep … infinity`).
3. **Config commune** : `bench set-config -g db_host 127.0.0.1`, `redis_cache|redis_queue|redis_socketio redis://127.0.0.1:6379`, `developer_mode 1`.
4. **Application** : `docker cp apps/cortex_rental fb:/home/frappe/frappe-bench/apps/`; `chown -R frappe`; copier `/root/.ccr/ca-bundle.crt` dans le conteneur;
   `PIP_CERT=/tmp/ca-bundle.crt ./env/bin/pip install -e apps/cortex_rental pytest`; ajouter `cortex_rental` à `sites/apps.txt`.
5. **Site** : `rebuild_site.sh` (supprime et recrée `cortex.localhost`, exécute l'assistant de configuration avec `setup_args.json`, installe Cortex, migre).
6. **Synchroniser le code** après une modification : `sync.sh` (copie sans `__pycache__`), puis
   `bench --site cortex.localhost run-tests --app cortex_rental [--module cortex_rental.tests.<module>]`.
7. **JS (`bench build`)** : Node est dans `/home/frappe/.nvm/versions/node/v22.23.3/bin` (à mettre dans le PATH; un shell de connexion le retire).
