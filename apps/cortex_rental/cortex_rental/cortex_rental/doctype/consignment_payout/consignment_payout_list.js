frappe.listview_settings["Consignment Payout"] = {
	add_fields: ["status", "owner"],
	get_indicator(doc) {
		const map = {
			Calculated: [__("Calculé"), "orange"],
			Approved: [__("Approuvé"), "blue"],
			Paid: [__("Payé"), "green"],
			Cancelled: [__("Annulé"), "red"],
		};
		return cortex.indicator(map, "status")(doc);
	},
};
