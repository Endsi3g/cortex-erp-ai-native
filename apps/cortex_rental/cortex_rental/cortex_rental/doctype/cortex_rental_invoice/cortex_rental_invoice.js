// Facture Cortex : bouton « Enregistrer un paiement » (le serveur valide le montant, la société et les droits).
frappe.ui.form.on("Cortex Rental Invoice", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Cancelled") return;
		const balance = flt(frm.doc.balance);
		if (balance > 0 && frappe.model.can_create("Cortex Rental Payment")) {
			frm.add_custom_button(__("Enregistrer un paiement"), () => {
				frappe.prompt(
					[
						{ fieldname: "amount", fieldtype: "Currency", label: __("Montant"), reqd: 1, default: balance },
						{ fieldname: "method", fieldtype: "Select", label: __("Mode de paiement"), options: ["Card", "Cash", "Bank Transfer", "Cheque", "Other"].map((v) => ({ value: v, label: __(v) })), default: "Card", reqd: 1 },
						{ fieldname: "paid_on", fieldtype: "Date", label: __("Date"), default: frappe.datetime.get_today(), reqd: 1 },
						{ fieldname: "reference", fieldtype: "Data", label: __("Référence") },
					],
					(values) => {
						frappe.call({
							method: "cortex_rental.api.v1.billing.record_payment",
							args: { invoice: frm.doc.name, ...values },
							freeze: true,
							callback: () => frm.reload_doc(),
						});
					},
					__("Enregistrer un paiement"),
					__("Enregistrer")
				);
			}, __("Actions"));
		}
		if (frm.doc.rental_transaction) {
			frm.add_custom_button(__("Ouvrir la location"), () => frappe.set_route("Form", "Cortex Rental Transaction", frm.doc.rental_transaction), __("Actions"));
		}
		frm.page.set_indicator(__(frm.doc.status), { Paid: "green", "Partially Paid": "orange", Issued: "blue", Cancelled: "gray" }[frm.doc.status] || "gray");
	},
});
