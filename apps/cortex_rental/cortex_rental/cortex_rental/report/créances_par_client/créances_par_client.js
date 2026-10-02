frappe.query_reports["Créances par client"] = {
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
			fieldname: "as_of",
			label: __("Au"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
