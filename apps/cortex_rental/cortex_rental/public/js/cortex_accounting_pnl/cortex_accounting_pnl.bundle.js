import { createApp } from "vue";
import CortexAccountingPnl from "./CortexAccountingPnl.vue";

function setup_cortex_accounting_pnl(wrapper) {
	const app = createApp(CortexAccountingPnl);
	app.mount(wrapper);
	return app;
}

frappe.ui.setup_cortex_accounting_pnl = setup_cortex_accounting_pnl;
export default setup_cortex_accounting_pnl;
