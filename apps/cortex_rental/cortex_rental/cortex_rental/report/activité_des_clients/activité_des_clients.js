frappe.query_reports["Activité des clients"] = {
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
			label: __("Départs depuis le"),
			fieldtype: "Date",
		},
	],
};
