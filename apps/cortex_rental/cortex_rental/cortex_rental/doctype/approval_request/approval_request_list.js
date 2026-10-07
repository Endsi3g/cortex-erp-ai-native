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
		// Si vous êtes la seule personne autorisée et que la règle est désactivée, vos demandes ne peuvent pas être approuvées :
		// on le dit clairement, avec un chemin pour comprendre et décider (propriétaire seulement).
		frappe.call({ method: "cortex_rental.api.v1.approval_queue.self_approval_policy", type: "GET" }).then((r) => {
			const p = r.message;
			if (!p || !p.sole_approver || !p.can_manage || p.enabled) return;
			if (listview.page.main.find(".cx-policy-banner").length) return;
			const banner = $(`<div class="cx-policy-banner"><span>${__("Vous êtes la seule personne autorisée à approuver : vos propres demandes ne peuvent pas être approuvées.")}</span><span><a class="btn btn-default btn-xs" href="/app/user">${__("Ajouter une personne")}</a> <button type="button" class="btn btn-primary btn-xs">${__("Comprendre et décider")}</button></span></div>`);
			banner.find("button").on("click", () => cortex.selfApprovalDialog(() => banner.remove()));
			listview.page.main.prepend(banner);
		});
		// Frappe cache le bouton principal quand la création directe est interdite : on ajoute un bouton à nous.
		listview.page.add_inner_button(__("Demander une approbation"), () => cortex.requestContractApproval()).addClass("btn-primary").removeClass("btn-default");
	},
	add_fields: ["status", "action", "requested_by_type", "requested_by_id", "entity_id"],
	get_indicator(doc) {
		return cortex.indicator(cortex.APPROVAL_STATES, "status")(doc);
	},
	formatters: {
		// Le code interne (« rental.transaction.transition_to_contract ») devient une phrase lisible.
		action: (value) => cortex.approvalActionLabel(value),
	},
};
