import { createApp } from "vue";
import CortexCheckin from "./CortexCheckin.vue";

function setup_cortex_checkin(wrapper) {
	const app = createApp(CortexCheckin);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_checkin = setup_cortex_checkin;
export default setup_cortex_checkin;
