import { createApp } from "vue";
import CortexCustomers from "./CortexCustomers.vue";

function setup_cortex_customers(wrapper) {
	const app = createApp(CortexCustomers);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_customers = setup_cortex_customers;
export default setup_cortex_customers;
