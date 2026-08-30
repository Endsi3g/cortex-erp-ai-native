// Global mount for the floating Cortex Copilot launcher + panel —
// loaded on every Desk page via hooks.py's app_include_js (verified
// real pattern: app_include_js can reference a .bundle.js with ESM
// imports, resolved by Frappe's esbuild pipeline the same way a Desk
// Page's own .bundle.js is — see docs/design-system.md's "packaging"
// note and CHANGELOG.md, ninth wave).
//
// frappe.ready() is the real, documented way to defer a global script
// until the Desk shell (frappe.boot, frappe.session, etc.) is actually
// up — not just until the DOM parses.
import { createApp } from "vue";
import CortexCopilotPanel from "./CortexCopilotPanel.vue";

frappe.ready(function () {
	if (frappe.session.user === "Guest") return;

	// Purely a UX nicety — don't show the launcher to an identity that
	// would always get PermissionDenied from require_human_staff_role()
	// server-side. The server enforces the real gate regardless of
	// whether this check is accurate or even runs at all.
	const HUMAN_STAFF_ROLES = [
		"System Manager",
		"Cortex System Manager",
		"Cortex Operations Manager",
		"Cortex Counter Staff",
		"Cortex Inventory Manager",
		"Cortex Finance Manager",
		"Cortex Consignment Manager",
		"Cortex Account Reviewer",
		"Rental Manager",
		"Rental Operator",
	];
	const roles = frappe.user_roles || [];
	if (!roles.some((r) => HUMAN_STAFF_ROLES.includes(r))) return;

	const mountPoint = document.createElement("div");
	mountPoint.id = "cortex-copilot-mount";
	document.body.appendChild(mountPoint);

	const app = createApp(CortexCopilotPanel, { mode: "floating" });
	app.mount(mountPoint);
	frappe.cortex_copilot_app = app;
});
