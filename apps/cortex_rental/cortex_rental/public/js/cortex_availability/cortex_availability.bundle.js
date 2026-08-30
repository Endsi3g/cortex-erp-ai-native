import { createApp } from "vue";
import CortexAvailability from "./CortexAvailability.vue";

function setup_cortex_availability(wrapper) {
	const app = createApp(CortexAvailability);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_availability = setup_cortex_availability;
export default setup_cortex_availability;
