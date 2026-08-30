import { createApp } from "vue";
import CortexCopilotPanel from "../cortex_copilot/CortexCopilotPanel.vue";

function setup_cortex_assistant(wrapper) {
	const app = createApp(CortexCopilotPanel, { mode: "docked" });
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_assistant = setup_cortex_assistant;
export default setup_cortex_assistant;
