import { createApp } from "vue";
import CortexFleet from "./CortexFleet.vue";

function setup_cortex_fleet(wrapper) {
	const app = createApp(CortexFleet);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_fleet = setup_cortex_fleet;
export default setup_cortex_fleet;
