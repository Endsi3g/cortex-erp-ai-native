// Controller for the detached /app/cortex-assistant Desk Page — hosts
// the same CortexCopilotPanel component the floating launcher uses
// (mode="docked"), per docs.frappe.io's documented Vue-in-a-Desk-Page
// pattern (see cortex_availability.js for the identical, already-
// verified structure this mirrors).

frappe.pages["cortex-assistant"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Cortex Assistant",
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_cortex_assistant(wrapper));
	}
};

frappe.pages["cortex-assistant"].on_page_show = function (wrapper) {
	load_cortex_assistant(wrapper);
};

async function load_cortex_assistant(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	$parent.css({ padding: "16px" });

	await frappe.require("cortex_assistant.bundle.js");
	frappe.cortex_assistant_app = frappe.ui.setup_cortex_assistant($parent.get(0));
}
