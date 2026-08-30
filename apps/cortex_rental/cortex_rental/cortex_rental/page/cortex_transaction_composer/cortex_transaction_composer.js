// Same verified Vue-in-a-Desk-Page pattern as cortex_availability.js /
// cortex_assistant.js — see docs.frappe.io/framework/using-vue-inside-a-desk-page.

frappe.pages["cortex-transaction-composer"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Nouvelle transaction",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_transaction_composer(wrapper));
	}
};

frappe.pages["cortex-transaction-composer"].on_page_show = function (wrapper) {
	load_cortex_transaction_composer(wrapper);
};

async function load_cortex_transaction_composer(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_transaction_composer.bundle.js");
	frappe.cortex_transaction_composer_app = frappe.ui.setup_cortex_transaction_composer($parent.get(0));
}
