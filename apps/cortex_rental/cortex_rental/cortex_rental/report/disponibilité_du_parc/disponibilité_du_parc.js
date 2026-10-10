frappe.query_reports["Disponibilité du parc"] = {
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
			fieldname: "from_date",
			label: __("Du"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("Au"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), 7),
			reqd: 1,
		},
		{
			fieldname: "category",
			label: __("Catégorie"),
			fieldtype: "Select",
			options: ["", ...((frappe.boot && frappe.boot.cortex_categories) || ["Camera Bodies", "Cinema Lenses", "Lighting", "Grip & Rigging", "Audio", "Monitors & Wireless Video", "Power & Batteries"])],
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const color = data.status === __("Complet") ? "red" : data.status === __("Limité") ? "orange" : "green";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
