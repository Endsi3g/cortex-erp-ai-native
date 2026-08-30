import { createApp } from "vue";
import CortexTransactionComposer from "./CortexTransactionComposer.vue";

function setup_cortex_transaction_composer(wrapper) {
	const app = createApp(CortexTransactionComposer);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_transaction_composer = setup_cortex_transaction_composer;
export default setup_cortex_transaction_composer;
