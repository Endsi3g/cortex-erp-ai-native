frappe.listview_settings["Cortex Rental Transaction"] = {
	add_fields: ["rental_state", "customer", "starts_at", "ends_at", "grand_total"],
	hide_name_column: false,
	get_indicator(doc) {
		return cortex.indicator(cortex.RENTAL_STATES, "rental_state")(doc);
	},
	formatters: {
		starts_at: (value) => cortex.shortDateTime(value),
		ends_at: (value) => cortex.shortDateTime(value),
	},
	onload(listview) {
		cortex.renamePrimary(listview, __("Nouvelle location"));
	},
};
