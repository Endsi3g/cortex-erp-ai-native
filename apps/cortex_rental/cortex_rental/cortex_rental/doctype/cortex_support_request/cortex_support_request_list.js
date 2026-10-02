frappe.listview_settings["Cortex Support Request"] = {
	add_fields: ["status", "priority", "category"],
	get_indicator(doc) {
		return cortex.indicator(cortex.SUPPORT_STATES, "status")(doc);
	},
	onload(listview) {
		cortex.renamePrimary(listview, __("Nouvelle demande"));
	},
};
