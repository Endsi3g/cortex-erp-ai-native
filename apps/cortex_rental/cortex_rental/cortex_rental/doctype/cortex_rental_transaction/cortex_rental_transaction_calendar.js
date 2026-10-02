// Calendrier et Gantt des locations : début → fin, couleur selon l'état.
frappe.views.calendar["Cortex Rental Transaction"] = {
	field_map: {
		start: "starts_at",
		end: "ends_at",
		id: "name",
		title: "customer",
		status: "rental_state",
	},
	gantt: true,
	filters: [
		{ fieldtype: "Link", fieldname: "customer", options: "Customer", label: __("Client") },
		{
			fieldtype: "Select",
			fieldname: "rental_state",
			label: __("État"),
			options: "\nQuote\nReservation\nContract\nChecked Out\nReturned\nClosed\nCancelled\nDisputed\nQuarantine",
		},
	],
	get_css_class(doc) {
		const color = (cortex.RENTAL_STATES[doc.rental_state] || [null, "gray"])[1];
		return { gray: "default", blue: "info", purple: "info", orange: "warning", green: "success", red: "danger", yellow: "warning" }[color] || "default";
	},
};
