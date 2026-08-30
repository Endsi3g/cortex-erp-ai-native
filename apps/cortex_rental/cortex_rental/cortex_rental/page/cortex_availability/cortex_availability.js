// Controller for the /app/cortex-availability Desk Page. Follows the
// framework's documented "Using Vue in a Desk Page" pattern (Frappe
// bundles Vue itself; no separate npm/vite project needed for this
// page) — see docs.frappe.io/framework/using-vue-inside-a-desk-page.
// The actual UI lives in public/js/cortex_availability/, loaded as a
// .bundle.js so `bench build` picks it up like any other app asset.

frappe.pages["cortex-availability"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Disponibilité",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_availability(wrapper));
	}
};

frappe.pages["cortex-availability"].on_page_show = function (wrapper) {
	load_cortex_availability(wrapper);
};

async function load_cortex_availability(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_availability.bundle.js");
	frappe.cortex_availability_app = frappe.ui.setup_cortex_availability($parent.get(0));
}
