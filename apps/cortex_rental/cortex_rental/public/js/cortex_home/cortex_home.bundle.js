// Accueil Cortex — monté par la Page Desk `cortex-home` (cortex_rental/page/cortex_home/cortex_home.js).
// Compilé par le bundler natif de Frappe (`bench build`) : Vue 3, sans Vite ni Frappe UI.
import { createApp } from "vue";
import CortexHome from "./CortexHome.vue";

frappe.provide("frappe.ui");

frappe.ui.setup_cortex_home = function (wrapper) {
	if (wrapper.cortex_home_app) return;

	const parent = $(wrapper).find(".layout-main-section")[0] || wrapper;
	const mount = document.createElement("div");
	mount.className = "cortex-home-mount";
	parent.appendChild(mount);

	const app = createApp(CortexHome);
	const vm = app.mount(mount);
	wrapper.cortex_home_app = app;
	// Rafraîchit les conversations récentes quand on revient sur la page.
	wrapper.cortex_home_refresh = () => vm.refresh && vm.refresh();
};
