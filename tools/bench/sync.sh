#!/bin/sh
# Copie l'application dans le conteneur du bench (sans __pycache__) et lance la commande donnée.
cd /home/user/cortex-erp-ai-native
tar --exclude='__pycache__' --exclude='*.egg-info' -cf - apps/cortex_rental/cortex_rental | docker exec -i -u frappe fb tar -xf - -C /tmp/sync_src 2>/dev/null || { docker exec -u root fb mkdir -p /tmp/sync_src && docker exec -u root fb chmod 777 /tmp/sync_src; tar --exclude='__pycache__' --exclude='*.egg-info' -cf - apps/cortex_rental/cortex_rental | docker exec -i -u frappe fb tar -xf - -C /tmp/sync_src; }
docker exec -u frappe fb bash -c 'cp -r /tmp/sync_src/apps/cortex_rental/cortex_rental/. /home/frappe/frappe-bench/apps/cortex_rental/cortex_rental/'
