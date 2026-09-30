frappe.listview_settings["Cortex Inbound Request"] = {
	add_fields: ["status", "source_channel"],
	get_indicator(doc) {
		const map = {
			Received: [__("Reçue"), "blue"],
			Processing: [__("En traitement"), "orange"],
			Processed: [__("Traitée"), "green"],
			Rejected: [__("Rejetée"), "red"],
		};
		return cortex.indicator(map, "status")(doc);
	},
};
