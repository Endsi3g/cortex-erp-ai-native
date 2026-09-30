// Monté par la Page Desk `cortex-availability` (cortex_rental/page/cortex_availability/cortex_availability.js).
import { createApp } from "vue";
import CortexAvailability from "./CortexAvailability.vue";

frappe.provide("frappe.ui");

frappe.ui.setup_cortex_availability = function (wrapper) {
	if (wrapper.cortex_availability_app) return;
	const parent = $(wrapper).find(".layout-main-section")[0] || wrapper;
	const mount = document.createElement("div");
	mount.className = "cx-avail-mount";
	parent.appendChild(mount);
	const app = createApp(CortexAvailability);
	// Le gabarit utilise __() pour traduire les catégories et les groupes.
	app.config.globalProperties.__ = window.__;
	const vm = app.mount(mount);
	wrapper.cortex_availability_app = app;
	wrapper.cortex_availability_refresh = () => vm.load && vm.load();
};
