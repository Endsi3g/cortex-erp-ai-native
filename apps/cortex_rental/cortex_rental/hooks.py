app_name = "cortex_rental"
app_title = "Cortex Rental"
app_publisher = "Cortex AI-Native ERP Team"
app_description = "AI-Native Rental, Availability & Consignment Management for Frappe & ERPNext"
app_email = "architecture@cortex.local"
app_license = "proprietary"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cortex_rental/css/cortex_rental.css"
# app_include_js = "/assets/cortex_rental/js/cortex_rental.js"

# DocType Events (Audit logging & validation hooks)
# ------------------------------------------------
doc_events = {
    "Quotation": {
        "before_save": "cortex_rental.overrides.quotation.before_save_quotation",
        "on_submit": "cortex_rental.overrides.quotation.on_submit_quotation",
    },
    "Sales Order": {
        "before_save": "cortex_rental.overrides.sales_order.before_save_sales_order",
        "on_submit": "cortex_rental.overrides.sales_order.on_submit_sales_order",
    },
    "Serial No": {
        "before_save": "cortex_rental.overrides.serial_no.before_save_serial_no",
    }
}

# Permission Query Hooks for Multi-Tenancy
# ----------------------------------------
permission_query_conditions = {
    "Audit Event": "cortex_rental.permissions.get_permission_query_conditions",
    "Approval Request": "cortex_rental.permissions.get_permission_query_conditions",
    "Consignment Payout": "cortex_rental.permissions.get_permission_query_conditions",
    "Rental Item": "cortex_rental.permissions.get_permission_query_conditions",
}
