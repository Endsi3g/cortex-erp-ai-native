#!/usr/bin/env bash
set -e

BENCH_DIR="/home/frappe/frappe-bench"
SITES_DIR="${BENCH_DIR}/sites"

# Fix permissions on sites directory if mounted volume is owned by root
sudo chown -R frappe:frappe "${SITES_DIR}" 2>/dev/null || true

mkdir -p "${SITES_DIR}" "${BENCH_DIR}/logs"

# 1. Initialize Common Site Config with default_site
cat <<EOF > "${SITES_DIR}/common_site_config.json"
{
  "db_host": "${DB_HOST:-mariadb}",
  "db_port": ${DB_PORT:-3306},
  "db_type": "${DB_TYPE:-mariadb}",
  "redis_cache": "${REDIS_CACHE:-redis://valkey:6379/0}",
  "redis_queue": "${REDIS_QUEUE:-redis://valkey:6379/1}",
  "redis_socketio": "redis://valkey:6379/2",
  "webserver_port": 8000,
  "socketio_port": 9000,
  "developer_mode": 1,
  "default_site": "cortex.local",
  "dns_multitenant": false
}
EOF

# 2. Write clean apps.txt
cat <<EOF > "${SITES_DIR}/apps.txt"
frappe
cortex_rental
EOF

# 3. Create default site cortex.local config if absent
SITE_DIR="${SITES_DIR}/cortex.local"
mkdir -p "${SITE_DIR}/logs" "${SITE_DIR}/public/files" "${SITE_DIR}/private/files"

if [ ! -f "${SITE_DIR}/site_config.json" ]; then
    echo "cortex.local" > "${SITES_DIR}/currentsite.txt"
    cat <<EOF > "${SITE_DIR}/site_config.json"
{
  "db_name": "${DB_DATABASE:-_cortex_dev}",
  "db_user": "${DB_USERNAME:-cortex_user}",
  "db_password": "${DB_PASSWORD:-cortex_local_dev_password_only}",
  "db_type": "${DB_TYPE:-mariadb}",
  "db_host": "${DB_HOST:-mariadb}",
  "db_port": ${DB_PORT:-3306},
  "developer_mode": 1
}
EOF
fi

# Ensure localhost alias exists
if [ ! -d "${SITES_DIR}/localhost" ] && [ ! -L "${SITES_DIR}/localhost" ]; then
    ln -sf cortex.local "${SITES_DIR}/localhost" || true
fi

# 4. Install cortex_rental in editable mode
if [ -d "${BENCH_DIR}/apps/cortex_rental" ]; then
    echo "Installing cortex_rental in editable mode..."
    if [ -f "${BENCH_DIR}/env/bin/pip" ]; then
        "${BENCH_DIR}/env/bin/pip" install -e "${BENCH_DIR}/apps/cortex_rental" --no-deps || true
    else
        pip install -e "${BENCH_DIR}/apps/cortex_rental" --no-deps || true
    fi
fi

# 5. Ensure Procfile exists
cat <<EOF > "${BENCH_DIR}/Procfile"
web: bench serve --port 8000
worker_short: bench worker --queue short
worker_long: bench worker --queue long
worker_default: bench worker --queue default
schedule: bench schedule
EOF

echo "Frappe Bench ready. Starting bench services..."
exec "$@"
