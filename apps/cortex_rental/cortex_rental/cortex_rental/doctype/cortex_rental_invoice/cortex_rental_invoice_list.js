frappe.listview_settings["Cortex Rental Invoice"] = {
	add_fields: ["status", "balance", "total", "due_date"],
	get_indicator(doc) {
		return cortex.indicator(cortex.INVOICE_STATES, "status")(doc);
	},
	// Les factures sont émises par Cortex à la réservation et à la clôture : pas de bouton « Ajouter ».
	onload(listview) {
		listview.page.clear_primary_action && listview.page.clear_primary_action();
	},
};
