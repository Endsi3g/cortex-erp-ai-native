cortex.APPROVAL_ACTIONS = {
	"transition_to_contract": __("Confirmer un contrat"),
	"transition_to_reservation": __("Confirmer une réservation"),
	"transition_to_checked out": __("Faire sortir le matériel"),
	"transition_to_closed": __("Clôturer la location"),
	"transition_to_cancelled": __("Annuler la location"),
};

// Une demande d'approbation naît d'un geste précis (« Demander le contrat » sur une réservation) : le formulaire brut
// n'est pas offert. Ce bouton ouvre le même geste depuis la liste.
cortex.requestContractApproval = function () {
	const dialog = new frappe.ui.Dialog({
		title: __("Demander l'approbation d'un contrat"),
		fields: [
			{
				fieldname: "rental",
				fieldtype: "Link",
				options: "Cortex Rental Transaction",
				label: __("Réservation"),
				reqd: 1,
				description: __("Seules les réservations prêtes pour le contrat sont proposées."),
				get_query: () => ({ filters: { rental_state: "Reservation" } }),
			},
		],
		primary_action_label: __("Soumettre à l'approbation"),
		primary_action: (values) => {
			cortex.call("rentals.request_contract", { name: values.rental }, { type: "POST" }).then((r) => {
				dialog.hide();
				if (r && r.approval_request_id) frappe.set_route("Form", "Approval Request", r.approval_request_id);
				else if (r && r.errors && r.errors.length) frappe.msgprint(frappe.utils.escape_html(r.errors[0].message));
			});
		},
	});
	dialog.show();
};

frappe.listview_settings["Approval Request"] = {
	onload(listview) {
		// Frappe cache le bouton principal quand la création directe est interdite : on ajoute un bouton à nous.
		listview.page.add_inner_button(__("Demander une approbation"), () => cortex.requestContractApproval()).addClass("btn-primary").removeClass("btn-default");
	},
	add_fields: ["status", "action", "requested_by_type", "requested_by_id", "entity_id"],
	get_indicator(doc) {
		return cortex.indicator(cortex.APPROVAL_STATES, "status")(doc);
	},
	formatters: {
		// Le code interne (« rental.transaction.transition_to_contract ») devient une phrase lisible.
		action: (value) => cortex.APPROVAL_ACTIONS[String(value || "").split(".").pop()] || value,
	},
};
