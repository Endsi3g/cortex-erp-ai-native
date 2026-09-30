cortex.APPROVAL_ACTIONS = {
	"transition_to_contract": __("Confirmer un contrat"),
	"transition_to_reservation": __("Confirmer une réservation"),
	"transition_to_checked out": __("Faire sortir le matériel"),
	"transition_to_closed": __("Clôturer la location"),
	"transition_to_cancelled": __("Annuler la location"),
};

frappe.listview_settings["Approval Request"] = {
	add_fields: ["status", "action", "requested_by_type", "requested_by_id", "entity_id"],
	get_indicator(doc) {
		return cortex.indicator(cortex.APPROVAL_STATES, "status")(doc);
	},
	formatters: {
		// Le code interne (« rental.transaction.transition_to_contract ») devient une phrase lisible.
		action: (value) => cortex.APPROVAL_ACTIONS[String(value || "").split(".").pop()] || value,
	},
};
