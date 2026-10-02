frappe.listview_settings["Cortex Extraction Run"] = {
	add_fields: ["validation_status", "inbound_request"],
	get_indicator(doc) {
		const map = { Valid: [__("Valide"), "green"], Invalid: [__("À corriger"), "red"] };
		return cortex.indicator(map, "validation_status")(doc);
	},
};
