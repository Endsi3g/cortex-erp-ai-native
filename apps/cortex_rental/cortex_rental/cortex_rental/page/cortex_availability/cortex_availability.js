// Grille de disponibilité : équipements × jours. Composant Vue compilé par le bundler de Frappe
// (public/js/cortex_availability/cortex_availability.bundle.js) ; les données viennent de
// cortex_rental.api.v1.availability.get_matrix.
frappe.pages["cortex-availability"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Grille de disponibilité"), single_column: true });
	wrapper.cortex_availability_ready = frappe.require("cortex_availability.bundle.js").then(() => {
		frappe.ui.setup_cortex_availability(wrapper);
	});
};

frappe.pages["cortex-availability"].on_page_show = function (wrapper) {
	if (wrapper.cortex_availability_ready) {
		wrapper.cortex_availability_ready.then(() => {
			// Sans catégorie, afficher le parc complet; une catégorie reste accessible par sous-page.
			const route = frappe.get_route();
			if (wrapper.cortex_availability_set) wrapper.cortex_availability_set(route[1] || "");
		});
	}
};
