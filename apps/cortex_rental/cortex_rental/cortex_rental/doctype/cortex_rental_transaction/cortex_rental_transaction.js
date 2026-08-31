// Frappe Form client script for Cortex Rental Transaction

frappe.ui.form.on("Cortex Rental Transaction", {
	refresh(frm) {
		if (frm.doc.rental_state === "Checked Out" && !frm.is_new()) {
			frm.add_custom_button(__("Effectuer le Check-in"), function () {
				frappe.route_options = {
					transaction: frm.doc.name,
				};
				frappe.set_route("cortex-checkin");
			}).addClass("btn-primary");
		}
	},
});
