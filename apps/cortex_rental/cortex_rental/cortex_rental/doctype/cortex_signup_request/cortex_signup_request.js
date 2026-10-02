frappe.ui.form.on("Cortex Signup Request", {
	refresh(frm) {
		if (frm.doc.status === "Pending Verification") {
			frm.add_custom_button(__("Renvoyer le courriel de vérification"), () =>
				frm.call("resend_verification").then(() => frm.reload_doc())
			);
		}
		if (frm.doc.status !== "Pending Approval") return;
		frm.add_custom_button(__("Approuver et créer l'entreprise"), () => {
			frappe.confirm(
				__("Créer l'entreprise « {0} » et inviter {1} ?", [frm.doc.company_name, frm.doc.email]),
				() =>
					frm.call("approve").then((r) => {
						const result = r.message || {};
						if (result.setup_link) {
							frappe.msgprint({
								title: __("Courriel non envoyé"),
								indicator: "orange",
								message: __("Aucun compte courriel sortant n'est configuré. Transmettez ce lien à usage unique à {0} :", [frm.doc.email]) +
									`<p><input class="form-control" readonly value="${frappe.utils.escape_html(result.setup_link)}" onclick="this.select()"></p>`,
							});
						}
						frm.reload_doc();
					})
			);
		}).addClass("btn-primary");
		frm.add_custom_button(__("Refuser"), () => {
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Motif (envoyé au demandeur)") },
				(values) => frm.call("reject", { reason: values.reason }).then(() => frm.reload_doc()),
				__("Refuser la demande")
			);
		});
	},
});
