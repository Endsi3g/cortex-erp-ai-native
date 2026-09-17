frappe.pages["cortex-fleet"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Parc Matériel & Maintenance",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_fleet(wrapper));
	}
};

frappe.pages["cortex-fleet"].on_page_show = function (wrapper) {
	load_cortex_fleet(wrapper);
};

async function load_cortex_fleet(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_fleet.bundle.js");
	frappe.cortex_fleet_app = frappe.ui.setup_cortex_fleet($parent.get(0));
}
