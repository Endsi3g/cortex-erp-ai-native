// Mon compte : profil, sécurité, notifications, société et rôles, activité. Chaque action passe par
// cortex_rental.api.v1.account.* et ne concerne que la personne connectée.
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
		this.TABS = [
			["profil", __("Profil")],
			["securite", __("Sécurité")],
			["notifications", __("Notifications")],
			["societe", __("Société et rôles")],
			["activite", __("Activité")],
		];
		this.root.html(`<div class="cx-acct"><nav class="cx-acct-tabs" role="tablist" aria-label="${__("Sections du compte")}"></nav><div class="cx-acct-body" role="tabpanel"></div></div>`);
		this.$tabs = this.root.find(".cx-acct-tabs");
		this.$body = this.root.find(".cx-acct-body");
		this.$tabs.on("click", "[data-tab]", (e) => {
			frappe.set_route("cortex-account", e.currentTarget.dataset.tab);
		});
	}

	call(method, args, type) {
		return frappe.call({ method: `cortex_rental.api.v1.account.${method}`, args, type: type || "GET", freeze: false }).then((r) => r.message);
	}

	show(tab) {
		if (tab && this.TABS.some((t) => t[0] === tab)) this.tab = tab;
		this.renderTabs();
		this.call("get_account").then((data) => {
			this.data = data;
			this.render();
		});
	}

	renderTabs() {
		this.$tabs.html(
			this.TABS.map(([id, label]) => `<button type="button" role="tab" data-tab="${id}" aria-selected="${id === this.tab}" class="cx-acct-tab${id === this.tab ? " active" : ""}">${label}</button>`).join("")
		);
	}

	render() {
		const esc = frappe.utils.escape_html;
		const d = this.data;
		this.$body.empty();
		if (this.tab === "profil") this.renderProfile(d, esc);
		else if (this.tab === "securite") this.renderSecurity(esc);
		else if (this.tab === "notifications") this.renderNotifications(d, esc);
		else if (this.tab === "societe") this.renderCompany(d, esc);
		else this.renderActivity(esc);
	}

	card(title, hint, inner) {
		return $(`<section class="cx-acct-card"><header><h2>${title}</h2>${hint ? `<p>${hint}</p>` : ""}</header>${inner}</section>`);
	}

	field(id, label, value, attrs) {
		return `<label class="cx-acct-field" for="${id}"><span>${label}</span><input id="${id}" value="${frappe.utils.escape_html(value || "")}" ${attrs || ""}></label>`;
	}

	toast(message, indicator) {
		frappe.show_alert({ message, indicator: indicator || "green" }, 5);
	}

	// ---- Profil
	renderProfile(d, esc) {
		const initials = (d.full_name || d.email).split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
		const avatar = d.image ? `<img src="${esc(d.image)}" alt="" class="cx-acct-avatar">` : `<span class="cx-acct-avatar cx-acct-initials">${esc(initials)}</span>`;
		const card = this.card(
			__("Profil"),
			__("Ces informations apparaissent sur vos actions (approbations, notes, journal d'audit)."),
			`<div class="cx-acct-photo">${avatar}<div><button type="button" class="btn btn-default btn-sm" data-act="photo">${__("Changer la photo")}</button>${d.image ? ` <button type="button" class="btn btn-link btn-sm" data-act="photo-remove">${__("Retirer")}</button>` : ""}<p>${__("PNG, JPEG ou WebP.")}</p></div></div>
			<form class="cx-acct-form" novalidate>
				<div class="cx-acct-grid">
					${this.field("cx-first", __("Prénom"), d.first_name, 'maxlength="80" autocomplete="given-name" required')}
					${this.field("cx-last", __("Nom"), d.last_name, 'maxlength="80" autocomplete="family-name"')}
					${this.field("cx-mail", __("Courriel"), d.email, 'readonly aria-describedby="cx-mail-h"')}
					${this.field("cx-tel", __("Téléphone"), d.mobile_no, 'maxlength="20" inputmode="tel" autocomplete="tel"')}
				</div>
				<p id="cx-mail-h" class="cx-acct-muted">${__("Votre courriel est votre identifiant : pour le changer, demandez à un administrateur de votre société.")}</p>
				<p class="cx-acct-err" role="alert" hidden></p>
				<div class="cx-acct-actions"><button type="submit" class="btn btn-primary btn-sm">${__("Enregistrer")}</button></div>
			</form>
			<dl class="cx-acct-meta"><div><dt>${__("Langue")}</dt><dd>${__("Français")}</dd></div><div><dt>${__("Fuseau horaire")}</dt><dd>${esc(d.time_zone || "—")}</dd></div><div><dt>${__("Membre depuis")}</dt><dd>${esc(d.member_since)}</dd></div><div><dt>${__("Dernière connexion")}</dt><dd>${esc(d.last_login || "—")}</dd></div></dl>`
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
		this.$body.append(card);
	}

	// ---- Sécurité : mot de passe + sessions
	renderSecurity(esc) {
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
		const sessions = this.card(__("Appareils connectés"), __("Les sessions ouvertes avec votre compte."), `<ul class="cx-acct-list" aria-live="polite"><li class="cx-acct-muted">${__("Chargement…")}</li></ul><div class="cx-acct-actions"><button type="button" class="btn btn-default btn-sm" data-act="others">${__("Déconnecter les autres appareils")}</button></div>`);
		sessions.on("click", "[data-act=others]", () => {
			frappe.confirm(__("Déconnecter tous les autres appareils ?"), () =>
				this.call("sign_out_other_sessions", {}, "POST").then((r) => {
					this.toast(__("{0} appareil(s) déconnecté(s).", [r.closed]));
					this.loadSessions(sessions);
				})
			);
		});
		this.$body.append(pass, sessions);
		this.loadSessions(sessions);
	}

	loadSessions(card) {
		this.call("list_sessions").then((r) => {
			const esc = frappe.utils.escape_html;
			card.find("ul").html(
				r.sessions.map((s) => `<li><span><strong>${s.current ? __("Cet appareil") : __("Autre appareil")}</strong> <small>${esc(s.device || "")}</small></span><span class="cx-acct-muted">${[s.ip, s.last_active].filter(Boolean).map(esc).join(" · ")}</span></li>`).join("") || `<li class="cx-acct-muted">${__("Aucune session.")}</li>`
			);
		});
	}

	// ---- Notifications
	renderNotifications(d, esc) {
		const n = d.notifications;
		const rows = Object.entries(n.labels)
			.map(([key, label]) => `<label class="cx-acct-switch"><input type="checkbox" data-key="${key}" ${n.values[key] ? "checked" : ""}><span>${esc(__(label))}</span></label>`)
			.join("");
		const card = this.card(__("Notifications par courriel"), __("Les alertes dans l'application (cloche) restent toujours actives."), `<div class="cx-acct-switches">${rows}</div>`);
		card.on("change", "input[type=checkbox]", (e) => {
			const key = e.currentTarget.dataset.key;
			const box = e.currentTarget;
			this.call("update_notifications", { values: JSON.stringify({ [key]: box.checked ? 1 : 0 }) }, "POST")
				.then((res) => {
					this.data.notifications = res;
					this.toast(__("Préférence enregistrée."));
				})
				.catch(() => (box.checked = !box.checked));
		});
		this.$body.append(card);
	}

	// ---- Société, rôles et IA
	renderCompany(d, esc) {
		const roles = d.roles.length ? d.roles.map((r) => `<span class="cx-acct-chip">${esc(__(r))}</span>`).join("") : `<span class="cx-acct-muted">${__("Aucun rôle Cortex.")}</span>`;
		const card = this.card(
			__("Société et rôles"),
			__("Vos droits dans l'application. Un administrateur de votre société peut les modifier dans « Équipe et rôles »."),
			`<dl class="cx-acct-meta"><div><dt>${__("Société")}</dt><dd>${esc(d.company || "—")}</dd></div></dl><div class="cx-acct-chips">${roles}</div>`
		);
		const ai = this.card(__("Assistant IA ce mois-ci"), __("Consommation de votre société."), `<div class="cx-acct-ai"><p class="cx-acct-muted">${__("Chargement…")}</p></div>`);
		this.call("ai_usage").then((u) => {
			const $box = ai.find(".cx-acct-ai");
			if (!u.visible) return $box.html(`<p class="cx-acct-muted">${__("Votre rôle ne donne pas accès à la consommation de l'IA.")}</p>`);
			const pct = u.cost_cap || u.token_cap ? Math.min(100, u.percent) : 0;
			const label = u.cost_cap ? `${u.cost.toFixed(2)} $ / ${u.cost_cap.toFixed(0)} $` : `${u.tokens.toLocaleString("fr-CA")} ${__("jetons")}`;
			const note = u.economy ? __("Plafond atteint : l'assistant utilise un modèle plus économique.") : u.blocked ? __("Plafond dépassé : l'assistant est en pause jusqu'au mois prochain.") : u.warning ? __("Vous approchez du plafond mensuel.") : "";
			$box.html(`<div class="cx-acct-bar" role="img" aria-label="${pct} %"><i style="width:${pct}%"></i></div><p><strong>${label}</strong> · ${u.calls} ${__("appels")}${u.cost_cap ? ` · ${u.percent} %` : ""}</p>${note ? `<p class="cx-acct-note">${note}</p>` : ""}`);
		});
		this.$body.append(card, ai);
	}

	// ---- Activité
	renderActivity(esc) {
		const card = this.card(__("Votre activité récente"), __("Vos dernières actions dans votre société, tirées du journal d'audit."), `<ul class="cx-acct-list"><li class="cx-acct-muted">${__("Chargement…")}</li></ul>`);
		this.call("my_activity").then((r) => {
			card.find("ul").html(
				r.activity
					.map((a) => `<li><span>${esc(a.text)} <a href="/app/${frappe.router.slug(a.entity_type)}/${encodeURIComponent(a.entity_id)}">${esc(a.entity_id)}</a></span><span class="cx-acct-muted">${esc(a.at)}</span></li>`)
					.join("") || `<li class="cx-acct-muted">${__("Aucune action récente.")}</li>`
			);
		});
		this.$body.append(card);
	}
};
