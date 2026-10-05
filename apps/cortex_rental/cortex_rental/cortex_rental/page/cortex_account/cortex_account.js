// Mon compte : profil, statistiques, approbations, activité, sécurité (appareils), notifications, société et rôles.
// Chaque action passe par cortex_rental.api.v1.account.* (ou administration.* pour l'équipe) et ne concerne que la
// personne connectée ; les chiffres viennent des dossiers réels, jamais d'une estimation.
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
		this.TABS = [
			["profil", __("Profil")],
			["statistiques", __("Statistiques")],
			["approbations", __("Approbations")],
			["activite", __("Activité")],
			["securite", __("Sécurité")],
			["notifications", __("Notifications")],
			["societe", __("Société et rôles")],
		];
		this.root.html(`<div class="cx-acct"><div class="cx-acct-hero"></div><nav class="cx-acct-tabs" role="tablist" aria-label="${__("Sections du compte")}"></nav><div class="cx-acct-body" role="tabpanel"></div></div>`);
		this.$hero = this.root.find(".cx-acct-hero");
		this.$tabs = this.root.find(".cx-acct-tabs");
		this.$body = this.root.find(".cx-acct-body");
		this.$tabs.on("click", "[data-tab]", (e) => frappe.set_route("cortex-account", e.currentTarget.dataset.tab));
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
		return $(`<section class="cx-acct-card ${cls || ""}"><header><h2>${title}</h2>${hint ? `<p>${hint}</p>` : ""}</header>${inner}</section>`);
	}

	field(id, label, value, attrs) {
		return `<label class="cx-acct-field" for="${id}"><span>${label}</span><input id="${id}" value="${this.esc(value)}" ${attrs || ""}></label>`;
	}

	kpi(label, value, sub, tone) {
		return `<div class="cx-kpi${tone ? " " + tone : ""}"><span class="cx-kpi-v">${value}</span><span class="cx-kpi-l">${label}</span>${sub ? `<span class="cx-kpi-s">${sub}</span>` : ""}</div>`;
	}

	empty(text) {
		return `<p class="cx-acct-muted cx-acct-empty">${text}</p>`;
	}

	// ---------- cycle ----------
	show(tab) {
		if (tab && this.TABS.some((t) => t[0] === tab)) this.tab = tab;
		this.renderTabs();
		this.call("get_account").then((data) => {
			this.data = data;
			this.renderHero();
			this.render();
			this.loadHeroStats();
		});
	}

	renderTabs() {
		this.$tabs.html(this.TABS.map(([id, label]) => `<button type="button" role="tab" data-tab="${id}" aria-selected="${id === this.tab}" class="cx-acct-tab${id === this.tab ? " active" : ""}">${label}</button>`).join(""));
	}

	render() {
		const d = this.data;
		this.$body.empty();
		const view = { profil: () => this.renderProfile(d), statistiques: () => this.renderStats(), approbations: () => this.renderApprovals(), activite: () => this.renderHistory(), securite: () => this.renderSecurity(), notifications: () => this.renderNotifications(d), societe: () => this.renderCompany(d) }[this.tab];
		view();
	}

	renderHero() {
		const d = this.data;
		const roles = d.roles.map((r) => `<span class="cx-acct-chip">${this.esc(__(r))}</span>`).join("");
		this.$hero.html(`
			<div class="cx-hero-id">${this.avatar(d, 64)}
				<div><h1>${this.esc(d.full_name)}</h1>
				<p>${this.esc(d.email)}${d.company_title || d.company ? ` · ${this.esc(d.company_title || d.company)}` : ""}</p>
				<div class="cx-acct-chips tight">${roles || `<span class="cx-acct-muted">${__("Aucun rôle Cortex.")}</span>`}</div></div></div>
			<div class="cx-hero-stats" aria-live="polite"></div>`);
	}

	avatar(d, size) {
		const initials = (d.full_name || d.email).split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
		return d.image ? `<img src="${this.esc(d.image)}" alt="" class="cx-acct-avatar" style="width:${size}px;height:${size}px">` : `<span class="cx-acct-avatar cx-acct-initials" style="width:${size}px;height:${size}px;font-size:${Math.round(size / 3)}px">${this.esc(initials)}</span>`;
	}

	loadHeroStats() {
		this.call("stats", { period: "30" }).then((s) => {
			this.stats30 = s;
			const w = s.work;
			this.$hero.find(".cx-hero-stats").html(
				[
					[__("Devis créés"), this.n(w.quotes_created)],
					[__("Sorties"), this.n(w.checkouts)],
					[__("Retours"), this.n(w.returns)],
					[__("Approbations décidées"), this.n(s.approvals.approved_by_me + s.approvals.rejected_by_me)],
					[__("Actions"), this.n(s.actions_total)],
				]
					.map(([l, v]) => `<div><b>${v}</b><span>${l}</span></div>`)
					.join("") + `<small>${__("30 derniers jours")}</small>`
			);
		});
	}

	// ---------- Profil ----------
	renderProfile(d) {
		const card = this.card(
			__("Profil"),
			__("Ces informations apparaissent sur vos actions (approbations, notes, journal d'audit)."),
			`<div class="cx-acct-photo">${this.avatar(d, 56)}<div><button type="button" class="btn btn-default btn-sm" data-act="photo">${__("Changer la photo")}</button>${d.image ? ` <button type="button" class="btn btn-link btn-sm" data-act="photo-remove">${__("Retirer")}</button>` : ""}<p>${__("PNG, JPEG ou WebP.")}</p></div></div>
			<form class="cx-acct-form" novalidate>
				<div class="cx-acct-grid">
					${this.field("cx-first", __("Prénom"), d.first_name, 'maxlength="80" autocomplete="given-name" required')}
					${this.field("cx-last", __("Nom"), d.last_name, 'maxlength="80" autocomplete="family-name"')}
					${this.field("cx-mail", __("Courriel"), d.email, 'readonly aria-describedby="cx-mail-h"')}
					${this.field("cx-tel", __("Téléphone"), d.mobile_no, 'maxlength="20" inputmode="tel" autocomplete="tel"')}
				</div>
				<p id="cx-mail-h" class="cx-acct-hint">${__("Votre courriel est votre identifiant : pour le changer, demandez à un administrateur de votre société.")}</p>
				<p class="cx-acct-err" role="alert" hidden></p>
				<div class="cx-acct-actions"><button type="submit" class="btn btn-primary btn-sm">${__("Enregistrer")}</button></div>
			</form>`,
			"wide"
		);
		card.find("form").on("submit", (e) => {
			e.preventDefault();
			const $err = card.find(".cx-acct-err").prop("hidden", true);
			const first = card.find("#cx-first").val().trim();
			if (!first) return $err.text(__("Le prénom est obligatoire.")).prop("hidden", false);
			const $btn = card.find("button[type=submit]").prop("disabled", true);
			this.call("update_profile", { first_name: first, last_name: card.find("#cx-last").val(), mobile_no: card.find("#cx-tel").val() }, "POST")
				.then((data) => {
					this.data = data;
					frappe.boot.user.fullname = data.full_name;
					this.toast(__("Profil enregistré."));
					this.renderHero();
					this.loadHeroStats();
					this.render();
				})
				.catch(() => $btn.prop("disabled", false));
		});
		card.on("click", "[data-act=photo]", () => {
			new frappe.ui.FileUploader({
				as_dataurl: false,
				allow_multiple: false,
				restrictions: { allowed_file_types: [".png", ".jpg", ".jpeg", ".webp"], max_file_size: 3 * 1024 * 1024 },
				on_success: (file) => this.call("update_photo", { file_url: file.file_url }, "POST").then(() => this.show()),
			});
		});
		card.on("click", "[data-act=photo-remove]", () => this.call("update_photo", { file_url: "" }, "POST").then(() => this.show()));

		const me = encodeURIComponent(d.email);
		const side = this.card(
			__("En un coup d'œil"),
			"",
			`<dl class="cx-acct-meta stack">
				<div><dt>${__("Société")}</dt><dd>${this.esc(d.company_title || d.company || "—")}</dd></div>
				<div><dt>${__("Langue")}</dt><dd>${__("Français")}</dd></div>
				<div><dt>${__("Fuseau horaire")}</dt><dd>${this.esc(d.time_zone || "—")}</dd></div>
				<div><dt>${__("Membre depuis")}</dt><dd>${this.esc(d.member_since)}</dd></div>
				<div><dt>${__("Dernière connexion")}</dt><dd>${this.when(d.last_login)}</dd></div>
			</dl>
			<div class="cx-acct-links">
				<a href="/app/cortex-rental-transaction?owner=${me}&rental_state=Quote">${__("Mes devis ouverts")}</a>
				<a href="/app/cortex-rental-transaction?owner=${me}">${__("Toutes mes locations")}</a>
				<a href="/app/approval-request?requested_by_id=${me}">${__("Mes demandes d'approbation")}</a>
			</div>`,
			"narrow"
		);
		this.$body.append($('<div class="cx-acct-cols"></div>').append(card, side));
	}

	// ---------- Statistiques ----------
	periodSelect(current, id) {
		const options = [["7", __("7 jours")], ["30", __("30 jours")], ["90", __("90 jours")], ["365", __("12 mois")], ["all", __("Depuis toujours")]];
		return `<label class="cx-acct-inline"><span>${__("Période")}</span><select id="${id}">${options.map(([v, l]) => `<option value="${v}"${v === current ? " selected" : ""}>${l}</option>`).join("")}</select></label>`;
	}

	renderStats() {
		const holder = $(`<div class="cx-acct-stats"><div class="cx-acct-toolbar">${this.periodSelect(this.period, "cx-period")}<span class="cx-acct-muted">${__("Chiffres tirés du journal d'audit et des dossiers : un zéro veut dire aucune action.")}</span></div><div class="cx-acct-statsbody">${this.empty(__("Chargement…"))}</div></div>`);
		holder.find("#cx-period").on("change", (e) => {
			this.period = e.target.value;
			this.fillStats(holder);
		});
		this.$body.append(holder);
		this.fillStats(holder);
	}

	fillStats(holder) {
		this.call("stats", { period: this.period }).then((s) => {
			const w = s.work, a = s.approvals, e = s.equipment, m = s.money, c = s.conversion;
			const k = (l, v, sub, tone) => this.kpi(l, v, sub, tone);
			const group = (title, inner) => `<section class="cx-acct-card"><header><h2>${title}</h2></header><div class="cx-kpis">${inner}</div></section>`;
			const max = Math.max(1, ...s.daily.map((d) => d.count));
			const bars = s.daily.map((d) => `<i title="${this.esc(d.date)} : ${d.count}" style="height:${Math.max(3, Math.round((d.count / max) * 100))}%" class="${d.count ? "on" : ""}"></i>`).join("");
			const top = e.top_items.length ? `<ol class="cx-top">${e.top_items.map((t) => `<li><span>${this.esc(t.item)}</span><b>${this.n(t.units)} ${__("unités")}</b></li>`).join("")}</ol>` : "";
			holder.find(".cx-acct-statsbody").html(
				`<section class="cx-acct-card"><header><h2>${__("Activité des 30 derniers jours")}</h2><p>${this.n(s.actions_total)} ${__("actions")} · ${this.n(s.logins)} ${__("connexions")} (${s.since ? __("depuis le {0}", [this.esc(s.since)]) : __("depuis toujours")})</p></header><div class="cx-bars" role="img" aria-label="${__("Actions par jour")}">${bars}</div><div class="cx-bars-axis"><span>${this.esc(s.daily[0].date)}</span><span>${this.esc(s.daily[s.daily.length - 1].date)}</span></div></section>` +
					`<div class="cx-acct-groups">` +
					group(__("Locations"), k(__("Devis créés"), this.n(w.quotes_created), c.rate == null ? "" : `${c.rate} % ${__("devenus réservations")}`) + k(__("Réservations"), this.n(w.reservations)) + k(__("Contrats confirmés"), this.n(w.contracts)) + k(__("Clôturées"), this.n(w.closed)) + k(__("Annulées"), this.n(w.cancelled)) + k(__("Litiges ouverts"), this.n(w.disputes), "", w.disputes ? "warn" : "") + k(__("Devis partagés"), this.n(w.quotes_shared)) + k(__("Clients ajoutés"), this.n(w.customers_added))) +
					group(__("Matériel emprunté"), k(__("Locations sorties"), this.n(e.rentals_checked_out)) + k(__("Unités sorties"), this.n(e.units_checked_out)) + k(__("Unités retournées"), this.n(e.units_returned)) + k(__("Retours abîmés"), this.n(e.returns_with_damage), "", e.returns_with_damage ? "warn" : "") + k(__("Manquants"), this.n(e.items_missing), "", e.items_missing ? "warn" : "") + (top ? `<div class="cx-kpi wide"><span class="cx-kpi-l">${__("Équipements les plus sortis")}</span>${top}</div>` : "")) +
					group(__("Facturation"), k(__("Factures émises"), this.n(w.invoices_issued)) + k(__("Paiements enregistrés"), this.n(w.payments_recorded), this.money(m.payments_recorded)) + k(__("Valeur des devis créés"), this.money(m.quoted_value))) +
					group(__("Approbations"), k(__("Demandées par moi"), this.n(a.requested)) + k(__("Approuvées par moi"), this.n(a.approved_by_me)) + k(__("Refusées par moi"), this.n(a.rejected_by_me)) + k(__("Retirées"), this.n(a.withdrawn)) + k(__("Mes demandes en attente"), this.n(a.my_requests_pending), "", a.my_requests_pending ? "warn" : "") + k(__("À décider (autres)"), this.n(a.mine_to_decide), "", a.mine_to_decide ? "warn" : "")) +
					group(__("Assistant IA"), s.ai.visible ? k(__("Demandes"), this.n(s.ai.calls)) + k(__("Jetons"), this.n(s.ai.tokens)) + k(__("Coût"), this.money(s.ai.cost)) : `<p class="cx-acct-muted">${__("Votre rôle ne donne pas accès à l'usage de l'IA.")}</p>`) +
					`</div>`
			);
		});
	}

	// ---------- Approbations ----------
	renderApprovals() {
		const holder = $(`<div>${this.empty(__("Chargement…"))}</div>`);
		this.$body.append(holder);
		this.call("my_approvals").then((r) => {
			const chip = (status, label) => `<span class="cx-pill ${status === "Approved" ? "ok" : status === "Rejected" ? "no" : "wait"}">${this.esc(label)}</span>`;
			const table = (rows, who) =>
				rows.length
					? `<div class="cx-table-wrap"><table class="cx-table"><thead><tr><th>${__("Demande")}</th><th>${__("Élément")}</th><th>${__("Statut")}</th><th>${who}</th><th>${__("Décidée le")}</th><th>${__("Motif")}</th></tr></thead><tbody>${rows
							.map(
								(x) =>
									`<tr><td><a href="/app/approval-request/${encodeURIComponent(x.id)}">${this.esc(x.what)}</a><div class="cx-acct-muted">${this.when(x.created)}</div></td><td>${this.link(x.entity_type, x.entity_id)}</td><td>${chip(x.status, x.status_label)}${x.self_decided ? ` <span class="cx-pill self" title="${__("Seule personne autorisée de la société")}">${__("auto-approbation")}</span>` : ""}</td><td>${this.esc(who === __("Décidée par") ? x.decided_by || "—" : x.requested_by)}</td><td>${this.when(x.decided_at)}</td><td class="cx-reason">${this.esc(x.reason) || "—"}</td></tr>`
							)
							.join("")}</tbody></table></div>`
					: this.empty(__("Aucune pour l'instant."));
			const approved = r.decided.filter((x) => x.status === "Approved").length;
			const rejected = r.decided.filter((x) => x.status === "Rejected").length;
			holder.empty().append(
				this.card(__("Historique de mes décisions"), __("Les demandes que vous avez approuvées ou refusées, avec le motif."), `<div class="cx-kpis inline">${this.kpi(__("Approuvées"), this.n(approved))}${this.kpi(__("Refusées"), this.n(rejected))}${this.kpi(__("Demandes faites"), this.n(r.requested.length))}</div>${table(r.decided, __("Demandée par"))}`),
				this.card(__("Mes demandes d'approbation"), __("Ce que vous avez soumis, et ce qui en est advenu."), table(r.requested, __("Décidée par")))
			);
		});
	}

	// ---------- Activité (historique complet) ----------
	renderHistory() {
		this.hist = { items: [], offset: 0, category: "", period: "90" };
		const card = this.card(
			__("Tout ce que j'ai fait"),
			__("Votre historique complet, tiré du journal d'audit (qui ne se modifie jamais)."),
			`<div class="cx-acct-toolbar">
				<label class="cx-acct-inline"><span>${__("Type")}</span><select id="cx-h-cat"><option value="">${__("Tout")}</option>${[["location", __("Locations")], ["approbation", __("Approbations")], ["client", __("Clients et devis")], ["finance", __("Facturation et paiements")], ["administration", __("Administration")], ["securite", __("Sécurité")]].map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
				${this.periodSelect("90", "cx-h-period")}
				<button type="button" class="btn btn-default btn-sm" data-act="csv">${__("Télécharger (CSV)")}</button>
			</div>
			<ul class="cx-acct-list cx-timeline"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>
			<div class="cx-acct-actions center"><button type="button" class="btn btn-default btn-sm" data-act="more" hidden>${__("Voir plus")}</button><span class="cx-acct-muted" data-role="count"></span></div>`
		);
		card.on("change", "#cx-h-cat, #cx-h-period", () => {
			this.hist = { items: [], offset: 0, category: card.find("#cx-h-cat").val(), period: card.find("#cx-h-period").val() };
			this.loadHistory(card, true);
		});
		card.on("click", "[data-act=more]", () => this.loadHistory(card, false));
		card.on("click", "[data-act=csv]", () => this.exportHistory());
		this.$body.append(card);
		this.loadHistory(card, true);
	}

	loadHistory(card, reset) {
		this.call("history", { category: this.hist.category, period: this.hist.period, limit: 30, offset: this.hist.offset }).then((r) => {
			this.hist.items = reset ? r.items : this.hist.items.concat(r.items);
			this.hist.offset = this.hist.items.length;
			const rows = this.hist.items.map((a) => `<li><span class="cx-tl-dot ${this.esc(a.category)}"></span><span class="cx-tl-main"><b>${this.esc(a.text)}</b> ${this.link(a.entity_type, a.entity_id)}${a.detail ? `<em>« ${this.esc(a.detail)} »</em>` : ""}</span><span class="cx-acct-muted">${this.when(a.at)}</span></li>`);
			card.find("ul").html(rows.join("") || `<li class="cx-acct-muted">${__("Aucune action dans cette période.")}</li>`);
			card.find("[data-act=more]").prop("hidden", !r.has_more);
			card.find("[data-role=count]").text(`${this.hist.items.length} / ${r.total}`);
		});
	}

	exportHistory() {
		const q = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
		const lines = [["Date", "Action", "Type", "Élément", "Détail"].map(q).join(",")].concat(this.hist.items.map((a) => [a.at, a.text, a.entity_type, a.entity_id, a.detail].map(q).join(",")));
		const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
		const a = document.createElement("a");
		a.href = URL.createObjectURL(blob);
		a.download = `mon-historique-${frappe.datetime.get_today()}.csv`;
		a.click();
		URL.revokeObjectURL(a.href);
	}

	// ---------- Sécurité ----------
	renderSecurity() {
		const pass = this.card(
			__("Mot de passe"),
			__("Au moins 10 caractères. Après le changement, vos autres appareils sont déconnectés."),
			`<form class="cx-acct-form" novalidate autocomplete="off">
				<div class="cx-acct-grid one">
					${this.field("cx-old", __("Mot de passe actuel"), "", 'type="password" autocomplete="current-password" required')}
					${this.field("cx-new", __("Nouveau mot de passe"), "", 'type="password" autocomplete="new-password" minlength="10" required')}
					${this.field("cx-new2", __("Confirmer le nouveau mot de passe"), "", 'type="password" autocomplete="new-password" required')}
				</div>
				<p class="cx-acct-err" role="alert" hidden></p>
				<div class="cx-acct-actions"><button type="submit" class="btn btn-primary btn-sm">${__("Changer le mot de passe")}</button></div>
			</form>`,
			"narrow"
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

		const sessions = this.card(
			__("Appareils connectés"),
			__("Chaque session ouverte avec votre compte : appareil, système, adresse IP et dernière activité. Déconnectez celles que vous ne reconnaissez pas."),
			`<ul class="cx-devices" aria-live="polite"><li class="cx-acct-muted">${__("Chargement…")}</li></ul><p class="cx-acct-hint" data-role="note"></p><div class="cx-acct-actions"><button type="button" class="btn btn-default btn-sm" data-act="others">${__("Déconnecter tous les autres appareils")}</button></div>`,
			"wide"
		);
		sessions.on("click", "[data-act=others]", () =>
			frappe.confirm(__("Déconnecter tous les autres appareils ? Ils devront se reconnecter."), () =>
				this.call("sign_out_other_sessions", {}, "POST").then((r) => {
					this.toast(__("{0} appareil(s) déconnecté(s).", [r.closed]));
					this.loadSessions(sessions);
				})
			)
		);
		sessions.on("click", "[data-device]", (e) => {
			const id = e.currentTarget.dataset.device;
			const label = e.currentTarget.dataset.label;
			frappe.confirm(__("Déconnecter « {0} » ? L'appareil devra se reconnecter.", [this.esc(label)]), () =>
				this.call("sign_out_session", { device_id: id }, "POST").then(() => {
					this.toast(__("Appareil déconnecté."));
					this.loadSessions(sessions);
				})
			);
		});

		const logins = this.card(__("Historique des connexions"), __("Vos dernières ouvertures de session, réussies ou refusées."), `<div class="cx-table-wrap"><table class="cx-table"><tbody><tr><td class="cx-acct-muted">${__("Chargement…")}</td></tr></tbody></table></div>`, "wide");
		this.call("login_history", { limit: 20 }).then((r) => {
			const row = (l) => `<tr><td>${this.when(l.at)}</td><td><span class="cx-pill ${l.ok ? "ok" : "no"}">${l.ok ? __("Réussie") : __("Refusée")}</span></td><td>${this.esc(l.ip) || "—"}</td></tr>`;
			const shown = r.logins.slice(0, 8).map(row).join("");
			const rest = r.logins.slice(8);
			logins.find("tbody").html(shown + (rest.length ? `<tr class="cx-more-row"><td colspan="3"><details><summary>${__("Voir les {0} autres connexions", [rest.length])}</summary><table class="cx-table"><tbody>${rest.map(row).join("")}</tbody></table></details></td></tr>` : "") || `<tr><td class="cx-acct-muted">${__("Aucune connexion enregistrée.")}</td></tr>`);
			logins.find("table").prepend(`<thead><tr><th>${__("Date")}</th><th>${__("Résultat")}</th><th>${__("Adresse IP")}</th></tr></thead>`);
		});

		this.$body.append($('<div class="cx-acct-cols even"></div>').append(pass, sessions.addClass("grow")));
		this.$body.append(logins);
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
	deviceList(sessions, buttonFor, extra) {
		const VISIBLE = 5;
		const rows = sessions.map((s) => this.deviceRow(s, buttonFor(s)));
		if (!rows.length) return `<li class="cx-acct-muted">${__("Aucune session.")}</li>`;
		const head = rows.slice(0, VISIBLE).join("");
		const rest = rows.slice(VISIBLE);
		return head + (rest.length ? `<li class="cx-more"><details><summary>${__("Voir les {0} autres sessions", [rest.length])}</summary><ul class="cx-devices">${rest.join("")}</ul></details></li>` : "");
	}

	loadSessions(card) {
		this.call("list_sessions").then((r) => {
			const button = (s) => (s.current ? "" : `<button type="button" class="btn btn-default btn-xs cx-danger" data-device="${this.esc(s.id)}" data-label="${this.esc(s.label)}">${__("Déconnecter")}</button>`);
			card.children("ul.cx-devices").html(this.deviceList(r.sessions, button));
			card.find("[data-role=note]").text(r.tracking_note ? __(r.tracking_note) : "");
			card.find("[data-act=others]").prop("hidden", r.sessions.filter((s) => !s.current).length === 0);
			card.find("header p").first().text(__("{0} session(s) ouverte(s) avec votre compte : appareil, système, adresse IP et dernière activité. Déconnectez celles que vous ne reconnaissez pas.", [r.sessions.length]));
		});
	}

	// Les administrateurs voient les appareils de l'équipe et peuvent déconnecter un membre (téléphone perdu, départ).
	maybeTeamDevices() {
		this.call("company_overview").then((o) => {
			if (!o.can_manage_team) return;
			const card = this.card(__("Appareils de l'équipe"), __("Visible aux administrateurs : déconnectez un appareil perdu ou toutes les sessions d'une personne qui quitte l'équipe."), `<div class="cx-team-dev">${this.empty(__("Chargement…"))}</div>`, "wide");
			this.$body.append(card);
			const load = () =>
				this.call("team_devices", {}, "GET", "administration").then((r) => {
					const data = (r && r.data) || r || {};
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
		const inbox = this.card(__("Boîte de notifications"), __("Les alertes reçues dans l'application (la cloche)."), `<div class="cx-acct-actions top"><span class="cx-acct-muted" data-role="unread"></span><button type="button" class="btn btn-default btn-sm" data-act="readall">${__("Tout marquer comme lu")}</button></div><ul class="cx-acct-list cx-inbox"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>`, "wide");
		const loadInbox = () =>
			this.call("inbox", { limit: 30 }).then((r) => {
				inbox.find("[data-role=unread]").text(r.unread ? __("{0} non lue(s)", [r.unread]) : __("Tout est lu."));
				inbox.find("[data-act=readall]").prop("hidden", !r.unread);
				inbox.find("ul").html(r.items.map((n) => `<li class="${n.read ? "" : "unread"}"><span class="cx-tl-main">${n.read ? "" : '<i class="cx-dot" aria-label="' + __("non lue") + '"></i>'}${n.entity_id && n.text.includes(n.entity_id) ? this.esc(n.text).replace(this.esc(n.entity_id), this.link(n.entity_type, n.entity_id)) : this.esc(n.text) + (n.entity_id ? ` ${this.link(n.entity_type, n.entity_id)}` : "")}</span><span class="cx-acct-muted">${this.when(n.at)}</span></li>`).join("") || `<li class="cx-acct-muted">${__("Aucune notification.")}</li>`);
			});
		inbox.on("click", "[data-act=readall]", () => this.call("mark_all_read", {}, "POST").then(() => loadInbox()));
		loadInbox();

		const prefs = this.card(__("Alertes de Cortex"), __("Choisissez celles que vous voulez recevoir dans l'application. Elles ne modifient aucun dossier."), `<div class="cx-acct-switches"></div>`, "narrow");
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
		const mail = this.card(__("Notifications par courriel"), __("Les alertes dans l'application (cloche) restent toujours actives."), `<div class="cx-acct-switches">${rows}</div>`, "narrow");
		mail.on("change", "input[data-key]", (e) => {
			const box = e.currentTarget;
			this.call("update_notifications", { values: JSON.stringify({ [box.dataset.key]: box.checked ? 1 : 0 }) }, "POST")
				.then((res) => {
					this.data.notifications = res;
					this.toast(__("Préférence enregistrée."));
				})
				.catch(() => (box.checked = !box.checked));
		});
		this.$body.append(inbox, $('<div class="cx-acct-cols even"></div>').append(prefs, mail));
	}

	// ---------- Société, rôles et droits ----------
	renderCompany(d) {
		const head = this.card(
			__("Société"),
			"",
			`<div class="cx-co-head">${d.company_logo ? `<img src="${this.esc(d.company_logo)}" alt="" class="cx-co-logo">` : ""}<div><h3>${this.esc(d.company_title || d.company || "—")}</h3><p class="cx-acct-muted">${__("Votre société dans Cortex : tout ce que vous voyez lui appartient.")}</p></div></div>
			<h4 class="cx-sub">${__("Mes rôles")}</h4><ul class="cx-roles"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>`,
			"wide"
		);
		const rights = this.card(__("Mes droits"), __("Ce que votre compte peut faire, écran par écran. Un administrateur peut les ajuster dans « Équipe et rôles »."), `<div class="cx-table-wrap"><table class="cx-table rights"><thead><tr><th>${__("Écran")}</th><th>${__("Voir")}</th><th>${__("Créer")}</th><th>${__("Modifier")}</th></tr></thead><tbody></tbody></table></div>`, "wide");
		const team = this.card(__("Mon équipe"), __("Les personnes actives de votre société et leurs rôles."), `<div class="cx-table-wrap"><table class="cx-table"><tbody><tr><td class="cx-acct-muted">${__("Chargement…")}</td></tr></tbody></table></div>`, "wide");
		const ai = this.card(__("Assistant IA ce mois-ci"), __("Consommation de votre société."), `<div class="cx-acct-ai"><p class="cx-acct-muted">${__("Chargement…")}</p></div>`, "narrow");
		this.call("company_overview").then((o) => {
			head.find(".cx-roles").html(o.roles.map((r) => `<li><span class="cx-acct-chip">${this.esc(__(r.role))}</span><span class="cx-acct-muted">${this.esc(__(r.help))}</span></li>`).join("") || `<li class="cx-acct-muted">${__("Aucun rôle Cortex.")}</li>`);
			const mark = (v) => (v ? '<span class="cx-yes" aria-label="oui">✓</span>' : '<span class="cx-no" aria-label="non">—</span>');
			rights.find("tbody").html(o.rights.map((r) => `<tr><td>${this.esc(__(r.area))}</td><td>${mark(r.read)}</td><td>${mark(r.create)}</td><td>${mark(r.write)}</td></tr>`).join(""));
			team.find("tbody").html(
				o.team.map((m) => `<tr><td><b>${this.esc(m.name)}</b>${m.you ? ` <span class="cx-pill ok">${__("vous")}</span>` : ""}${m.email ? `<div class="cx-acct-muted">${this.esc(m.email)}</div>` : ""}</td><td>${m.roles.map((r) => `<span class="cx-acct-chip small">${this.esc(__(r))}</span>`).join(" ") || "—"}</td><td class="cx-acct-muted">${m.last_active ? this.when(m.last_active) : "—"}</td></tr>`).join("")
			);
			team.find("table").prepend(`<thead><tr><th>${__("Personne")}</th><th>${__("Rôles")}</th><th>${__("Dernière activité")}</th></tr></thead>`);
		});
		this.call("ai_usage").then((u) => {
			const $box = ai.find(".cx-acct-ai");
			if (!u.visible) return $box.html(`<p class="cx-acct-muted">${__("Votre rôle ne donne pas accès à la consommation de l'IA.")}</p>`);
			const pct = u.cost_cap || u.token_cap ? Math.min(100, u.percent) : 0;
			const label = u.cost_cap ? `${u.cost.toFixed(2)} $ / ${u.cost_cap.toFixed(0)} $` : `${u.tokens.toLocaleString("fr-CA")} ${__("jetons")}`;
			const note = u.economy ? __("Plafond atteint : l'assistant utilise un modèle plus économique.") : u.blocked ? __("Plafond dépassé : l'assistant est en pause jusqu'au mois prochain.") : u.warning ? __("Vous approchez du plafond mensuel.") : "";
			$box.html(`<div class="cx-acct-bar" role="img" aria-label="${pct} %"><i style="width:${pct}%"></i></div><p><strong>${label}</strong> · ${u.calls} ${__("appels")}${u.cost_cap ? ` · ${u.percent} %` : ""}</p>${note ? `<p class="cx-acct-note">${note}</p>` : ""}`);
		});
		this.$body.append(head, $('<div class="cx-acct-cols even"></div>').append(rights, $('<div class="cx-acct-stack"></div>').append(ai)), team);
	}
};
