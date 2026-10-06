// Configuration de l'espace : un assistant plein écran, étape par étape. Les étapes obligatoires (informations de
// l'entreprise, contact du propriétaire) ne peuvent pas être passées : elles servent au soutien, aux devis et aux
// factures. Les autres sont facultatives et peuvent être passées. On peut revenir en arrière sur toutes les étapes,
// aussi après la fin. Chaque enregistrement passe par cortex_rental.api.v1.onboarding.* (propriétaire seulement).
frappe.pages["cortex-setup"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Configuration"), single_column: true });
	wrapper.cx_onboarding = new cortex.OnboardingPage(wrapper);
};

frappe.pages["cortex-setup"].on_page_show = function (wrapper) {
	if (wrapper.cx_onboarding) wrapper.cx_onboarding.show(frappe.get_route()[1]);
};

// L'assistant couvre tout l'écran (barre latérale comprise) : on le retire dès qu'on quitte la page.
frappe.pages["cortex-setup"].on_page_hide = function (wrapper) {
	if (wrapper.cx_onboarding) wrapper.cx_onboarding.$el.detach();
	document.body.classList.remove("cx-onb-open");
};

cortex.OnboardingPage = class OnboardingPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.$el = $('<div class="cx-onb" role="main"></div>');
		this.state = null;
		this.step = "company";
		this.choices = null;
	}

	call(method, args, type) {
		return frappe.call({ method: `cortex_rental.api.v1.onboarding.${method}`, args, type: type || "GET", freeze: false }).then((r) => r.message);
	}

	esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	show(step) {
		this.requested = step;
		this.$el.appendTo(document.body);
		document.body.classList.add("cx-onb-open");
		this.$el.html(`<div class="cx-onb-loading">${__("Chargement…")}</div>`);
		Promise.all([this.call("get_onboarding"), this.choices ? this.choices : this.call("list_choices")]).then(([state, choices]) => {
			this.choices = choices;
			this.state = state.data;
			const keys = this.state.steps.map((s) => s.key).concat(["recap"]);
			// Un lien direct vers une étape verrouillée (étapes obligatoires non terminées) ramène à l'étape à faire.
			const locked = new Set(this.state.steps.filter((s) => s.locked).map((s) => s.key));
			if (!this.state.can_finish) locked.add("recap");
			const wanted = this.requested && keys.includes(this.requested) && !locked.has(this.requested) ? this.requested : null;
			const current = this.state.steps.find((s) => s.current);
			this.step = wanted || (current ? current.key : "recap");
			this.render();
		});
	}

	stepOf(key) {
		return this.state.steps.find((s) => s.key === key);
	}

	go(key) {
		this.step = key;
		frappe.set_route("cortex-setup", key);
	}

	apply(result) {
		const data = result && result.data;
		if (!data) return null;
		if (data.ok === false) {
			this.error(data.message || __("Une erreur est survenue."));
			return null;
		}
		this.state = data.state;
		return data.state;
	}

	error(message) {
		this.$el.find(".cx-onb-err").text(message).prop("hidden", false);
		const el = this.$el.find(".cx-onb-err")[0];
		if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
	}

	// ---------- cadre ----------
	render() {
		const s = this.state;
		const p = s.progress;
		const stepsHtml = s.steps
			.map((st, i) => {
				const status = st.done ? "done" : st.skipped ? "skipped" : st.locked ? "locked" : "todo";
				const tag = st.required ? __("Obligatoire") : st.done ? __("Terminée") : st.skipped ? __("Passée") : __("Facultatif");
				return `<li><button type="button" class="cx-onb-step ${status}${st.key === this.step ? " on" : ""}" data-key="${st.key}"${st.locked ? " disabled" : ""}><i>${st.done ? "✓" : i + 1}</i><span><b>${this.esc(__(st.title))}</b><small>${tag}</small></span></button></li>`;
			})
			.join("");
		const recapOn = this.step === "recap";
		this.$el.html(`
			<header class="cx-onb-head">
				<div class="cx-onb-brand"><span class="cx-onb-mark">C</span><div><b>${__("Configuration de votre espace")}</b><small>${this.esc(s.company_info.company_name)}</small></div></div>
				<div class="cx-onb-prog"><span>${__("{0} sur {1} étapes · obligatoires {2}/{3}", [p.done, p.total, p.required_done, p.required_total])}</span><div class="cx-onb-bar"><i style="width:${Math.round((p.done / p.total) * 100)}%"></i></div></div>
				<button type="button" class="btn btn-default btn-sm" data-act="later">${s.status === "Completed" ? __("Fermer") : __("Continuer plus tard")}</button>
			</header>
			<div class="cx-onb-main">
				<nav class="cx-onb-steps" aria-label="${__("Étapes")}"><ol>${stepsHtml}<li><button type="button" class="cx-onb-step ${s.can_finish ? "todo" : "locked"}${recapOn ? " on" : ""}" data-key="recap"${s.can_finish ? "" : " disabled"}><i>★</i><span><b>${__("Récapitulatif")}</b><small>${s.status === "Completed" ? __("Terminée") : __("Dernière étape")}</small></span></button></li></ol></nav>
				<section class="cx-onb-card"><p class="cx-onb-err" role="alert" hidden></p><div class="cx-onb-content"></div><footer class="cx-onb-foot"></footer></section>
			</div>`);
		this.$el.on("click", "[data-key]", (e) => this.go(e.currentTarget.dataset.key));
		this.$el.find("[data-act=later]").on("click", () => frappe.set_route("cortex-rental"));
		this.renderStep();
	}

	foot(buttons) {
		const $foot = this.$el.find(".cx-onb-foot").empty();
		buttons.forEach((b) => {
			const $b = $(`<button type="button" class="btn ${b.primary ? "btn-primary" : "btn-default"} btn-sm">${b.label}</button>`);
			$b.on("click", b.run);
			$foot.append($b);
		});
	}

	prevKey() {
		const keys = this.state.steps.map((s) => s.key);
		const i = keys.indexOf(this.step);
		return this.step === "recap" ? keys[keys.length - 1] : i > 0 ? keys[i - 1] : null;
	}

	nextKey() {
		const keys = this.state.steps.map((s) => s.key).concat(["recap"]);
		return keys[keys.indexOf(this.step) + 1] || null;
	}

	back() {
		const prev = this.prevKey();
		return prev ? { label: __("Retour"), run: () => this.go(prev) } : null;
	}

	// Navigation d'une étape facultative : Retour · Passer · Terminer cette étape.
	optionalFoot(done) {
		const next = this.nextKey();
		const st = this.stepOf(this.step);
		this.foot(
			[
				this.back(),
				{ label: __("Passer pour l'instant"), run: () => this.call("skip_step", { step: this.step }, "POST").then((r) => this.apply(r) && this.go(next)) },
				{ label: st.done ? __("Continuer") : __("Terminer cette étape"), primary: true, run: () => (st.done ? this.go(next) : this.call("complete_step", { step: this.step }, "POST").then((r) => this.apply(r) && this.go(next))) },
			].filter(Boolean)
		);
		return done;
	}

	field(id, label, value, attrs, hint) {
		return `<label class="cx-onb-field" for="${id}"><span>${label}</span><input id="${id}" value="${this.esc(value)}" ${attrs || ""}>${hint ? `<small>${hint}</small>` : ""}</label>`;
	}

	select(id, label, value, options) {
		return `<label class="cx-onb-field" for="${id}"><span>${label}</span><select id="${id}">${options.map((o) => `<option value="${this.esc(o.value)}"${o.value === value ? " selected" : ""}>${this.esc(o.label)}</option>`).join("")}</select></label>`;
	}

	renderStep() {
		const $c = this.$el.find(".cx-onb-content");
		const s = this.state;
		const k = this.step;
		const head = (title, text, required) => `<div class="cx-onb-title"><h1>${title}</h1><span class="cx-onb-tag ${required ? "req" : ""}">${required ? __("Obligatoire") : __("Facultatif")}</span></div><p class="cx-onb-lead">${text}</p>`;
		if (k === "company") return this.stepCompany($c, head);
		if (k === "owner") return this.stepOwner($c, head);
		if (k === "team") {
			$c.html(head(__("Votre équipe"), __("Invitez vos gestionnaires, votre comptoir et votre finance. Chaque personne reçoit un courriel pour choisir son mot de passe et ne voit que ce dont elle a besoin."), false) + this.teamHtml());
			this.bindTeam($c);
			return this.optionalFoot();
		}
		if (k === "catalog") {
			const n = s.catalog.equipment_count;
			$c.html(head(__("Votre catalogue"), __("Ajoutez votre matériel : nom, tarif par jour, valeur de remplacement et numéros de série. Vous pouvez en ajouter un seul pour essayer, ou en importer plusieurs depuis un fichier."), false) + `<div class="cx-onb-stat"><b>${n}</b><span>${n === 1 ? __("équipement au catalogue") : __("équipements au catalogue")}</span></div><div class="cx-onb-cta"><a class="btn btn-primary btn-sm" href="/app/cortex-rental-item-profile/new">${__("Ajouter un équipement")}</a><a class="btn btn-default btn-sm" href="/app/data-import/new?reference_doctype=Cortex%20Rental%20Item%20Profile">${__("Importer depuis un fichier")}</a></div><p class="cx-onb-hint">${__("Quand vous revenez ici, le nombre d'équipements se met à jour tout seul.")}</p>`);
			return this.optionalFoot();
		}
		if (k === "pricing") return this.stepPricing($c, head);
		if (k === "first") {
			const n = s.first.rentals;
			$c.html(head(__("Votre première location"), __("Créez un devis d'essai pour voir le parcours complet : disponibilité, retenue du matériel, partage au client, réservation, contrat. Rien n'est envoyé à un client tant que vous ne le partagez pas."), false) + `<div class="cx-onb-stat"><b>${n}</b><span>${n === 1 ? __("location créée") : __("locations créées")}</span></div><div class="cx-onb-cta"><a class="btn btn-primary btn-sm" href="/app/cortex-rental-transaction/new">${__("Créer un devis d'essai")}</a><a class="btn btn-default btn-sm" href="/app/cortex-availability">${__("Voir la disponibilité")}</a></div>`);
			return this.optionalFoot();
		}
		return this.stepRecap($c);
	}

	// ----- Votre entreprise (obligatoire)
	stepCompany($c, head) {
		const ci = this.state.company_info;
		const countries = this.choices.data.countries.map((c) => ({ value: c, label: c }));
		const currencies = this.choices.data.currencies.map((c) => ({ value: c, label: c }));
		$c.html(
			head(__("Votre entreprise"), __("Ces informations apparaissent sur vos devis et vos factures, et nous permettent de vous aider rapidement si vous avez besoin de soutien."), true) +
				`<form class="cx-onb-form" novalidate>
					<div class="cx-onb-logo"><div class="cx-onb-logo-prev">${ci.logo ? `<img src="${this.esc(ci.logo)}" alt="${__("Logo actuel")}">` : `<span>${__("Aucun logo")}</span>`}</div><div><b>${__("Logo de l'entreprise")} <em>*</em></b><p>${__("PNG, JPEG ou WebP, 2 Mo au plus. Il apparaît dans la barre latérale et sur les devis.")}</p><button type="button" class="btn btn-default btn-sm" data-act="logo">${ci.logo ? __("Changer le logo") : __("Ajouter le logo")}</button></div></div>
					<div class="cx-onb-grid">
						${this.field("cx-name", __("Nom de l'entreprise"), ci.company_name, "readonly")}
						${this.field("cx-addr", __("Adresse") + " *", ci.address_line1, 'maxlength="140" autocomplete="address-line1" required')}
						${this.field("cx-city", __("Ville") + " *", ci.city, 'maxlength="60" autocomplete="address-level2" required')}
						${this.field("cx-state", __("Province ou État") + " *", ci.state, 'maxlength="60" autocomplete="address-level1" required list="cx-prov"')}
						<datalist id="cx-prov">${["Québec", "Ontario", "Nouveau-Brunswick", "Nouvelle-Écosse", "Manitoba", "Colombie-Britannique", "Alberta", "Saskatchewan", "Île-du-Prince-Édouard", "Terre-Neuve-et-Labrador"].map((x) => `<option value="${x}">`).join("")}</datalist>
						${this.field("cx-zip", __("Code postal") + " *", ci.pincode, 'maxlength="20" autocomplete="postal-code" required')}
						${this.select("cx-country", __("Pays") + " *", ci.country, countries)}
						${this.select("cx-cur", __("Devise") + " *", ci.default_currency, currencies)}
						${this.field("cx-phone", __("Téléphone de l'entreprise") + " *", ci.phone_no, 'maxlength="20" inputmode="tel" autocomplete="tel" required')}
						${this.field("cx-mail", __("Courriel de contact") + " *", ci.email, 'type="email" maxlength="140" autocomplete="email" required')}
						${this.field("cx-web", __("Site Web"), ci.website, 'maxlength="140" autocomplete="url"', __("Facultatif"))}
					</div>
				</form>`
		);
		$c.find("[data-act=logo]").on("click", () =>
			new frappe.ui.FileUploader({
				as_dataurl: false,
				allow_multiple: false,
				restrictions: { allowed_file_types: [".png", ".jpg", ".jpeg", ".webp"], max_file_size: 2 * 1024 * 1024 },
				on_success: (file) =>
					frappe.call({ method: "cortex_rental.api.v1.administration.set_company_logo", args: { file_url: file.file_url }, type: "POST", freeze: false }).then((r) => {
						const data = (r.message || {}).data || {};
						if (data.ok === false) return this.error(data.message);
						this.state.company_info.logo = data.logo;
						this.$el.find(".cx-onb-err").prop("hidden", true);
						this.keepForm = this.readCompany();
						this.renderStep();
						this.restoreForm();
					}),
			})
		);
		this.foot([
			this.back(),
			{
				label: __("Enregistrer et continuer"),
				primary: true,
				run: () => {
					const v = this.readCompany();
					this.call("save_company_profile", { country: v.country, default_currency: v.cur, address_line1: v.addr, city: v.city, state: v.state, pincode: v.zip, phone_no: v.phone, email: v.mail, website: v.web }, "POST").then((r) => this.apply(r) && this.go("owner"));
				},
			},
		].filter(Boolean));
	}

	readCompany() {
		const f = (id) => this.$el.find(`#${id}`).val();
		return { addr: f("cx-addr"), city: f("cx-city"), state: f("cx-state"), zip: f("cx-zip"), country: f("cx-country"), cur: f("cx-cur"), phone: f("cx-phone"), mail: f("cx-mail"), web: f("cx-web") };
	}

	// Après le téléversement du logo, on remet ce qui était déjà saisi (rien n'est perdu).
	restoreForm() {
		const v = this.keepForm || {};
		const set = (id, val) => val && this.$el.find(`#${id}`).val(val);
		set("cx-addr", v.addr);
		set("cx-city", v.city);
		set("cx-state", v.state);
		set("cx-zip", v.zip);
		set("cx-country", v.country);
		set("cx-cur", v.cur);
		set("cx-phone", v.phone);
		set("cx-mail", v.mail);
		set("cx-web", v.web);
	}

	// ----- Vous, le propriétaire (obligatoire)
	stepOwner($c, head) {
		const o = this.state.owner_info;
		const zones = ["America/Toronto", "America/Montreal", "America/Halifax", "America/Winnipeg", "America/Edmonton", "America/Vancouver", "America/St_Johns"];
		$c.html(
			head(__("Vous, le propriétaire"), __("La personne-ressource de l'entreprise. Nous utilisons ces informations pour vous joindre si un problème survient avec votre compte."), true) +
				`<form class="cx-onb-form" novalidate><div class="cx-onb-grid">
					${this.field("cx-first", __("Prénom") + " *", o.first_name, 'maxlength="80" autocomplete="given-name" required')}
					${this.field("cx-last", __("Nom"), o.last_name, 'maxlength="80" autocomplete="family-name"')}
					${this.field("cx-omail", __("Courriel (votre identifiant)"), o.email, "readonly")}
					${this.field("cx-mobile", __("Téléphone mobile") + " *", o.mobile_no, 'maxlength="20" inputmode="tel" autocomplete="tel" required')}
					${this.select("cx-tz", __("Fuseau horaire"), o.time_zone, (zones.includes(o.time_zone) ? zones : [o.time_zone].concat(zones)).map((z) => ({ value: z, label: z })))}
				</div></form>`
		);
		this.foot([
			this.back(),
			{
				label: __("Enregistrer et continuer"),
				primary: true,
				run: () => {
					const f = (id) => this.$el.find(`#${id}`).val();
					this.call("save_owner_profile", { first_name: f("cx-first"), last_name: f("cx-last"), mobile_no: f("cx-mobile"), time_zone: f("cx-tz") }, "POST").then((r) => this.apply(r) && this.go("team"));
				},
			},
		].filter(Boolean));
	}

	// ----- Votre équipe (facultatif)
	teamHtml() {
		const s = this.state;
		const members = s.team.map((m) => `<li><b>${this.esc(m.full_name || m.email)}</b><span>${this.esc(m.email)}</span><em>${m.signed_in ? __("Connecté") : __("Invité")}</em></li>`).join("");
		const presets = s.role_presets.map((p) => ({ value: p.key, label: `${p.label} : ${p.description}` }));
		return `<ul class="cx-onb-people">${members}</ul>
			<form class="cx-onb-form cx-onb-invite" novalidate><h3>${__("Inviter quelqu'un")}</h3><div class="cx-onb-grid">
				${this.field("cx-iname", __("Nom complet"), "", 'maxlength="100"')}
				${this.field("cx-imail", __("Courriel"), "", 'type="email" maxlength="140"')}
				${this.select("cx-ipreset", __("Profil"), "manager", presets)}
			</div><button type="button" class="btn btn-default btn-sm" data-act="invite">${__("Envoyer l'invitation")}</button></form>`;
	}

	bindTeam($c) {
		$c.find("[data-act=invite]").on("click", () => {
			const f = (id) => $c.find(`#${id}`).val();
			this.call("invite_team_member", { email: f("cx-imail"), full_name: f("cx-iname"), preset: f("cx-ipreset") }, "POST").then((r) => {
				const data = r && r.data;
				if (!data || data.ok === false) return this.error((data && data.message) || __("Invitation impossible."));
				frappe.show_alert({ message: data.email_sent ? __("Invitation envoyée à {0}.", [data.email]) : __("Invitation créée. Le courriel n'a pas pu partir : transmettez le lien de configuration vous-même."), indicator: data.email_sent ? "green" : "orange" }, 8);
				if (data.setup_link) frappe.msgprint({ title: __("Lien de configuration"), message: `<input class="form-control" readonly value="${this.esc(data.setup_link)}" onclick="this.select()">` });
				this.call("get_onboarding").then((st) => {
					this.state = st.data;
					this.render();
				});
			});
		});
	}

	// ----- Prix, taxes et règles (facultatif)
	stepPricing($c, head) {
		const pr = this.state.pricing;
		const rules = pr.rules.map((r) => `<li>${this.esc(r.rule_name)} : ${r.calendar_days} ${__("jours civils")} = ${r.billable_days} ${__("jours facturés")}</li>`).join("") || `<li>${__("Aucune règle active.")}</li>`;
		$c.html(
			head(__("Prix, taxes et règles"), __("Vos numéros de taxes et votre acompte figurent sur les factures. Les taux de TPS (5 %) et de TVQ (9,975 %) sont déjà réglés."), false) +
				`<form class="cx-onb-form" novalidate><div class="cx-onb-grid">
					${this.field("cx-tps", __("Numéro de TPS"), pr.tps_number, 'maxlength="40" placeholder="123456789 RT0001"')}
					${this.field("cx-tvq", __("Numéro de TVQ"), pr.tvq_number, 'maxlength="40" placeholder="1234567890 TQ0001"')}
					${this.field("cx-dep", __("Acompte à la réservation (%)"), pr.deposit_percent, 'inputmode="decimal" maxlength="6"', __("0 pour ne pas demander d'acompte"))}
				</div></form>
				<h3 class="cx-onb-sub">${__("Règle de prix par défaut")}</h3><ul class="cx-onb-rules">${rules}</ul><a href="/app/rental-pricing-rule">${__("Modifier les règles de prix")}</a>`
		);
		const st = this.stepOf("pricing");
		this.foot([
			this.back(),
			{ label: __("Passer pour l'instant"), run: () => this.call("skip_step", { step: "pricing" }, "POST").then((r) => this.apply(r) && this.go("first")) },
			{ label: __("Enregistrer et continuer"), primary: true, run: () => this.call("save_pricing", { tps_number: this.$el.find("#cx-tps").val(), tvq_number: this.$el.find("#cx-tvq").val(), deposit_percent: String(this.$el.find("#cx-dep").val()).replace(",", ".") }, "POST").then((r) => this.apply(r) && this.go("first")) },
		].filter(Boolean));
		return st;
	}

	// ----- Récapitulatif
	stepRecap($c) {
		const s = this.state;
		const rows = s.steps.map((st) => `<li class="${st.done ? "done" : st.skipped ? "skipped" : ""}"><i>${st.done ? "✓" : st.skipped ? "–" : "•"}</i><span><b>${this.esc(__(st.title))}</b><small>${st.done ? __("Terminée") : st.skipped ? __("Passée pour l'instant") : st.required ? __("À faire (obligatoire)") : __("À faire (facultatif)")}</small></span><button type="button" class="btn btn-link btn-sm" data-key="${st.key}">${st.done ? __("Modifier") : __("Ouvrir")}</button></li>`).join("");
		$c.html(`<div class="cx-onb-title"><h1>${s.status === "Completed" ? __("Votre configuration est terminée") : __("Presque terminé")}</h1></div><p class="cx-onb-lead">${s.can_finish ? __("Les informations obligatoires sont complètes. Vous pouvez terminer maintenant : les étapes facultatives restent accessibles dans Administration › Configuration.") : __("Il reste des étapes obligatoires avant de terminer.")}</p><ul class="cx-onb-recap">${rows}</ul>`);
		this.foot([
			this.back(),
			{
				label: s.status === "Completed" ? __("Aller au tableau de bord") : __("Terminer la configuration"),
				primary: true,
				run: () => (s.status === "Completed" ? frappe.set_route("cortex-rental") : this.call("finish_onboarding", {}, "POST").then((r) => {
					if (this.apply(r)) {
						frappe.show_alert({ message: __("Votre espace est prêt."), indicator: "green" });
						if (frappe.boot.cortex_home) frappe.boot.cortex_home.setup_pending = false;
						frappe.set_route("cortex-rental");
					}
				})),
			},
		].filter(Boolean));
	}
};
