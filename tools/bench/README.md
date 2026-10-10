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

## Essais de bout en bout de l'assistant (IA)

Sans clé réelle : `tools/bench/fake_gemini.py` simule l'API « generateContent » de Gemini **en validant la requête comme l'API réelle**
(types en majuscules, aucun `parameters` vide, rôles qui alternent…) et suit des scénarios qui utilisent les vrais résultats des outils.

```bash
docker cp tools/bench/fake_gemini.py fb:/tmp/ && docker exec -u frappe -d fb python3 /tmp/fake_gemini.py 9911 fake-gemini-key
bench --site cortex.localhost set-config cortex_ai_gemini_base_url http://127.0.0.1:9911/v1beta   # ESSAIS SEULEMENT
bench --site cortex.localhost set-config cortex_ai_actions 1
# Cortex AI Settings : clé « fake-gemini-key », modèle gemini-3.8-flash (script /tmp/aiconf.py du handoff)
docker exec -u frappe -d fb bash -lc 'cd /home/frappe/frappe-bench && bench --site cortex.localhost serve --port 8000 --noreload'
cd tools/ui-harness && npm install && node e2e-ai.mjs      # 27 vérifications dans le vrai Desk (Chromium)
```
Après un changement de code Python : **redémarrer le conteneur** (`docker restart fb`) puis relancer le faux serveur et `bench serve` : le serveur de
développement garde l'ancien code en mémoire (et `pkill` n'existe pas dans l'image).
Le serveur Docker ne démarre pas tout seul : `dockerd --iptables=false --ip-masq=false --bridge=none &`, puis `docker start mdb rds fb`.
