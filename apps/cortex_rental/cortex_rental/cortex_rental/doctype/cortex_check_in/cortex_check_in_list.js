frappe.listview_settings["Cortex Check-In"] = {
	add_fields: ["status", "transaction"],
	get_indicator(doc) {
		return doc.status === "Completed"
			? [__("Terminé"), "green", "status,=,Completed"]
			: [__("Brouillon"), "orange", "status,=,Draft"];
	},
};
