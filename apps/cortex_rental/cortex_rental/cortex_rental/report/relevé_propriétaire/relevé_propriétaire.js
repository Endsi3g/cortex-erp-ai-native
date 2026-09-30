frappe.query_reports["Relevé propriétaire"] = {
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
			fieldname: "owner",
			label: __("Propriétaire"),
			fieldtype: "Link",
			options: "Consignment Owner",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("Du"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Au"),
			fieldtype: "Date",
		},
	],
};
