// Décision humaine sur une demande d'approbation. Le serveur applique les règles (un agent n'approuve jamais,
// on ne s'approuve pas soi-même, un refus exige un motif) ; ce script ne fait que les présenter.
frappe.ui.form.on("Approval Request", {
	refresh(frm) {
		const entry = cortex.APPROVAL_STATES[frm.doc.status];
		if (entry && !frm.is_new()) frm.page.set_indicator(entry[0], entry[1]);
		if (frm.is_new() || frm.doc.status !== "Pending") return;

		const group = __("Décision");
		frm.add_custom_button(__("Approuver"), () => decide(frm, "approve"), group);
		frm.add_custom_button(__("Refuser"), () => decide(frm, "reject"), group);
		frm.page.set_inner_btn_group_as_primary(group);

		if (frm.doc.entity_type && frm.doc.entity_id) {
			frm.add_custom_button(__("Ouvrir l'élément concerné"), () =>
				frappe.set_route("Form", frm.doc.entity_type, frm.doc.entity_id)
			);
		}
	},
});

function decide(frm, decision) {
	const reject = decision === "reject";
	frappe.prompt(
		{
			fieldname: "reason",
			fieldtype: "Small Text",
			label: reject ? __("Motif du refus (obligatoire)") : __("Commentaire (facultatif)"),
			reqd: reject ? 1 : 0,
		},
		(values) => {
			cortex.call("approval_queue.decide_approval", { name: frm.doc.name, decision, reason: values.reason }).then(() => {
				frappe.show_alert({ message: reject ? __("Demande refusée.") : __("Demande approuvée."), indicator: reject ? "red" : "green" });
				frm.reload_doc();
			});
		},
		reject ? __("Refuser la demande") : __("Approuver la demande"),
		reject ? __("Refuser") : __("Approuver")
	);
}
