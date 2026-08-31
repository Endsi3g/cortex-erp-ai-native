// Same verified Vue-in-a-Desk-Page pattern as cortex_availability.js /
// cortex_transaction_composer.js — see docs.frappe.io/framework/using-vue-inside-a-desk-page.

frappe.pages["cortex-checkin"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Check-in & Retours",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_checkin(wrapper));
	}
};

frappe.pages["cortex-checkin"].on_page_show = function (wrapper) {
	load_cortex_checkin(wrapper);
};

async function load_cortex_checkin(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: 0 });

	await frappe.require("cortex_checkin.bundle.js");
	frappe.cortex_checkin_app = frappe.ui.setup_cortex_checkin($parent.get(0));
}
