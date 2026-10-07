// Paiement Cortex : lié à sa facture, à sa location, à son client et à son écriture comptable (lecture seule).
frappe.ui.form.on("Cortex Rental Payment", {
	refresh(frm) {
		cortex.dossier(frm);
		if (!frm.is_new() && frm.doc.invoice) frm.add_custom_button(__("Ouvrir la facture"), () => frappe.set_route("Form", "Cortex Rental Invoice", frm.doc.invoice));
		// Le client d'abord : solde dû, factures et locations en cours en tête du paiement (lecture seule, droits vérifiés).
		if (!frm.is_new() && frm.doc.customer) {
			cortex.call("customers.summary", { customer: frm.doc.customer }, { type: "GET", freeze: false, silent: true })
				.then((s) => {
					const money = (v) => format_currency(v || 0, frappe.defaults.get_default("currency") || "CAD");
					const parts = [`<b>${frappe.utils.escape_html(frm.doc.customer)}</b>`];
					if (s.balance_due != null) parts.push(`${__("Solde dû")} : ${money(s.balance_due)}`);
					if (s.rentals_count != null) parts.push(`${s.rentals_count} ${__("locations")}`);
					if (s.late_returns) parts.push(`<span class="text-danger">${s.late_returns} ${__("retour(s) en retard")}</span>`);
					frm.dashboard.set_headline(parts.join(" · "));
				})
				.catch(() => {});
		}
	},
});
