// Règles partagées de l'interface : libellés lisibles des demandes d'approbation, et fenêtre d'explication de la règle
// « le seul approbateur décide de ses propres demandes » (désactivée par défaut ; chaque société l'active elle-même).
window.cortex = window.cortex || {};

cortex.APPROVAL_ACTIONS = {
	transition_to_contract: __("Confirmer un contrat"),
	transition_to_reservation: __("Confirmer une réservation"),
	"transition_to_checked out": __("Faire sortir le matériel"),
	transition_to_closed: __("Clôturer la location"),
	transition_to_cancelled: __("Annuler la location"),
	transition_to_disputed: __("Ouvrir un litige"),
};

// « rental.transaction.transition_to_contract » devient « Confirmer un contrat » (jamais le code interne à l'écran).
cortex.approvalActionLabel = function (action) {
	const key = String(action || "").split(".").pop();
	if (cortex.APPROVAL_ACTIONS[key]) return cortex.APPROVAL_ACTIONS[key];
	const text = key.replace(/_/g, " ").trim();
	return text ? text.charAt(0).toUpperCase() + text.slice(1) : __("Demande");
};

// Explique la règle, ses bénéfices et ses dangers, puis laisse le propriétaire décider (avec une case de lecture).
cortex.selfApprovalDialog = function (onDone) {
	frappe.call({ method: "cortex_rental.api.v1.approval_queue.self_approval_policy", type: "GET" }).then((r) => {
		const p = r.message;
		const esc = frappe.utils.escape_html;
		const list = (items) => `<ul class="cx-policy-list">${items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
		const state = p.enabled
			? `<p class="cx-policy-state on">${__("Cette règle est activée pour votre société.")}${p.sole_approver ? "" : " " + __("Elle ne s'applique pas en ce moment : une autre personne autorisée existe.")}</p>`
			: `<p class="cx-policy-state">${__("Cette règle est désactivée : c'est le réglage prudent.")}</p>`;
		const body = `<div class="cx-policy">${state}<p>${esc(p.what)}</p><h4>${__("Ce que vous gagnez")}</h4>${list(p.benefits)}<h4>${__("Ce que vous risquez")}</h4>${list(p.dangers)}<p class="cx-policy-advice">${esc(p.advice)}</p></div>`;
		const fields = [{ fieldtype: "HTML", fieldname: "body", options: body }];
		if (!p.can_manage) fields.push({ fieldtype: "HTML", fieldname: "note", options: `<p class="text-muted">${__("Seul le propriétaire de la société peut changer cette règle.")}</p>` });
		else if (!p.enabled) fields.push({ fieldtype: "Check", fieldname: "ack", label: __("J'ai compris les risques et j'assume cette décision.") });
		const dialog = new frappe.ui.Dialog({
			title: __("Auto-approbation du propriétaire seul"),
			size: "large",
			fields,
			primary_action_label: !p.can_manage ? __("Fermer") : p.enabled ? __("Désactiver la règle") : __("Activer la règle"),
			primary_action: (values) => {
				if (!p.can_manage) return dialog.hide();
				if (!p.enabled && !values.ack) {
					frappe.show_alert({ message: __("Cochez la case pour confirmer que vous avez compris les risques."), indicator: "orange" });
					return;
				}
				frappe
					.call({ method: "cortex_rental.api.v1.approval_queue.set_self_approval", type: "POST", args: { enabled: p.enabled ? 0 : 1, acknowledged: values.ack ? 1 : 0 } })
					.then(() => {
						dialog.hide();
						frappe.show_alert({ message: p.enabled ? __("Règle désactivée.") : __("Règle activée. Chaque auto-approbation sera notée dans le journal d'audit."), indicator: p.enabled ? "blue" : "orange" }, 8);
						if (onDone) onDone();
					});
			},
		});
		dialog.show();
	});
};
