// Thin Desk shell: the screen itself is built in public/frontend and mounted by
// public/js/cortex_host/cortex_host.js.
frappe.pages["cortex-checkin"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Check-in et retours",
		single_column: true,
	});
};

frappe.pages["cortex-checkin"].on_page_show = function (wrapper) {
	cortex_rental.host.mount(wrapper);
};

frappe.pages["cortex-checkin"].on_page_hide = function (wrapper) {
	cortex_rental.host.unmount(wrapper);
};
