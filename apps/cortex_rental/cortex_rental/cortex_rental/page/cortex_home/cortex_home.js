// Accueil Cortex : première page après la connexion (écran conversationnel).
// Le composant Vue est compilé par le bundler natif de Frappe (`bench build`), voir
// public/js/cortex_home/cortex_home.bundle.js.
frappe.pages["cortex-home"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Accueil Cortex"), single_column: true });
	wrapper.cortex_home_ready = frappe.require("cortex_home.bundle.js").then(() => {
		frappe.ui.setup_cortex_home(wrapper);
	});
};

frappe.pages["cortex-home"].on_page_show = function (wrapper) {
	if (wrapper.cortex_home_ready) {
		wrapper.cortex_home_ready.then(() => {
			if (wrapper.cortex_home_refresh) wrapper.cortex_home_refresh();
		});
	}
};
