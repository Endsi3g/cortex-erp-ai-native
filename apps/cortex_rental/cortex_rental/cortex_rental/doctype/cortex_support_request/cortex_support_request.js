// Demande de support : on note la page d'où l'on vient pour aider l'équipe à comprendre le contexte.
frappe.ui.form.on("Cortex Support Request", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.page_url) {
			frm.set_value("page_url", (cortex.previousRoute || "").slice(0, 140));
		}
	},
	refresh(frm) {
		frm.page.set_indicator(...(cortex.SUPPORT_STATES[frm.doc.status] || [frm.doc.status, "gray"]));
	},
});
