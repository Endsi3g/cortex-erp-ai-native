frappe.query_reports["Journal comptable"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: (frappe.boot.cortex_home && frappe.boot.cortex_home.company) || frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{ fieldname: "from_date", label: __("Du"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("Au"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "account", label: __("Compte (numéro)"), fieldtype: "Data" },
	],
};
