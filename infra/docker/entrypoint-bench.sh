#!/usr/bin/env bash
set -e

BENCH_DIR="/home/frappe/frappe-bench"
SITES_DIR="${BENCH_DIR}/sites"

# Fix permissions on sites directory if mounted volume is owned by root
sudo chown -R frappe:frappe "${SITES_DIR}" 2>/dev/null || true

mkdir -p "${SITES_DIR}" "${BENCH_DIR}/logs"

# 1. Initialize Common Site Config with default_site & root password
cat <<EOF > "${SITES_DIR}/common_site_config.json"
{
  "db_host": "${DB_HOST:-mariadb}",
  "db_port": ${DB_PORT:-3306},
  "db_type": "${DB_TYPE:-mariadb}",
  "root_password": "${DB_ROOT_PASSWORD:-cortex_root_dev_password}",
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

# 2. Ensure ERPNext is acquired
if [ ! -d "${BENCH_DIR}/apps/erpnext" ]; then
    echo "Downloading ERPNext version-15..."
    bench get-app erpnext --branch version-15 || true
fi

# Write clean apps.txt
cat <<EOF > "${SITES_DIR}/apps.txt"
frappe
erpnext
cortex_rental
EOF

# 3. Install cortex_rental in editable mode
if [ -d "${BENCH_DIR}/apps/cortex_rental" ]; then
    echo "Installing cortex_rental in editable mode..."
    if [ -f "${BENCH_DIR}/env/bin/pip" ]; then
        "${BENCH_DIR}/env/bin/pip" install -e "${BENCH_DIR}/apps/cortex_rental" --no-deps || true
    else
        pip install -e "${BENCH_DIR}/apps/cortex_rental" --no-deps || true
    fi
fi

# 4. Create or Migrate default site cortex.local
SITE_DIR="${SITES_DIR}/cortex.local"

if [ ! -f "${SITE_DIR}/site_config.json" ]; then
    echo "Initializing new site cortex.local..."
    bench new-site cortex.local \
        --admin-password "${ADMIN_PASSWORD:-admin}" \
        --mariadb-root-password "${DB_ROOT_PASSWORD:-cortex_root_dev_password}" \
        --install-app erpnext \
        --install-app cortex_rental || true
    echo "cortex.local" > "${SITES_DIR}/currentsite.txt"
else
    echo "Existing site cortex.local found. Ensuring apps are installed & migrating..."
    bench --site cortex.local install-app erpnext 2>/dev/null || true
    bench --site cortex.local install-app cortex_rental 2>/dev/null || true
    bench --site cortex.local migrate || true
fi

# Ensure localhost alias exists
if [ ! -d "${SITES_DIR}/localhost" ] && [ ! -L "${SITES_DIR}/localhost" ]; then
    ln -sf cortex.local "${SITES_DIR}/localhost" || true
fi

# 5. Build Vue 3 bundles
if [ -d "${BENCH_DIR}/apps/cortex_rental" ]; then
    echo "Building cortex_rental frontend bundles..."
    bench build --app cortex_rental || true
fi

# 6. Ensure Procfile exists
cat <<EOF > "${BENCH_DIR}/Procfile"
web: bench serve --port 8000
worker_short: bench worker --queue short
worker_long: bench worker --queue long
worker_default: bench worker --queue default
schedule: bench schedule
EOF

echo "Frappe Bench ready. Starting bench services..."
exec "$@"
