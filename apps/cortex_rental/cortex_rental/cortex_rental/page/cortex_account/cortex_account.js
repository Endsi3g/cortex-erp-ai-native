// Mon compte : sept pages dédiées (profil, statistiques, approbations, activité, sécurité, notifications, société et
// rôles), chacune dans le groupe « Mon compte » de la barre latérale (/app/cortex-account/<page>). Chaque action passe
// par cortex_rental.api.v1.account.* (ou administration.* pour l'équipe) et ne concerne que la personne connectée ; les
// chiffres viennent des dossiers réels, jamais d'une estimation. Tout est aligné à gauche, en une seule colonne.
frappe.pages["cortex-account"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Mon compte"), single_column: true });
	wrapper.cx_account = new cortex.AccountPage(wrapper);
};

frappe.pages["cortex-account"].on_page_show = function (wrapper) {
	if (wrapper.cx_account) wrapper.cx_account.show(frappe.get_route()[1]);
};

cortex.AccountPage = class AccountPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.root = $(wrapper).find(".layout-main-section");
		this.tab = "profil";
		this.data = null;
		this.period = "30";
		this.PAGES = {
			profil: __("Profil"),
			statistiques: __("Statistiques"),
			approbations: __("Mes approbations"),
			activite: __("Activité"),
			securite: __("Sécurité"),
			notifications: __("Notifications"),
			societe: __("Société et rôles"),
		};
		this.root.html('<div class="cx-acct"><div class="cx-acct-body"></div></div>');
		this.$body = this.root.find(".cx-acct-body");
		// Les chiffres et les liens ouvrent d'autres pages de Mon compte avec un filtre (route_options).
		this.root.on("click", "[data-go]", (e) => {
			e.preventDefault();
			const { go, kind, scope, period } = e.currentTarget.dataset;
			frappe.route_options = { kind: kind || "", scope: scope || "", period: period || "" };
			frappe.set_route("cortex-account", go);
		});
	}

	// ---------- utilitaires ----------
	call(method, args, type, scope) {
		return frappe.call({ method: `cortex_rental.api.v1.${scope || "account"}.${method}`, args, type: type || "GET", freeze: false }).then((r) => r.message);
	}

	esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	when(v) {
		return v ? this.esc(cortex.shortDateTime(String(v).length === 16 ? `${v}:00` : v)) : "—";
	}

	n(v) {
		return Number(v || 0).toLocaleString("fr-CA");
	}

	money(v) {
		return `${Number(v || 0).toLocaleString("fr-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} $`;
	}

	link(type, id) {
		if (!type || !id) return this.esc(id || "");
		return `<a href="/app/${frappe.router.slug(type)}/${encodeURIComponent(id)}">${this.esc(id)}</a>`;
	}

	toast(message, indicator) {
		frappe.show_alert({ message, indicator: indicator || "green" }, 5);
	}

	card(title, hint, inner, cls) {
		return $(`<section class="cx-acct-card ${cls || ""}">${title ? `<header><h2>${title}</h2>${hint ? `<p>${hint}</p>` : ""}</header>` : ""}${inner}</section>`);
	}

	// Carte pliable : le titre reste visible, le contenu se replie (pour garder la page courte).
	fold(title, hint, inner, open, count, summary) {
		return $(`<section class="cx-acct-card cx-fold"><details${open ? " open" : ""}><summary><span><h2>${title}</h2>${hint ? `<p>${hint}</p>` : ""}</span>${summary ? `<em class="cx-fold-sum">${summary}</em>` : ""}${count != null ? `<em class="cx-fold-count">${count}</em>` : '<em class="cx-fold-count"></em>'}<i class="cx-fold-chev" aria-hidden="true"></i></summary><div class="cx-fold-body">${inner}</div></details></section>`);
	}

	field(id, label, value, attrs) {
		return `<label class="cx-acct-field" for="${id}"><span>${label}</span><input id="${id}" value="${this.esc(value)}" ${attrs || ""}></label>`;
	}

	// Un chiffre ; avec `go`, il devient un lien vers la liste qui le compose.
	kpi(label, value, sub, tone, go) {
		const attrs = go ? ` href="#" data-go="${go.page}" data-kind="${go.kind || ""}" data-scope="${go.scope || ""}" data-period="${go.period || ""}"` : "";
		return `<${go ? "a" : "div"} class="cx-kpi${tone ? " " + tone : ""}${go ? " link" : ""}"${attrs}><span class="cx-kpi-v">${value}</span><span class="cx-kpi-l">${label}</span>${sub ? `<span class="cx-kpi-s">${sub}</span>` : ""}</${go ? "a" : "div"}>`;
	}

	empty(text) {
		return `<p class="cx-acct-muted cx-acct-empty">${text}</p>`;
	}

	table(head, rows, cls) {
		return `<div class="cx-table-wrap"><table class="cx-table ${cls || ""}"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
	}

	avatar(d, size) {
		const initials = (d.full_name || d.email).split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
		const style = `width:${size}px;height:${size}px`;
		return d.image ? `<img src="${this.esc(d.image)}" alt="" class="cx-acct-avatar" style="${style}">` : `<span class="cx-acct-avatar cx-acct-initials" style="${style};font-size:${Math.round(size / 3)}px">${this.esc(initials)}</span>`;
	}

	// ---------- cycle ----------
	show(tab) {
		this.tab = tab && this.PAGES[tab] ? tab : "profil";
		try {
			this.wrapper.page.set_title(this.PAGES[this.tab]);
		} catch (e) {
			// Le titre est aussi aligné par la barre latérale.
		}
		this.options = frappe.route_options || {};
		frappe.route_options = null;
		this.$body.empty();
		this.call("get_account").then((data) => {
			this.data = data;
			this.render();
		});
	}

	render() {
		const d = this.data;
		this.$body.empty();
		({ profil: () => this.renderProfile(d), statistiques: () => this.renderStats(), approbations: () => this.renderApprovals(), activite: () => this.renderHistory(), securite: () => this.renderSecurity(), notifications: () => this.renderNotifications(d), societe: () => this.renderCompany(d) })[this.tab]();
	}

	// ---------- Profil ----------
	renderProfile(d) {
		const hero = this.card(
			"",
			"",
			`<div class="cx-hero">
				<button type="button" class="cx-hero-photo" data-act="photo" aria-label="${__("Changer la photo de profil")}" title="${__("Changer la photo")}">${this.avatar(d, 80)}<span class="cx-hero-cam">${__("Modifier")}</span></button>
				<div class="cx-hero-id">
					<h2>${this.esc(d.full_name)}</h2>
					<p>${this.esc(d.email)}${d.company_title || d.company ? ` · ${this.esc(d.company_title || d.company)}` : ""}</p>
					<p class="cx-hero-role"><b>${this.esc(__(d.role.label))}</b> <span>${this.esc(__(d.role.help))}</span></p>
					<div class="cx-hero-actions"><button type="button" class="btn btn-default btn-sm" data-act="photo">${__("Changer la photo")}</button>${d.image ? ` <button type="button" class="btn btn-link btn-sm" data-act="photo-remove">${__("Retirer la photo")}</button>` : ""}<span class="cx-acct-muted">${__("PNG, JPEG ou WebP, 3 Mo au plus.")}</span></div>
				</div>
			</div>
			<div class="cx-hero-stats"><span class="cx-hero-cap">${__("30 derniers jours")}</span><div class="cx-hero-nums" aria-live="polite">${this.empty(__("Chargement…"))}</div></div>`,
			"hero-card"
		);
		hero.on("click", "[data-act=photo]", () => this.pickPhoto());
		hero.on("click", "[data-act=photo-remove]", () => this.call("update_photo", { file_url: "" }, "POST").then(() => window.location.reload()));
		this.call("stats", { period: "30" }).then((s) => {
			const w = s.work;
			const go = (kind) => ({ page: "activite", kind, period: "30" });
			hero.find(".cx-hero-nums").html(
				[
					[__("Devis créés"), w.quotes_created, go("quotes_created")],
					[__("Sorties"), w.checkouts, go("checkouts")],
					[__("Retours"), w.returns, go("returns")],
					[__("Approbations décidées"), s.approvals.approved_by_me + s.approvals.rejected_by_me, { page: "approbations" }],
					[__("Actions au total"), s.actions_total, { page: "activite", period: "30" }],
				]
					.map(([l, v, g]) => `<a href="#" class="cx-hero-num" data-go="${g.page}" data-kind="${g.kind || ""}" data-period="${g.period || ""}"><b>${this.n(v)}</b><span>${l}</span></a>`)
					.join("")
			);
		});

		const form = this.card(
			__("Mes informations"),
			__("Ces informations apparaissent sur vos actions (approbations, notes, journal d'audit)."),
			`<form class="cx-acct-form" novalidate>
				<div class="cx-acct-grid four">
					${this.field("cx-first", __("Prénom"), d.first_name, 'maxlength="80" autocomplete="given-name" required')}
					${this.field("cx-last", __("Nom"), d.last_name, 'maxlength="80" autocomplete="family-name"')}
					${this.field("cx-mail", __("Courriel"), d.email, 'readonly aria-describedby="cx-mail-h"')}
					${this.field("cx-tel", __("Téléphone"), d.mobile_no, 'maxlength="20" inputmode="tel" autocomplete="tel"')}
				</div>
				<p id="cx-mail-h" class="cx-acct-hint">${__("Votre courriel est votre identifiant : pour le changer, demandez à un administrateur de votre société.")}</p>
				<p class="cx-acct-err" role="alert" hidden></p>
				<div class="cx-acct-actions"><button type="submit" class="btn btn-primary btn-sm">${__("Enregistrer")}</button></div>
			</form>
			<dl class="cx-acct-meta"><div><dt>${__("Langue")}</dt><dd>${__("Français")}</dd></div><div><dt>${__("Fuseau horaire")}</dt><dd>${this.esc(d.time_zone || "—")}</dd></div><div><dt>${__("Membre depuis")}</dt><dd>${this.esc(d.member_since)}</dd></div><div><dt>${__("Dernière connexion")}</dt><dd>${this.when(d.last_login)}</dd></div></dl>`
		);
		form.find("form").on("submit", (e) => {
			e.preventDefault();
			const $err = form.find(".cx-acct-err").prop("hidden", true);
			const first = form.find("#cx-first").val().trim();
			if (!first) return $err.text(__("Le prénom est obligatoire.")).prop("hidden", false);
			const $btn = form.find("button[type=submit]").prop("disabled", true);
			this.call("update_profile", { first_name: first, last_name: form.find("#cx-last").val(), mobile_no: form.find("#cx-tel").val() }, "POST")
				.then((data) => {
					this.data = data;
					frappe.boot.user.fullname = data.full_name;
					this.toast(__("Profil enregistré."));
					this.render();
				})
				.catch(() => $btn.prop("disabled", false));
		});

		const todo = this.card(__("Ce qui m'attend"), __("Vos dossiers qui demandent une action maintenant. Chaque ligne ouvre la liste concernée."), `<ul class="cx-todo"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>`);
		this.call("todo").then((r) => {
			todo.find("ul").html(
				r.items
					.map((i) => `<li class="${i.tone}"><span class="cx-todo-n">${this.n(i.count)}</span><span class="cx-todo-l">${this.esc(__(i.label))}</span><a class="btn btn-default btn-xs" href="${this.esc(i.href)}">${i.count ? __("Ouvrir") : __("Voir")}</a></li>`)
					.join("") || `<li class="cx-acct-muted">${__("Rien ne vous attend.")}</li>`
			);
		});

		const me = encodeURIComponent(d.email);
		const quick = this.card(
			__("Raccourcis"),
			"",
			`<div class="cx-cta-row">
				<a class="btn btn-primary btn-sm" href="/app/cortex-rental-transaction/new">${__("Nouvelle location")}</a>
				<a class="btn btn-default btn-sm" href="/app/cortex-rental-transaction?owner=${me}&rental_state=Quote">${__("Mes devis ouverts")}</a>
				<a class="btn btn-default btn-sm" href="/app/cortex-rental-transaction?owner=${me}">${__("Toutes mes locations")}</a>
				<a class="btn btn-default btn-sm" href="/app/approval-request?requested_by_id=${me}">${__("Mes demandes d'approbation")}</a>
				<a class="btn btn-default btn-sm" href="/app/cortex-account/securite">${__("Mes appareils")}</a>
			</div>`
		);
		this.$body.append(hero, todo, form, quick);
	}

	pickPhoto() {
		new frappe.ui.FileUploader({
			as_dataurl: false,
			allow_multiple: false,
			restrictions: { allowed_file_types: [".png", ".jpg", ".jpeg", ".webp"], max_file_size: 3 * 1024 * 1024 },
			on_success: (file) => this.call("update_photo", { file_url: file.file_url }, "POST").then(() => window.location.reload()),
		});
	}

	// ---------- Statistiques ----------
	periodSelect(current, id) {
		const options = [["7", __("7 jours")], ["30", __("30 jours")], ["90", __("90 jours")], ["365", __("12 mois")], ["all", __("Depuis toujours")]];
		return `<label class="cx-acct-inline"><span>${__("Période")}</span><select id="${id}">${options.map(([v, l]) => `<option value="${v}"${v === current ? " selected" : ""}>${l}</option>`).join("")}</select></label>`;
	}

	renderStats() {
		const holder = $(`<div class="cx-acct-stats"><div class="cx-acct-toolbar">${this.periodSelect(this.period, "cx-period")}<span class="cx-acct-muted">${__("Chiffres tirés du journal d'audit et des dossiers : un zéro veut dire aucune action. Cliquez un chiffre pour voir ce qui le compose.")}</span></div><div class="cx-acct-statsbody">${this.empty(__("Chargement…"))}</div></div>`);
		holder.find("#cx-period").on("change", (e) => {
			this.period = e.target.value;
			this.fillStats(holder);
		});
		this.$body.append(holder);
		this.fillStats(holder);
	}

	// Page allégée : un graphique, puis une ligne par domaine avec son résumé ; le détail (les tuiles) se déplie à la demande.
	fillStats(holder) {
		this.call("stats", { period: this.period }).then((s) => {
			const w = s.work, a = s.approvals, e = s.equipment, m = s.money, c = s.conversion;
			const go = (kind, page) => ({ page: page || "activite", kind, period: this.period });
			const k = (l, v, sub, tone, g) => this.kpi(l, v, sub, tone, g);
			const tiles = (inner) => {
				const count = (inner.match(/class="cx-kpi(?![-\w])/g) || []).length - (inner.match(/class="cx-kpi wide/g) || []).length;
				const cols = count <= 4 ? Math.max(count, 1) : Math.ceil(count / 2);
				return `<div class="cx-kpis" style="grid-template-columns:repeat(${cols},minmax(0,1fr))">${inner}</div>`;
			};
			const row = (title, summary, inner, open) => this.fold(title, "", tiles(inner), open, null, summary);
			const max = Math.max(1, ...s.daily.map((d) => d.count));
			const bars = s.daily.map((d) => `<i title="${this.esc(d.date)} : ${d.count}" style="height:${Math.max(3, Math.round((d.count / max) * 100))}%" class="${d.count ? "on" : ""}"></i>`).join("");
			const top = e.top_items.length ? `<ol class="cx-top">${e.top_items.map((t) => `<li><span>${this.esc(t.item)}</span><b>${this.n(t.units)} ${__("unités")}</b></li>`).join("")}</ol>` : "";
			const pieces = (...p) => p.filter(Boolean).join(" · ");
			const top3 = this.card(
				__("Résumé"),
				`${this.n(s.actions_total)} ${__("actions")} · ${this.n(s.logins)} ${__("connexions")} · ${s.since ? __("depuis le {0}", [this.esc(s.since)]) : __("depuis toujours")} · <a href="#" data-go="activite" data-period="${this.period}">${__("Voir le détail : qui a fait quoi")}</a>`,
				`<div class="cx-headline">${[[__("Devis créés"), w.quotes_created, c.rate == null ? "" : `${c.rate} % ${__("devenus réservations")}`], [__("Réservations"), w.reservations, ""], [__("Locations sorties"), e.rentals_checked_out, ""], [__("Paiements enregistrés"), this.money(m.payments_recorded), ""]].map(([l, v, sub]) => `<div><b>${typeof v === "number" ? this.n(v) : v}</b><span>${l}</span>${sub ? `<small>${sub}</small>` : ""}</div>`).join("")}</div><div class="cx-bars" role="img" aria-label="${__("Actions par jour")}">${bars}</div><div class="cx-bars-axis"><span>${this.esc(s.daily[0].date)}</span><span>${this.esc(s.daily[s.daily.length - 1].date)}</span></div>`
			);
			holder.find(".cx-acct-statsbody").empty().append(
				top3,
				row(__("Locations"), pieces(`${this.n(w.quotes_created)} ${__("devis")}`, `${this.n(w.contracts)} ${__("contrats")}`, `${this.n(w.closed)} ${__("clôturées")}`), k(__("Devis créés"), this.n(w.quotes_created), "", "", go("quotes_created")) + k(__("Réservations"), this.n(w.reservations), "", "", go("reservations")) + k(__("Contrats confirmés"), this.n(w.contracts), "", "", go("contracts")) + k(__("Clôturées"), this.n(w.closed), "", "", go("closed")) + k(__("Annulées"), this.n(w.cancelled), "", "", go("cancelled")) + k(__("Litiges ouverts"), this.n(w.disputes), "", w.disputes ? "warn" : "", go("disputes")) + k(__("Devis partagés"), this.n(w.quotes_shared), "", "", go("quotes_shared")) + k(__("Clients ajoutés"), this.n(w.customers_added), "", "", go("customers_added")), false),
				row(__("Matériel emprunté"), pieces(`${this.n(e.units_checked_out)} ${__("unités sorties")}`, `${this.n(e.units_returned)} ${__("retournées")}`, e.returns_with_damage || e.items_missing ? `${this.n(e.returns_with_damage + e.items_missing)} ${__("à surveiller")}` : ""), k(__("Locations sorties"), this.n(e.rentals_checked_out), "", "", go("checkouts")) + k(__("Unités sorties"), this.n(e.units_checked_out)) + k(__("Unités retournées"), this.n(e.units_returned), "", "", go("returns")) + k(__("Retours abîmés"), this.n(e.returns_with_damage), "", e.returns_with_damage ? "warn" : "") + k(__("Manquants"), this.n(e.items_missing), "", e.items_missing ? "warn" : "") + (top ? `<div class="cx-kpi wide"><span class="cx-kpi-l">${__("Équipements les plus sortis")}</span>${top}</div>` : "")),
				row(__("Facturation"), pieces(`${this.n(w.invoices_issued)} ${__("factures")}`, this.money(m.quoted_value) + " " + __("de devis")), k(__("Factures émises"), this.n(w.invoices_issued), "", "", go("invoices_issued")) + k(__("Paiements enregistrés"), this.n(w.payments_recorded), this.money(m.payments_recorded), "", go("payments_recorded")) + k(__("Valeur des devis créés"), this.money(m.quoted_value))),
				row(__("Approbations"), pieces(`${this.n(a.approved_by_me + a.rejected_by_me)} ${__("décisions")}`, `${this.n(a.requested)} ${__("demandes")}`, a.my_requests_pending ? `${this.n(a.my_requests_pending)} ${__("en attente")}` : ""), k(__("Demandées par moi"), this.n(a.requested), "", "", { page: "approbations" }) + k(__("Approuvées par moi"), this.n(a.approved_by_me), "", "", { page: "approbations" }) + k(__("Refusées par moi"), this.n(a.rejected_by_me), "", "", { page: "approbations" }) + k(__("Retirées"), this.n(a.withdrawn), "", "", { page: "approbations" }) + k(__("Mes demandes en attente"), this.n(a.my_requests_pending), "", a.my_requests_pending ? "warn" : "", { page: "approbations" }) + k(__("À décider (autres)"), this.n(a.mine_to_decide), "", a.mine_to_decide ? "warn" : "", { page: "approbations" })),
				s.ai.visible ? row(__("Assistant IA"), pieces(`${this.n(s.ai.calls)} ${__("demandes")}`, this.money(s.ai.cost)), k(__("Demandes"), this.n(s.ai.calls)) + k(__("Jetons"), this.n(s.ai.tokens)) + k(__("Coût"), this.money(s.ai.cost))) : $()
			);
		});
	}

	// ---------- Approbations ----------
	renderApprovals() {
		const holder = $(`<div>${this.empty(__("Chargement…"))}</div>`);
		this.$body.append(holder);
		this.call("my_approvals").then((r) => {
			const chip = (status, label) => `<span class="cx-pill ${status === "Approved" ? "ok" : status === "Rejected" ? "no" : "wait"}">${this.esc(label)}</span>`;
			const rows = (list, who) =>
				list.map(
					(x) =>
						`<tr><td><a href="/app/approval-request/${encodeURIComponent(x.id)}">${this.esc(x.what)}</a><div class="cx-acct-muted">${this.when(x.created)}</div></td><td>${this.link(x.entity_type, x.entity_id)}</td><td>${chip(x.status, x.status_label)}${x.self_decided ? ` <span class="cx-pill self" title="${__("Seule personne autorisée de la société")}">${__("auto-approbation")}</span>` : ""}</td><td>${this.esc(who === "decided" ? x.decided_by || "—" : x.requested_by)}</td><td>${this.when(x.decided_at)}</td><td class="cx-reason">${this.esc(x.reason) || "—"}</td></tr>`
				);
			const approved = r.decided.filter((x) => x.status === "Approved").length;
			const rejected = r.decided.filter((x) => x.status === "Rejected").length;
			const pending = r.requested.filter((x) => x.status === "Pending").length;
			const headDecided = [__("Demande"), __("Élément"), __("Statut"), __("Demandée par"), __("Décidée le"), __("Motif")];
			const headAsked = [__("Demande"), __("Élément"), __("Statut"), __("Décidée par"), __("Décidée le"), __("Motif")];
			const exportRows = r.decided.map((x) => ({ type: __("Décision"), ...x })).concat(r.requested.map((x) => ({ type: __("Demande"), ...x })));
			holder.on("click", "[data-act=export]", () =>
				cortex.exportData({
					title: __("Mes approbations"),
					subtitle: `${r.decided.length} ${__("décision(s)")} · ${r.requested.length} ${__("demande(s)")}`,
					filename: "mes-approbations",
					columns: [
						{ key: "type", label: __("Type"), weight: 0.9 },
						{ key: "what", label: __("Demande"), weight: 1.8 },
						{ key: "entity_id", label: __("Élément"), weight: 1.5 },
						{ key: "status_label", label: __("Statut"), weight: 1 },
						{ key: "requested_by", label: __("Demandée par"), weight: 1.7 },
						{ key: "decided_by", label: __("Décidée par"), weight: 1.7 },
						{ key: "decided_at", label: __("Décidée le"), weight: 1.2 },
						{ key: "reason", label: __("Motif"), weight: 2 },
					],
					rows: exportRows,
				})
			);
			holder.empty().append(
				this.card("", "", `<div class="cx-kpis inline">${this.kpi(__("Approuvées par moi"), this.n(approved))}${this.kpi(__("Refusées par moi"), this.n(rejected))}${this.kpi(__("Mes demandes"), this.n(r.requested.length))}${this.kpi(__("En attente"), this.n(pending), "", pending ? "warn" : "")}</div><div class="cx-cta-row"><a class="btn btn-primary btn-sm" href="/app/approval-request">${__("Demander une approbation")}</a><a class="btn btn-default btn-sm" href="/app/approval-request?status=Pending">${__("Voir celles à décider")}</a><button type="button" class="btn btn-default btn-sm cx-push" data-act="export">${__("Exporter")}</button></div>`),
				this.card(__("Mes décisions"), __("Les demandes des autres que vous avez approuvées ou refusées, avec le motif."), r.decided.length ? this.table(headDecided, rows(r.decided, "asked")) : this.empty(__("Aucune décision pour l'instant."))),
				this.card(__("Mes demandes"), __("Ce que vous avez soumis, et ce qui en est advenu."), r.requested.length ? this.table(headAsked, rows(r.requested, "decided")) : this.empty(__("Aucune demande pour l'instant.")))
			);
		});
	}

	// ---------- Activité (historique complet, moi ou toute l'équipe) ----------
	renderHistory() {
		const o = this.options || {};
		this.hist = { items: [], offset: 0, category: "", period: o.period || "90", scope: o.scope === "team" ? "team" : "me", kind: o.kind || "" };
		const kinds = [["", __("Toutes les actions")], ["quotes_created", __("Devis créés")], ["reservations", __("Réservations")], ["contracts", __("Contrats confirmés")], ["checkouts", __("Sorties")], ["returns", __("Retours")], ["closed", __("Clôtures")], ["cancelled", __("Annulations")], ["disputes", __("Litiges")], ["quotes_shared", __("Devis partagés")], ["customers_added", __("Clients ajoutés")], ["invoices_issued", __("Factures émises")], ["payments_recorded", __("Paiements enregistrés")], ["approvals", __("Approbations")]];
		const card = this.card(
			"",
			"",
			`<div class="cx-acct-toolbar">
				<div class="cx-seg" role="group" aria-label="${__("Qui")}"><button type="button" data-scope="me" class="${this.hist.scope === "me" ? "on" : ""}">${__("Moi")}</button><button type="button" data-scope="team" class="${this.hist.scope === "team" ? "on" : ""}" hidden>${__("Toute l'équipe")}</button></div>
				<label class="cx-acct-inline"><span>${__("Action")}</span><select id="cx-h-kind">${kinds.map(([v, l]) => `<option value="${v}"${v === this.hist.kind ? " selected" : ""}>${l}</option>`).join("")}</select></label>
				${this.periodSelect(this.hist.period, "cx-h-period")}
				<button type="button" class="btn btn-default btn-sm cx-push" data-act="export">${__("Exporter")}</button>
			</div>
			<ul class="cx-acct-list cx-timeline"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>
			<div class="cx-acct-actions center"><button type="button" class="btn btn-default btn-sm" data-act="more" hidden>${__("Voir plus")}</button><span class="cx-acct-muted" data-role="count"></span></div>`
		);
		const reload = () => {
			this.hist = { ...this.hist, items: [], offset: 0, kind: card.find("#cx-h-kind").val(), period: card.find("#cx-h-period").val() };
			this.loadHistory(card, true);
		};
		card.on("change", "#cx-h-kind, #cx-h-period", reload);
		card.on("click", "[data-scope]", (e) => {
			card.find("[data-scope]").removeClass("on");
			$(e.currentTarget).addClass("on");
			this.hist.scope = e.currentTarget.dataset.scope;
			reload();
		});
		card.on("click", "[data-act=more]", () => this.loadHistory(card, false));
		card.on("click", "[data-act=export]", () => this.exportHistory());
		this.$body.append(card);
		this.loadHistory(card, true);
	}

	loadHistory(card, reset) {
		const h = this.hist;
		this.call("history", { category: "", kind: h.kind, period: h.period, limit: 30, offset: h.offset, scope: h.scope }).then((r) => {
			card.find("[data-scope=team]").prop("hidden", !r.can_team);
			h.items = reset ? r.items : h.items.concat(r.items);
			h.offset = h.items.length;
			const rows = h.items.map((a) => {
				const who = h.scope === "team" ? `<b>${this.esc(a.you ? __("Vous") : a.actor)}</b> · ` : "";
				const approval = a.requested_by || a.confirmed_by ? `<em>${a.requested_by ? `${__("Demandée par")} ${this.esc(a.requested_by)}` : ""}${a.requested_by && a.confirmed_by ? " · " : ""}${a.confirmed_by ? `${__("Confirmée par")} ${this.esc(a.confirmed_by)}` : ""}</em>` : "";
				return `<li><span class="cx-tl-dot ${this.esc(a.category)}"></span><span class="cx-tl-main">${who}${this.esc(a.text)} ${this.link(a.entity_type, a.entity_id)}${a.detail ? `<em>« ${this.esc(a.detail)} »</em>` : ""}${approval}</span><span class="cx-acct-muted">${this.when(a.at)}</span></li>`;
			});
			card.find("ul").html(rows.join("") || `<li class="cx-acct-muted">${__("Aucune action dans cette période.")}</li>`);
			card.find("[data-act=more]").prop("hidden", !r.has_more);
			card.find("[data-role=count]").text(`${h.items.length} / ${r.total}`);
		});
	}

	// Un seul bouton : la fenêtre « Exporter » demande PDF ou CSV. On charge jusqu'à 500 lignes du filtre courant.
	async exportHistory() {
		const h = this.hist;
		const rows = [];
		let offset = 0;
		for (let guard = 0; guard < 5; guard++) {
			const r = await this.call("history", { category: "", kind: h.kind, period: h.period, limit: 100, offset, scope: h.scope });
			rows.push(...r.items);
			offset += r.items.length;
			if (!r.has_more || !r.items.length) break;
		}
		const periods = { 7: __("7 jours"), 30: __("30 jours"), 90: __("90 jours"), 365: __("12 mois"), all: __("depuis toujours") };
		cortex.exportData({
			title: h.scope === "team" ? __("Activité de l'équipe") : __("Mon activité"),
			subtitle: `${__("Période")} : ${periods[h.period] || h.period} · ${rows.length} ${__("ligne(s)")}`,
			filename: h.scope === "team" ? "activite-equipe" : "mon-activite",
			columns: [
				{ key: "at", label: __("Date"), weight: 1.1 },
				{ key: "actor", label: __("Personne"), weight: 1.3 },
				{ key: "text", label: __("Action"), weight: 1.8 },
				{ key: "entity_id", label: __("Élément"), weight: 1.5 },
				{ key: "who", label: __("Demandée / confirmée par"), weight: 2 },
				{ key: "detail", label: __("Détail"), weight: 2.2 },
			],
			rows: rows.map((a) => ({ ...a, who: [a.requested_by && `${__("demandée par")} ${a.requested_by}`, a.confirmed_by && `${__("confirmée par")} ${a.confirmed_by}`].filter(Boolean).join(" · ") })),
		});
	}

	// ---------- Sécurité : une seule colonne ----------
	renderSecurity() {
		const pass = this.card(
			__("Mot de passe"),
			__("Au moins 10 caractères. Après le changement, vos autres appareils sont déconnectés."),
			`<form class="cx-acct-form" novalidate autocomplete="off">
				<div class="cx-acct-grid three">
					${this.field("cx-old", __("Mot de passe actuel"), "", 'type="password" autocomplete="current-password" required')}
					${this.field("cx-new", __("Nouveau mot de passe"), "", 'type="password" autocomplete="new-password" minlength="10" required')}
					${this.field("cx-new2", __("Confirmer le nouveau mot de passe"), "", 'type="password" autocomplete="new-password" required')}
				</div>
				<p class="cx-acct-err" role="alert" hidden></p>
				<div class="cx-acct-actions"><button type="submit" class="btn btn-primary btn-sm">${__("Changer le mot de passe")}</button></div>
			</form>`
		);
		pass.find("form").on("submit", (e) => {
			e.preventDefault();
			const $err = pass.find(".cx-acct-err").prop("hidden", true);
			const fail = (t) => $err.text(t).prop("hidden", false);
			const [o, n, n2] = ["#cx-old", "#cx-new", "#cx-new2"].map((s) => pass.find(s).val());
			if (!o) return fail(__("Saisissez votre mot de passe actuel."));
			if (n.length < 10) return fail(__("Le nouveau mot de passe doit contenir au moins 10 caractères."));
			if (n !== n2) return fail(__("Les deux nouveaux mots de passe ne sont pas identiques."));
			const $btn = pass.find("button[type=submit]").prop("disabled", true);
			this.call("change_password", { old_password: o, new_password: n }, "POST")
				.then((r) => {
					this.toast(r.other_sessions_closed ? __("Mot de passe changé. {0} autre(s) appareil(s) déconnecté(s).", [r.other_sessions_closed]) : __("Mot de passe changé."));
					pass.find("form")[0].reset();
					this.loadSessions(sessions);
				})
				.catch(() => {})
				.finally(() => $btn.prop("disabled", false));
		});

		const sessions = this.fold(
			__("Appareils connectés"),
			__("Chaque session ouverte avec votre compte : appareil, système, adresse IP et dernière activité."),
			`<ul class="cx-devices" aria-live="polite"><li class="cx-acct-muted">${__("Chargement…")}</li></ul><p class="cx-acct-hint" data-role="note"></p><div class="cx-acct-actions"><button type="button" class="btn btn-default btn-sm" data-act="others">${__("Déconnecter tous les autres appareils")}</button></div>`,
			true
		);
		sessions.on("click", "[data-act=others]", () =>
			frappe.confirm(__("Déconnecter tous les autres appareils ? Ils devront se reconnecter."), () =>
				this.call("sign_out_other_sessions", {}, "POST").then((r) => {
					this.toast(__("{0} appareil(s) déconnecté(s).", [r.closed]));
					this.loadSessions(sessions);
				})
			)
		);
		sessions.on("click", "[data-device]:not([data-member])", (e) => {
			const { device, label } = e.currentTarget.dataset;
			frappe.confirm(__("Déconnecter « {0} » ? L'appareil devra se reconnecter.", [this.esc(label)]), () =>
				this.call("sign_out_session", { device_id: device }, "POST").then(() => {
					this.toast(__("Appareil déconnecté."));
					this.loadSessions(sessions);
				})
			);
		});

		const logins = this.fold(__("Historique des connexions"), __("Vos dernières ouvertures de session, réussies ou refusées."), `<div class="cx-acct-muted">${__("Chargement…")}</div>`, false);
		this.call("login_history", { limit: 20 }).then((r) => {
			const row = (l) => `<tr><td>${this.when(l.at)}</td><td><span class="cx-pill ${l.ok ? "ok" : "no"}">${l.ok ? __("Réussie") : __("Refusée")}</span></td><td>${this.esc(l.ip) || "—"}</td></tr>`;
			logins.find(".cx-fold-body").html(r.logins.length ? this.table([__("Date"), __("Résultat"), __("Adresse IP")], r.logins.map(row)) : this.empty(__("Aucune connexion enregistrée.")));
			logins.find(".cx-fold-count").text(r.logins.length);
		});

		this.$body.append(pass, sessions, logins);
		this.loadSessions(sessions);
		this.maybeTeamDevices();
	}

	deviceIcon(type) {
		const paths = {
			"Téléphone": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
			"Tablette": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M11 18h2"/>',
			"Ordinateur": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M2 20h20"/>',
		};
		return `<svg class="cx-dev-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">${paths[type] || '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01"/>'}</svg>`;
	}

	deviceRow(s, button) {
		const facts = [s.browser && `${__("Navigateur")} : ${this.esc(s.browser)}`, s.os && `${__("Système")} : ${this.esc(s.os)}`, s.model && `${__("Modèle")} : ${this.esc(s.model)}`, `${__("Adresse IP")} : ${this.esc(s.ip) || "—"}`, s.signed_in_at && `${__("Connecté le")} ${this.when(s.signed_in_at)}`, `${__("Dernière activité")} ${this.when(s.last_active)}`].filter(Boolean);
		return `<li class="${s.current ? "current" : ""}">${this.deviceIcon(s.type)}<div class="cx-dev-main"><div class="cx-dev-title"><b>${this.esc(s.label)}</b>${s.current ? `<span class="cx-pill ok">${__("Cet appareil")}</span>` : ""}${s.identified ? "" : `<span class="cx-pill wait" title="${__("Session ouverte avant le suivi des appareils : l'appareil n'est pas connu.")}">${__("Non identifié")}</span>`}</div><div class="cx-dev-facts">${facts.map((f) => `<span>${f}</span>`).join("")}</div></div>${button}</li>`;
	}

	// Au plus 5 appareils sont montrés d'abord (les plus récents) ; le reste se déplie à la demande.
	deviceList(sessions, buttonFor) {
		const VISIBLE = 5;
		const rows = sessions.map((s) => this.deviceRow(s, buttonFor(s)));
		if (!rows.length) return `<li class="cx-acct-muted">${__("Aucune session.")}</li>`;
		const rest = rows.slice(VISIBLE);
		return rows.slice(0, VISIBLE).join("") + (rest.length ? `<li class="cx-more"><details><summary>${__("Voir les {0} autres sessions", [rest.length])}</summary><ul class="cx-devices">${rest.join("")}</ul></details></li>` : "");
	}

	loadSessions(card) {
		this.call("list_sessions").then((r) => {
			const button = (s) => (s.current ? "" : `<button type="button" class="btn btn-default btn-xs cx-danger" data-device="${this.esc(s.id)}" data-label="${this.esc(s.label)}">${__("Déconnecter")}</button>`);
			card.find(".cx-fold-body > ul.cx-devices").html(this.deviceList(r.sessions, button));
			card.find("[data-role=note]").text(r.tracking_note ? __(r.tracking_note) : "");
			card.find("[data-act=others]").prop("hidden", r.sessions.filter((s) => !s.current).length === 0);
			card.find(".cx-fold-count").text(r.sessions.length);
		});
	}

	// Les administrateurs voient les appareils de l'équipe et peuvent déconnecter un membre (téléphone perdu, départ).
	maybeTeamDevices() {
		this.call("company_overview").then((o) => {
			if (!o.can_manage_team) return;
			const card = this.fold(__("Appareils de l'équipe"), __("Visible aux administrateurs : déconnectez un appareil perdu ou toutes les sessions d'une personne qui quitte l'équipe."), `<div class="cx-team-dev">${this.empty(__("Chargement…"))}</div>`, false);
			this.$body.append(card);
			const load = () =>
				this.call("team_devices", {}, "GET", "administration").then((r) => {
					const data = (r && r.data) || r || {};
					card.find(".cx-fold-count").text((data.members || []).length);
					card.find(".cx-team-dev").html(
						(data.members || [])
							.map((m) => {
								const button = (s) => (s.current ? "" : `<button type="button" class="btn btn-default btn-xs cx-danger" data-member="${this.esc(m.email)}" data-device="${this.esc(s.id)}" data-label="${this.esc(s.label)}">${__("Déconnecter")}</button>`);
								const all = m.sessions.filter((s) => !s.current).length && !m.you ? `<button type="button" class="btn btn-default btn-xs cx-danger" data-member="${this.esc(m.email)}">${__("Tout déconnecter")}</button>` : "";
								return `<details class="cx-team-member"><summary><b>${this.esc(m.full_name)}</b> <span class="cx-acct-muted">${this.esc(m.email)}${m.you ? ` · ${__("vous")}` : ""} · ${m.sessions.length} ${__("session(s)")}</span></summary>${all ? `<div class="cx-team-all">${all}</div>` : ""}<ul class="cx-devices">${this.deviceList(m.sessions, button)}</ul></details>`;
							})
							.join("")
					);
				});
			card.on("click", "[data-member]", (e) => {
				const { member, device } = e.currentTarget.dataset;
				frappe.confirm(device ? __("Déconnecter cet appareil ?") : __("Déconnecter toutes les sessions de {0} ?", [this.esc(member)]), () =>
					this.call("sign_out_member", { email: member, device_id: device || "" }, "POST", "administration").then((r) => {
						const data = (r && r.data) || r || {};
						if (data.ok === false) return frappe.msgprint(this.esc(data.message || ""));
						this.toast(__("{0} session(s) fermée(s).", [data.closed || 0]));
						load();
					})
				);
			});
			load();
		});
	}

	// ---------- Notifications ----------
	renderNotifications(d) {
		const inbox = this.card(__("Boîte de notifications"), __("Les alertes reçues dans l'application (la cloche)."), `<div class="cx-acct-actions top"><span class="cx-acct-muted" data-role="unread"></span><button type="button" class="btn btn-default btn-sm" data-act="readall">${__("Tout marquer comme lu")}</button></div><ul class="cx-acct-list cx-inbox"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>`);
		const loadInbox = () =>
			this.call("inbox", { limit: 30 }).then((r) => {
				inbox.find("[data-role=unread]").text(r.unread ? __("{0} non lue(s)", [r.unread]) : __("Tout est lu."));
				inbox.find("[data-act=readall]").prop("hidden", !r.unread);
				const text = (n) => (n.entity_id && n.text.includes(n.entity_id) ? this.esc(n.text).replace(this.esc(n.entity_id), this.link(n.entity_type, n.entity_id)) : this.esc(n.text) + (n.entity_id ? ` ${this.link(n.entity_type, n.entity_id)}` : ""));
				inbox.find("ul").html(r.items.map((n) => `<li class="${n.read ? "" : "unread"}"><span class="cx-tl-main">${n.read ? "" : `<i class="cx-dot" aria-label="${__("non lue")}"></i>`}${text(n)}</span><span class="cx-acct-muted">${this.when(n.at)}</span></li>`).join("") || `<li class="cx-acct-muted">${__("Aucune notification.")}</li>`);
			});
		inbox.on("click", "[data-act=readall]", () => this.call("mark_all_read", {}, "POST").then(() => loadInbox()));
		loadInbox();

		const prefs = this.card(__("Alertes de Cortex"), __("Choisissez celles que vous voulez recevoir dans l'application. Elles ne modifient aucun dossier."), `<div class="cx-acct-switches"></div>`);
		this.call("preferences").then((p) => {
			prefs.find(".cx-acct-switches").html(Object.entries(p.labels).map(([key, label]) => `<label class="cx-acct-switch"><input type="checkbox" data-pref="${key}" ${p.values[key] ? "checked" : ""}><span>${this.esc(__(label))}</span></label>`).join(""));
		});
		prefs.on("change", "input[data-pref]", (e) => {
			const box = e.currentTarget;
			this.call("update_preferences", { values: JSON.stringify({ [box.dataset.pref]: box.checked ? 1 : 0 }) }, "POST")
				.then(() => this.toast(__("Préférence enregistrée.")))
				.catch(() => (box.checked = !box.checked));
		});

		const n = d.notifications;
		const rows = Object.entries(n.labels).map(([key, label]) => `<label class="cx-acct-switch"><input type="checkbox" data-key="${key}" ${n.values[key] ? "checked" : ""}><span>${this.esc(__(label))}</span></label>`).join("");
		const mail = this.card(__("Notifications par courriel"), __("Les alertes dans l'application (cloche) restent toujours actives."), `<div class="cx-acct-switches">${rows}</div>`);
		mail.on("change", "input[data-key]", (e) => {
			const box = e.currentTarget;
			this.call("update_notifications", { values: JSON.stringify({ [box.dataset.key]: box.checked ? 1 : 0 }) }, "POST")
				.then((res) => {
					this.data.notifications = res;
					this.toast(__("Préférence enregistrée."));
				})
				.catch(() => (box.checked = !box.checked));
		});
		this.$body.append(inbox, prefs, mail);
	}

	// Cartes réservées au propriétaire : logo de la société et règle d'auto-approbation (avec son explication).
	ownerCards(after, d) {
		const logo = this.card(
			__("Logo de la société"),
			__("Il apparaît dans la barre latérale, sur les devis envoyés à vos clients et à l'accueil de votre équipe. PNG, JPEG ou WebP, 2 Mo au plus."),
			`<div class="cx-logo-row"><div class="cx-logo-preview">${d.company_logo ? `<img src="${this.esc(d.company_logo)}" alt="${__("Logo actuel")}">` : `<span class="cx-acct-muted">${__("Aucun logo")}</span>`}</div><div class="cx-hero-actions"><button type="button" class="btn btn-primary btn-sm" data-act="logo">${d.company_logo ? __("Changer le logo") : __("Ajouter un logo")}</button>${d.company_logo ? `<button type="button" class="btn btn-link btn-sm" data-act="logo-remove">${__("Retirer")}</button>` : ""}</div></div>`
		);
		const done = () => window.location.reload();
		logo.on("click", "[data-act=logo]", () =>
			new frappe.ui.FileUploader({
				as_dataurl: false,
				allow_multiple: false,
				restrictions: { allowed_file_types: [".png", ".jpg", ".jpeg", ".webp"], max_file_size: 2 * 1024 * 1024 },
				on_success: (file) =>
					this.call("set_company_logo", { file_url: file.file_url }, "POST", "administration").then((r) => {
						const data = (r && r.data) || r || {};
						if (data.ok === false) return frappe.msgprint(this.esc(data.message || ""));
						done();
					}),
			})
		);
		logo.on("click", "[data-act=logo-remove]", () => this.call("set_company_logo", { file_url: "" }, "POST", "administration").then(done));
		const rule = this.card(
			__("Approbations"),
			__("Par défaut, une personne ne peut pas approuver sa propre demande : une deuxième personne autorisée doit la décider."),
			`<p class="cx-acct-muted" data-role="policy">${__("Chargement…")}</p><div class="cx-cta-row"><button type="button" class="btn btn-default btn-sm" data-act="policy">${__("Comprendre et décider")}</button></div>`
		);
		const refresh = () =>
			this.call("self_approval_policy", {}, "GET", "approval_queue").then((p) => {
				rule.find("[data-role=policy]").text(p.enabled ? (p.sole_approver ? __("Auto-approbation activée : vous pouvez approuver vos propres demandes, car vous êtes la seule personne autorisée.") : __("Auto-approbation activée, mais elle ne s'applique pas : une autre personne autorisée existe.")) : __("Auto-approbation désactivée (réglage prudent)."));
			});
		rule.on("click", "[data-act=policy]", () => cortex.selfApprovalDialog(refresh));
		refresh();
		after.after(logo, rule);
	}

	// ---------- Société et rôles : une seule colonne ----------
	// Profil en lecture seule d'une personne de la société : tout compte de la société peut le consulter, seul le
	// propriétaire gère les comptes (page « Équipe et règles »). Le temps d'utilisation n'est pas mesuré : jamais affiché.
	showColleague(email) {
		this.call("colleague_profile", { email }).then((p) => {
			const dialog = new frappe.ui.Dialog({ title: p.name });
			const photo = p.photo ? `<img src="${this.esc(p.photo)}" alt="" width="64" height="64" style="border-radius:50%;object-fit:cover">` : `<span class="cx-avatar cx-avatar-initials" style="width:64px;height:64px;display:grid;place-items:center;border-radius:50%;background:#eef3ef">${this.esc((p.name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase())}</span>`;
			const line = (label, value) => (value ? `<div><dt>${label}</dt><dd>${value}</dd></div>` : "");
			const presence = p.online ? `<span class="indicator-pill green">${__("En ligne")}</span>` : `<span class="text-muted">${p.last_active ? __("Vu {0}", [this.when(p.last_active)]) : __("Jamais connecté")}</span>`;
			const recent = p.recent.length ? `<ul class="cx-todo">${p.recent.map((r) => `<li>${this.esc(r.text)} <span class="cx-acct-muted">· ${this.when(r.at)}</span></li>`).join("")}</ul>` : `<p class="cx-acct-muted">${__("Aucune action enregistrée.")}</p>`;
			const contact = [p.email ? `<a class="btn btn-default btn-sm" href="mailto:${this.esc(p.email)}">${__("Écrire un courriel")}</a>` : "", p.phone ? `<a class="btn btn-default btn-sm" href="tel:${this.esc(p.phone)}">${__("Appeler")}</a>` : ""].join(" ");
			dialog.$body.html(
				`<div style="display:flex;gap:14px;align-items:center;margin-bottom:12px">${photo}<div><b>${this.esc(__(p.role.label))}</b><div>${presence}</div>${p.enabled ? "" : `<div class="text-muted">${__("Compte désactivé")}</div>`}</div></div>
				<dl class="cx-acct-meta">${line(__("Courriel"), this.esc(p.email))}${line(__("Téléphone"), this.esc(p.phone))}${line(__("Membre depuis"), this.esc(p.member_since))}${line(__("Connexions (30 jours)"), this.n(p.logins_30d))}${line(__("Actions (30 jours)"), this.n(p.actions_30d))}</dl>
				<h6>${__("Activité récente")}</h6>${recent}<div style="margin-top:10px">${contact}</div>
				<p class="cx-acct-muted" style="margin-top:10px">${__("Le temps d'utilisation n'est pas mesuré par Cortex.")}</p>`
			);
			dialog.show();
		});
	}

	renderCompany(d) {
		const head = this.card(
			"",
			"",
			`<div class="cx-co-head">${d.company_logo ? `<img src="${this.esc(d.company_logo)}" alt="" class="cx-co-logo">` : ""}<div><h2>${this.esc(d.company_title || d.company || "—")}</h2><p class="cx-co-role"><b>${this.esc(__(d.role.label))}</b> <span>${this.esc(__(d.role.help))}</span></p></div></div><div class="cx-cta-row cx-co-cta" hidden></div>`
		);
		const stats = this.card(__("Votre société en chiffres"), __("Lus dans vos dossiers. Une tuile absente veut dire que votre rôle ne donne pas accès à ces données."), `<div class="cx-co-stats"><p class="cx-acct-muted">${__("Chargement…")}</p></div>`);
		this.call("company_stats").then((c) => {
			const tile = (label, value, href, note) => `<a class="cx-hero-num" href="${this.esc(href || "#")}"><b>${value}</b><span>${label}</span>${note ? `<small>${note}</small>` : ""}</a>`;
			const tiles = [];
			if (c.team) tiles.push(tile(__("Personnes actives"), this.n(c.team.active), "/app/cortex-admin"));
			if (c.customers) tiles.push(tile(__("Clients actifs"), this.n(c.customers.active), "/app/customer"));
			if (c.equipment) {
				const u = c.equipment.units;
				const out = u ? Object.entries(u).filter(([k]) => k !== "Active" && u[k]).map(([k, n]) => `${n} ${__(({ Quarantine: "en quarantaine", "Under Repair": "en réparation", Missing: "manquant", Decommissioned: "retiré" })[k] || k)}`).join(" · ") : "";
				tiles.push(tile(__("Équipements au catalogue"), this.n(c.equipment.items), "/app/cortex-rental-item-profile", u ? `${this.n(u.Active || 0)} ${__("unités actives")}${out ? " · " + out : ""}` : ""));
			}
			if (c.rentals) {
				tiles.push(tile(__("Locations en cours"), this.n(c.rentals.open), "/app/cortex-rental-transaction?rental_state=%5B%22in%22%2C%5B%22Reservation%22%2C%22Contract%22%2C%22Checked%20Out%22%5D%5D"));
				tiles.push(tile(__("Devis ouverts"), this.n(c.rentals.quotes), "/app/cortex-rental-transaction?rental_state=Quote"));
				tiles.push(tile(__("Créés en {0} jours", [c.period_days]), this.n(c.rentals.created), "/app/cortex-rental-transaction"));
				tiles.push(tile(__("Retours en retard"), this.n(c.rentals.late_returns), "/app/cortex-rental-transaction?rental_state=Checked%20Out", c.rentals.late_returns ? __("à relancer") : ""));
			}
			if (c.billing) {
				tiles.push(tile(__("Facturé en {0} jours", [c.period_days]), this.money(c.billing.invoiced), "/app/cortex-rental-invoice"));
				if (c.billing.collected !== null) tiles.push(tile(__("Encaissé en {0} jours", [c.period_days]), this.money(c.billing.collected), "/app/cortex-rental-payment"));
				tiles.push(tile(__("Solde dû"), this.money(c.billing.outstanding), "/app/cortex-rental-invoice?status=%5B%22in%22%2C%5B%22Issued%22%2C%22Partially%20Paid%22%5D%5D", `${this.n(c.billing.outstanding_count)} ${__("factures")}`));
			}
			stats.find(".cx-co-stats").html(tiles.length ? `<div class="cx-hero-nums">${tiles.join("")}</div>` : `<p class="cx-acct-muted">${__("Votre rôle ne donne accès à aucune statistique de la société.")}</p>`);
		}).catch(() => stats.find(".cx-co-stats").html(`<p class="cx-acct-muted">${__("Les statistiques sont indisponibles pour le moment. Réessayez dans un instant.")}</p>`));
		const ai = this.card(__("Assistant IA ce mois-ci"), __("Consommation de votre société."), `<div class="cx-acct-ai"><p class="cx-acct-muted">${__("Chargement…")}</p></div>`);
		const rights = this.card(__("Mes droits"), __("Ce que votre compte peut faire, écran par écran. Ils découlent de votre rôle : un administrateur peut les ajuster dans « Équipe et règles »."), `<div class="cx-acct-muted">${__("Chargement…")}</div>`);
		const team = this.card(__("Mon équipe"), __("Les personnes actives de votre société et leur rôle."), `<div class="cx-acct-muted">${__("Chargement…")}</div>`);
		this.call("company_overview").then((o) => {
			if (o.can_manage_team) this.ownerCards(head, d);
			const mark = (v) => (v ? `<span class="cx-yes" aria-label="${__("oui")}">✓</span>` : `<span class="cx-no" aria-label="${__("non")}">—</span>`);
			rights.find(".cx-acct-muted").replaceWith(
				this.table([__("Écran"), __("Voir"), __("Créer"), __("Modifier"), ""], o.rights.map((r) => `<tr><td>${this.esc(__(r.area))}</td><td class="c">${mark(r.read)}</td><td class="c">${mark(r.create)}</td><td class="c">${mark(r.write)}</td><td class="r">${r.href ? `<a href="${this.esc(r.href)}">${__("Ouvrir")}</a>` : ""}</td></tr>`), "rights")
			);
			team.find(".cx-acct-muted").replaceWith(
				this.table([__("Personne"), __("Rôle"), __("Dernière activité")], o.team.map((m) => `<tr><td><a href="#" class="cx-person" data-person="${this.esc(m.id)}"><b>${this.esc(m.name)}</b></a>${m.you ? ` <span class="cx-acct-muted">(${__("vous")})</span>` : ""}${m.email ? `<div class="cx-acct-muted">${this.esc(m.email)}</div>` : ""}</td><td>${this.esc(__(m.role))}</td><td class="cx-acct-muted">${m.last_active ? this.when(m.last_active) : "—"}</td></tr>`))
			);
			if (o.can_manage_team) this.card(__("Configuration de l'entreprise"), __("Reprenez l'assistant de configuration (entreprise, équipe, catalogue, taxes) à tout moment."), `<a class="btn btn-default btn-sm" href="/app/cortex-setup">${__("Ouvrir la configuration")}</a>`).insertAfter(head);
			if (o.can_manage_team) head.find(".cx-co-cta").prop("hidden", false).html(`<a class="btn btn-primary btn-sm" href="/app/cortex-admin">${__("Gérer l'équipe et les rôles")}</a><a class="btn btn-default btn-sm" href="/app/cortex-account/securite">${__("Appareils de l'équipe")}</a><a class="btn btn-default btn-sm" data-go="activite" data-scope="team" href="#">${__("Activité de l'équipe")}</a>`);
		});
		team.on("click", "[data-person]", (e) => {
			e.preventDefault();
			this.showColleague($(e.currentTarget).data("person"));
		});
		this.call("ai_usage").then((u) => {
			const $box = ai.find(".cx-acct-ai");
			if (!u.visible) return $box.html(`<p class="cx-acct-muted">${__("Votre rôle ne donne pas accès à la consommation de l'IA.")}</p>`);
			const pct = u.cost_cap || u.token_cap ? Math.min(100, u.percent) : 0;
			const label = u.cost_cap ? `${u.cost.toFixed(2)} $ / ${u.cost_cap.toFixed(0)} $` : `${u.tokens.toLocaleString("fr-CA")} ${__("jetons")}`;
			const note = u.economy ? __("Plafond atteint : l'assistant utilise un modèle plus économique.") : u.blocked ? __("Plafond dépassé : l'assistant est en pause jusqu'au mois prochain.") : u.warning ? __("Vous approchez du plafond mensuel.") : "";
			$box.html(`<div class="cx-acct-bar" role="img" aria-label="${pct} %"><i style="width:${pct}%"></i></div><p><strong>${label}</strong> · ${u.calls} ${__("appels")}${u.cost_cap ? ` · ${u.percent} %` : ""}</p>${note ? `<p class="cx-acct-note">${note}</p>` : ""}`);
		});
		this.$body.append(head, stats, ai, rights, team);
	}
};
