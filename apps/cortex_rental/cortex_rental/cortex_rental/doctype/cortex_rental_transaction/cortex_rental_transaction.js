// Frappe Form client script for Cortex Rental Transaction

frappe.ui.form.on("Cortex Rental Transaction", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Ouvrir dans Cortex"), () => {
			window.location.href = `/cortex/rentals/${encodeURIComponent(frm.doc.name)}`;
		});
		if (frm.doc.rental_state === "Checked Out") {
			frm.add_custom_button(__("Effectuer le Check-in"), () => {
				window.location.href = `/cortex/checkin/${encodeURIComponent(frm.doc.name)}`;
			}).addClass("btn-primary");
		}
	},
});
