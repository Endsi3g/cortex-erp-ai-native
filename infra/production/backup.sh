#!/usr/bin/env bash
# Sauvegarde quotidienne d'un site Cortex : base de données + fichiers, chiffrées, avec rétention.
#   BENCH=/home/frappe/frappe-bench SITE=app.exemple.ca BACKUP_DIR=/var/backups/cortex \
#   GPG_RECIPIENT=ops@exemple.ca RETENTION_DAYS=30 ./backup.sh
# À planifier avec cron (ex. 02:30) ; copier ensuite BACKUP_DIR hors du serveur (stockage objet, autre région).
# La clé de chiffrement du site (encryption_key de site_config.json) se sauvegarde SÉPARÉMENT : sans elle, les secrets
# stockés (clés d'API, Stripe) sont illisibles après une restauration.
set -euo pipefail
BENCH="${BENCH:-/home/frappe/frappe-bench}"
SITE="${SITE:?définir SITE}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cortex}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
cd "$BENCH"
bench --site "$SITE" backup --with-files >/dev/null
SRC="$BENCH/sites/$SITE/private/backups"
LATEST="$(ls -1t "$SRC" | head -n 4)"
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"
for f in $LATEST; do cp "$SRC/$f" "$DEST/"; done

if [[ -n "${GPG_RECIPIENT:-}" ]]; then
    for f in "$DEST"/*; do
        gpg --batch --yes --trust-model always -r "$GPG_RECIPIENT" -o "$f.gpg" -e "$f" && rm -f "$f"
    done
fi
sha256sum "$DEST"/* > "$DEST/SHA256SUMS"
find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +
echo "Sauvegarde terminée : $DEST ($(du -sh "$DEST" | cut -f1))"
