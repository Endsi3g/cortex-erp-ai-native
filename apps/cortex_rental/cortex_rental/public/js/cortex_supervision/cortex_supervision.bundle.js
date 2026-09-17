import { createApp } from "vue";
import CortexSupervision from "./CortexSupervision.vue";

function setup_cortex_supervision(wrapper) {
	const app = createApp(CortexSupervision);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_supervision = setup_cortex_supervision;
export default setup_cortex_supervision;
