#!/bin/sh
# Mise à jour d'un banc de développement : migrate (obligatoire quand un champ ou un état est ajouté) → build → clear-cache.
# Ordre important : le « boot » de chaque personne et la table des bundles sont en cache; sans clear-cache, le navigateur peut
# recevoir l'ancien JS. Usage : sh tools/bench/upgrade.sh [site]   (défaut : cortex.localhost)
set -e
SITE="${1:-cortex.localhost}"
cd /home/user/cortex-erp-ai-native
sh tools/bench/sync.sh
docker exec -u frappe fb bash -lc "export PATH=/home/frappe/.nvm/versions/node/v22.23.3/bin:\$PATH; cd /home/frappe/frappe-bench && bench --site $SITE migrate && bench build && bench --site $SITE clear-cache"
echo "Mise à jour faite. Redémarrez 'bench serve' (et le conteneur si du Python a changé)."
