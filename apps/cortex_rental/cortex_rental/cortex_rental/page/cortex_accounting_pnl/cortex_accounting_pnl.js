// Controller for the /app/cortex-accounting-pnl Desk Page. Same
// "Vue in a Desk Page" pattern as every other Cortex screen (see
// cortex_availability.js) — no separate npm/vite project.

frappe.pages["cortex-accounting-pnl"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Profit and Loss Statement",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_accounting_pnl(wrapper));
	}
};

frappe.pages["cortex-accounting-pnl"].on_page_show = function (wrapper) {
	load_cortex_accounting_pnl(wrapper);
};

async function load_cortex_accounting_pnl(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_accounting_pnl.bundle.js");
	frappe.cortex_accounting_pnl_app = frappe.ui.setup_cortex_accounting_pnl($parent.get(0));
}
