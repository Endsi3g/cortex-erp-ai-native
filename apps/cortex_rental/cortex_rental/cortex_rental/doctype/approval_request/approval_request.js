// Décision humaine sur une demande d'approbation. Le serveur applique les règles (un agent n'approuve jamais,
// on ne s'approuve pas soi-même, un refus exige un motif) ; ce script ne fait que les présenter.
frappe.ui.form.on("Approval Request", {
	refresh(frm) {
		// Une demande naît d'un geste précis, jamais d'un formulaire vide : on renvoie vers la liste et son bouton.
		if (frm.is_new()) {
			frappe.show_alert({ message: __("Une demande d'approbation se crée depuis une réservation (« Demander le contrat »), ou avec le bouton « Demander une approbation » de la liste."), indicator: "blue" }, 8);
			frappe.set_route("List", "Approval Request");
			return;
		}
		frm.disable_save(); // une décision se prend avec les boutons, jamais en enregistrant le formulaire
		const entry = cortex.APPROVAL_STATES[frm.doc.status];
		if (entry && !frm.is_new()) frm.page.set_indicator(entry[0], entry[1]);
		if (frm.is_new() || frm.doc.status !== "Pending") return;

		// Le serveur dit ce que cette personne peut faire (règle des deux personnes, seul approbateur, retrait).
		cortex.call("approval_queue.decision_options", { name: frm.doc.name }, { type: "GET" }).then((o) => {
			if (!o || frm.doc.status !== "Pending") return;
			if (o.note) frm.set_intro(frappe.utils.escape_html(__(o.note)), o.can_approve ? "orange" : "blue");
			if (o.can_approve) frm.add_custom_button(__("Approuver"), () => decide(frm, "approve")).removeClass("btn-default").addClass("btn-primary");
			if (o.can_reject) frm.add_custom_button(__("Refuser"), () => decide(frm, "reject"));
			if (o.can_withdraw) frm.add_custom_button(__("Retirer ma demande"), () => decide(frm, "withdraw"));
			if (frm.doc.entity_type && frm.doc.entity_id) {
				frm.add_custom_button(__("Ouvrir l'élément concerné"), () => frappe.set_route("Form", frm.doc.entity_type, frm.doc.entity_id));
			}
		});
	},
});

function decide(frm, decision) {
	const reject = decision === "reject";
	const withdraw = decision === "withdraw";
	frappe.prompt(
		{
			fieldname: "reason",
			fieldtype: "Small Text",
			label: reject ? __("Motif du refus (obligatoire)") : withdraw ? __("Raison du retrait (facultatif)") : __("Commentaire (facultatif)"),
			reqd: reject ? 1 : 0,
		},
		(values) => {
			cortex.call("approval_queue.decide_approval", { name: frm.doc.name, decision, reason: values.reason }, { type: "POST" }).then(() => {
				frappe.show_alert({ message: reject ? __("Demande refusée.") : withdraw ? __("Demande retirée.") : __("Demande approuvée."), indicator: reject || withdraw ? "red" : "green" });
				frm.reload_doc();
			});
		},
		reject ? __("Refuser la demande") : withdraw ? __("Retirer ma demande") : __("Approuver la demande"),
		reject ? __("Refuser") : withdraw ? __("Retirer") : __("Approuver")
	);
}
