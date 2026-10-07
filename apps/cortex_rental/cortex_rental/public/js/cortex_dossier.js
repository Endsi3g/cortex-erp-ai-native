// Dossier relié : en haut d'une location, d'une facture ou d'un paiement, les liens vers tout ce qui s'y rattache
// (client, factures, paiements, approbations, retenue, écritures) et l'historique (qui a fait quoi, qui a confirmé).
// Chaque lien est une action : on passe d'un écran à l'autre sans chercher. Lecture seule, tirée des dossiers réels.
window.cortex = window.cortex || {};

cortex.dossier = function (frm) {
	if (!frm || frm.is_new()) return;
	const esc = frappe.utils.escape_html;
	const slug = (t) => frappe.router.slug(t);
	const open = (type, id) => `/app/${slug(type)}/${encodeURIComponent(id)}`;
	const money = (v) => format_currency(v || 0, frappe.defaults.get_default("currency") || "CAD");
	const when = (v) => cortex.shortDateTime(`${v}:00`);
	frappe
		.call({ method: "cortex_rental.api.v1.dossier.get", args: { doctype: frm.doctype, name: frm.doc.name }, type: "GET" })
		.then((r) => {
			const d = r.message;
			if (!d || frm.doc.name !== d.name) return;
			const item = (label, html) => (html ? `<div class="cx-dos-item"><span>${label}</span>${html}</div>` : "");
			const link = (href, text) => `<a href="${href}">${esc(text)}</a>`;
			const items = [];
			if (d.customer) items.push(item(__("Client"), link(open("Customer", d.customer.id), d.customer.name)));
			if (d.transaction) items.push(item(__("Location de matériel"), link(open("Cortex Rental Transaction", d.transaction), d.transaction)));
			if (d.invoice) items.push(item(__("Facture"), link(open("Cortex Rental Invoice", d.invoice), d.invoice)));
			if (d.invoices) {
				const open_balance = d.invoices.reduce((a, i) => a + (i.balance || 0), 0);
				items.push(item(__("Factures"), d.invoices.length ? d.invoices.map((i) => `${link(open("Cortex Rental Invoice", i.id), i.id)} <small>${esc(__(i.type))} · ${esc(__(i.status))}</small>`).join("<br>") + (open_balance ? `<small class="cx-dos-warn">${__("Solde dû")} ${money(open_balance)}</small>` : "") : `<small>${__("Aucune pour l'instant")}</small>`));
			}
			if (d.siblings && d.siblings.length > 1) items.push(item(__("Autres factures"), d.siblings.filter((i) => i.id !== d.name).map((i) => link(open("Cortex Rental Invoice", i.id), i.id)).join(" · ")));
			if (d.payments && d.payments.length) items.push(item(__("Paiements"), d.payments.map((p) => `${link(open("Cortex Rental Payment", p.id), p.id)} <small>${money(p.amount)} · ${esc(p.paid_on)}</small>`).join("<br>")));
			if (d.approvals && d.approvals.length) {
				const a = d.approvals[0];
				items.push(item(__("Approbation"), `${link(open("Approval Request", a.id), a.id)} <small>${esc(__(a.status === "Pending" ? "En attente" : a.status === "Approved" ? "Approuvée" : a.status === "Rejected" ? "Refusée" : a.status))}${a.decided_by ? ` · ${esc(a.decided_by)}` : ""}</small>`));
			}
			if (d.hold && d.hold.status) items.push(item(__("Retenue du matériel"), `<small>${esc(d.hold.status === "Active" ? __("Active jusqu'au {0}", [when(d.hold.until)]) : d.hold.status === "Insufficient" ? __("Aucune : disponibilité insuffisante") : __("Libérée"))}</small>`));
			if (d.check_ins && d.check_ins.length) items.push(item(__("Retours"), d.check_ins.map((c) => link(open("Cortex Check-In", c), c)).join(" · ")));
			if (d.journal && d.journal.length) items.push(item(__("Écritures comptables"), d.journal.map((j) => link(open("Cortex Journal Entry", j), j)).join(" · ")));
			if (d.created_by) items.push(item(__("Créé par"), `<small>${esc(d.created_by)}</small>`));

			const events = (d.timeline || []).concat(d.transaction_timeline || []);
			const history = events.length
				? `<details class="cx-dos-history"><summary>${__("Historique du dossier")} <em>${events.length}</em></summary><ul>${events.map((e) => `<li><span class="cx-tl-dot ${esc(e.category)}"></span><span><b>${esc(e.actor)}</b> · ${esc(e.text)}${e.detail ? ` <em>« ${esc(e.detail)} »</em>` : ""}${e.requested_by || e.confirmed_by ? `<small>${e.requested_by ? `${__("Demandée par")} ${esc(e.requested_by)}` : ""}${e.requested_by && e.confirmed_by ? " · " : ""}${e.confirmed_by ? `${__("Confirmée par")} ${esc(e.confirmed_by)}` : ""}</small>` : ""}</span><time>${when(e.at)}</time></li>`).join("")}</ul></details>`
				: "";
			frm.layout.wrapper.find(".cx-dossier").remove();
			frm.layout.wrapper.prepend(`<section class="cx-dossier" aria-label="${__("Dossier relié")}"><div class="cx-dos-grid">${items.join("")}</div>${history}</section>`);
		});
};
