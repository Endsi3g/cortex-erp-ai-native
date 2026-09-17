frappe.pages["cortex-supervision"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Supervision IA & Approbations",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_supervision(wrapper));
	}
};

frappe.pages["cortex-supervision"].on_page_show = function (wrapper) {
	load_cortex_supervision(wrapper);
};

async function load_cortex_supervision(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_supervision.bundle.js");
	frappe.cortex_supervision_app = frappe.ui.setup_cortex_supervision($parent.get(0));
}
