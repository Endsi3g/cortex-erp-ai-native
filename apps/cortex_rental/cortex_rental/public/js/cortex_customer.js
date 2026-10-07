// Fiche client 360° : tout ce que le système sait du client, tiré des dossiers réels (aucune estimation).
frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.cortex_company) return;
		frm.add_custom_button(__("Nouveau devis"), () => frappe.new_doc("Cortex Rental Transaction", { customer: frm.doc.name }));
		frm.add_custom_button(__("Voir ses locations"), () => frappe.set_route("List", "Cortex Rental Transaction", { customer: frm.doc.name }));
		cortex_customer.show_summary(frm);
	},
});

const cortex_customer = {
	show_summary(frm) {
		cortex.call("customers.summary", { customer: frm.doc.name }, { type: "GET" }).then((s) => {
			if (!s || frm.doc.name !== s.customer) return;
			const money = (v) => format_currency(v || 0, frappe.defaults.get_default("currency") || "CAD");
			const link = (name) => `<a href="/app/cortex-rental-transaction/${encodeURIComponent(name)}">${frappe.utils.escape_html(name)}</a>`;
			const cells = [];
			const b = s.billing;
			if (b) {
				cells.push([__("Solde dû"), money(b.balance_due), b.overdue_invoices ? "red" : ""]);
				cells.push([__("Total facturé"), money(b.billed_total), ""]);
			}
			cells.push([__("Locations"), String(s.rentals_count || 0), ""]);
			if (s.late_returns) cells.push([__("Retours en retard"), String(s.late_returns), "red"]);
			if (s.last_rental) cells.push([__("Dernière location"), cortex.shortDateTime(s.last_rental.ends_at), ""]);
			const stats = cells
				.map(([label, value, tone]) => `<div class="cx-c360-stat"><div class="text-muted small">${label}</div><div class="h5 ${tone === "red" ? "text-danger" : ""}">${value}</div></div>`)
				.join("");
			const list = (title, rows, text) =>
				rows.length
					? `<div class="cx-c360-list"><div class="text-muted small">${title}</div>${rows.map((r) => `<div>${link(r.name)} <span class="text-muted">${text(r)}</span></div>`).join("")}</div>`
					: "";
			const html =
				`<div class="cx-c360-bar" style="background:var(--card-bg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);padding:12px 16px;margin-bottom:12px">` +
				`<div class="cx-c360" style="display:flex;flex-wrap:wrap;gap:32px">${stats}</div>` +
				`<div style="display:flex;flex-wrap:wrap;gap:32px;margin-top:8px">` +
				list(__("Devis ouverts"), s.quotes, (r) => `${money(r.total)} · ${r.hold_status === "Active" ? __("matériel retenu") : __("sans retenue")}`) +
				list(__("Locations en cours"), s.active, (r) => `${__(r.state)} · ${cortex.shortDateTime(r.starts_at)} → ${cortex.shortDateTime(r.ends_at)}`) +
				`</div></div>`;
			frm.layout.wrapper.find(".cx-c360-bar").remove();
			frm.layout.wrapper.prepend(html);
		});
	},
};
