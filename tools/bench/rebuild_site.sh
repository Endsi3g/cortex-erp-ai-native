set -e
cd /home/frappe/frappe-bench
bench drop-site cortex.localhost --force --no-backup --root-password root 2>&1 | tail -1
bench new-site cortex.localhost --mariadb-root-password root --admin-password admin --install-app erpnext --set-default 2>&1 | tr '\r' '\n' | grep -v "Updating DocTypes" | tail -2
bench --site cortex.localhost set-config developer_mode 1
bench --site cortex.localhost set-config allow_tests true
bench --site cortex.localhost execute frappe.db.set_single_value --args '["System Settings","setup_complete",0]'
bench --site cortex.localhost execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete --kwargs "{\"args\": $(cat /tmp/setup_args.json)}" 2>&1 | tr '\r' '\n' | tail -3
bench --site cortex.localhost install-app cortex_rental 2>&1 | tr '\r' '\n' | grep -v "Updating DocTypes" | tail -3
bench --site cortex.localhost migrate 2>&1 | tr '\r' '\n' | grep -v "Updating DocTypes" | tail -3
echo REBUILD_DONE
