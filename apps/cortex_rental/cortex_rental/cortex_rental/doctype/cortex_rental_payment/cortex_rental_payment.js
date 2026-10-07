// Paiement Cortex : lié à sa facture, à sa location, à son client et à son écriture comptable (lecture seule).
frappe.ui.form.on("Cortex Rental Payment", {
	refresh(frm) {
		cortex.dossier(frm);
		if (!frm.is_new() && frm.doc.invoice) frm.add_custom_button(__("Ouvrir la facture"), () => frappe.set_route("Form", "Cortex Rental Invoice", frm.doc.invoice));
	},
});
