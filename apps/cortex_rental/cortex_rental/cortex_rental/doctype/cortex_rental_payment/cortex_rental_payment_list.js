// Liste des paiements : l'essentiel d'un coup d'œil (remboursement en orange, paiement en vert) et colonnes utiles.
frappe.listview_settings["Cortex Rental Payment"] = {
	add_fields: ["kind", "method", "amount", "signed_amount", "paid_on", "customer", "invoice"],
	get_indicator(doc) {
		return doc.kind === "Refund" ? [__("Remboursement"), "orange", "kind,=,Refund"] : [__("Paiement"), "green", "kind,=,Payment"];
	},
	formatters: {
		method(value) {
			return value ? __(value) : "";
		},
	},
	// Les paiements s'enregistrent depuis la facture (le serveur valide le montant et les droits) : pas de bouton « Ajouter ».
	onload(listview) {
		listview.page.clear_primary_action && listview.page.clear_primary_action();
	},
};
