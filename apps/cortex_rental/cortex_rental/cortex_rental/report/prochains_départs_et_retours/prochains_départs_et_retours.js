frappe.query_reports["Prochains départs et retours"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: (frappe.boot.cortex_home && frappe.boot.cortex_home.company) || frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "days",
			label: __("Horizon (jours)"),
			fieldtype: "Int",
			default: 7,
		},
		{
			fieldname: "kind",
			label: __("Type"),
			fieldtype: "Select",
			options: ["", "Départs", "Retours"],
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "kind" && data) {
			const color = data.kind === __("En retard") ? "red" : data.kind === __("Départ") ? "blue" : "green";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
