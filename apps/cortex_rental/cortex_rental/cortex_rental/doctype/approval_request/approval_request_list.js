frappe.listview_settings["Approval Request"] = {
	add_fields: ["status", "action", "requested_by_type"],
	get_indicator(doc) {
		return cortex.indicator(cortex.APPROVAL_STATES, "status")(doc);
	},
};
