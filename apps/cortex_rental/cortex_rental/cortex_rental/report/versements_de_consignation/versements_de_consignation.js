frappe.query_reports["Versements de consignation"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "status",
			label: __("État"),
			fieldtype: "Select",
			options: ["", "Calculated", "Approved", "Paid", "Cancelled"],
		},
	],
};
