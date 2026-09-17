frappe.pages["cortex-customers"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Clients & Risque Assurance",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_customers(wrapper));
	}
};

frappe.pages["cortex-customers"].on_page_show = function (wrapper) {
	load_cortex_customers(wrapper);
};

async function load_cortex_customers(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_customers.bundle.js");
	frappe.cortex_customers_app = frappe.ui.setup_cortex_customers($parent.get(0));
}
