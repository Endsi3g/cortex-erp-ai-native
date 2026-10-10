// Modèles de secteur : un point de départ complet (catégories d'équipement, règles de prix, réglages) pour un domaine de
// location. Déterministe, sans IA. Propriétaire seulement. Cette page n'écrit rien elle-même : « Aperçu » crée une
// proposition (cortex_rental.api.v1.sector_templates.propose), « Appliquer » et « Annuler » passent par le moteur d'actions
// (chat.decide_action / chat.undo_action) : approbation, journal d'audit et annulation comme pour l'assistant.
frappe.pages["cortex-sector-templates"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Modèles de secteur"), single_column: true });
	wrapper.cx_templates = new cortex.SectorTemplatesPage(wrapper);
};

frappe.pages["cortex-sector-templates"].on_page_show = function (wrapper) {
	if (wrapper.cx_templates) wrapper.cx_templates.load();
};

cortex.SectorTemplatesPage = class SectorTemplatesPage {
	constructor(wrapper) {
		this.root = $(wrapper).find(".layout-main-section");
		this.root.html(`
			<style>
				.cx-tpl { max-width: 880px; display: flex; flex-direction: column; gap: 16px; }
				.cx-tpl-lead { margin: 0; color: var(--text-muted); font-size: 14px; }
				.cx-tpl-card, .cx-tpl-preview { border: 1px solid var(--border-color); border-radius: 10px; background: var(--card-bg); }
				.cx-tpl-card { padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
				.cx-tpl-card h3 { margin: 0 0 2px; font-size: 15px; font-weight: 600; }
				.cx-tpl-card p { margin: 0; font-size: 13px; color: var(--text-muted); }
				.cx-tpl-preview-head { padding: 10px 16px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; gap: 8px; font-weight: 600; }
				.cx-tpl-badge { font-weight: 400; font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--control-bg); color: var(--text-muted); }
				.cx-tpl-row { padding: 8px 16px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; gap: 16px; font-size: 13.5px; }
				.cx-tpl-row small { display: block; color: var(--text-muted); font-size: 12px; }
				.cx-tpl-foot { padding: 12px 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
				.cx-tpl-msg { padding: 0 16px 12px; font-size: 13px; color: var(--text-muted); }
				.cx-tpl-msg.bad { color: var(--red-600, #b42318); }
				.cx-tpl-cats { font-size: 13px; color: var(--text-muted); margin: 0; }
				.cx-tpl-note { font-size: 12px; color: var(--text-muted); }
			</style>
			<div class="cx-tpl" role="main">
				<p class="cx-tpl-lead">${__("Un modèle ajoute ce qui manque (catégories d'équipement, règles de prix) et règle des valeurs par défaut du secteur. Il ne retire rien, ne touche ni aux taxes ni aux comptes, et vous voyez tout avant d'appliquer. Vous pouvez annuler après coup.")}</p>
				<div class="cx-tpl-list"></div>
				<div class="cx-tpl-out" aria-live="polite"></div>
				<p class="cx-tpl-cats"></p>
			</div>`);
		this.$list = this.root.find(".cx-tpl-list");
		this.$out = this.root.find(".cx-tpl-out");
		this.$cats = this.root.find(".cx-tpl-cats");
		this.root.on("click", "[data-tpl]", (e) => this.preview(e.currentTarget.dataset.tpl));
		this.root.on("click", "[data-act]", (e) => this.act(e.currentTarget.dataset.act));
		this.block = null;
	}

	esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	call(method, args, type, scope) {
		return frappe.call({ method: `cortex_rental.api.v1.${scope || "sector_templates"}.${method}`, args, type: type || "GET", freeze: false }).then((r) => r.message && r.message.data);
	}

	load() {
		this.call("list_templates").then((data) => {
			const cards = (data.templates || []).map((t) => `
				<div class="cx-tpl-card">
					<div>
						<h3>${this.esc(t.label)}</h3>
						<p>${this.esc(t.description)}</p>
						<p class="cx-tpl-note">${t.categories} ${__("catégories")} · ${t.pricing_rules} ${__("règles de prix")} · ${t.settings} ${__("réglages")}</p>
					</div>
					<button class="btn btn-default btn-sm" data-tpl="${this.esc(t.key)}">${__("Voir l'aperçu")}</button>
				</div>`);
			this.$list.html(cards.join(""));
			this.$cats.text(`${__("Catégories d'équipement du site")} : ${(data.categories || []).map((c) => __(c)).join(", ")}`);
		});
	}

	preview(key) {
		this.$out.html(`<p class="cx-tpl-note">${__("Calcul de l'aperçu…")}</p>`);
		frappe.call({ method: "cortex_rental.api.v1.sector_templates.propose", args: { template: key }, type: "POST", freeze: false }).then(
			(r) => {
				this.block = r.message.data;
				this.status = "Proposed";
				this.message = "";
				this.render();
			},
			() => {
				this.block = null;
				// Un refus du serveur (déjà appliqué, droits) est montré par Frappe; on garde l'aperçu précédent vide.
				this.$out.empty();
			}
		);
	}

	render() {
		const b = this.block;
		if (!b) return this.$out.empty();
		const badge = { Proposed: __("À approuver"), Executed: __("Appliqué"), Rejected: __("Refusé"), Failed: __("Échec"), Expired: __("Périmé"), Undone: __("Annulé") }[this.status] || this.status;
		const rows = (b.rows || []).map((r) => `
			<div class="cx-tpl-row"><div>${this.esc(r.label)}${r.detail ? `<small>${this.esc(r.detail)}</small>` : ""}</div>${r.value ? `<div>${this.esc(r.value)}</div>` : ""}</div>`).join("");
		let buttons = "";
		if (this.status === "Proposed") {
			buttons = `<button class="btn btn-primary btn-sm" data-act="apply">${this.esc(b.approve_label || __("Appliquer"))}</button>
				<button class="btn btn-default btn-sm" data-act="reject">${__("Refuser")}</button>
				<span class="cx-tpl-note">${__("Rien n'est fait avant votre approbation")}</span>`;
		} else if (this.status === "Executed" && this.canUndo) {
			buttons = `<button class="btn btn-default btn-sm" data-act="undo">${this.esc(b.undo_label || __("Annuler ce modèle"))}</button>`;
		}
		this.$out.html(`
			<div class="cx-tpl-preview">
				<div class="cx-tpl-preview-head"><span>${this.esc(b.title)}</span><span class="cx-tpl-badge">${badge}</span></div>
				${b.subtitle ? `<div class="cx-tpl-msg">${this.esc(b.subtitle)}</div>` : ""}
				${rows}
				<div class="cx-tpl-foot">${buttons}</div>
				${this.message ? `<div class="cx-tpl-msg ${this.status === "Failed" || this.bad ? "bad" : ""}" role="alert">${this.esc(this.message)}</div>` : ""}
			</div>`);
	}

	act(kind) {
		if (!this.block) return;
		const id = this.block.action_id;
		const method = kind === "undo" ? "undo_action" : "decide_action";
		const args = kind === "undo" ? { name: id } : { name: id, approve: kind === "apply" ? 1 : 0 };
		this.root.find("[data-act]").prop("disabled", true);
		this.bad = false;
		frappe.call({ method: `cortex_rental.api.v1.chat.${method}`, args, type: "POST", freeze: false }).then(
			(r) => {
				const out = r.message.data;
				this.status = out.status;
				this.canUndo = !!out.can_undo;
				this.message = out.message || "";
				this.bad = !out.ok;
				this.render();
				if (out.ok) this.load();
			},
			() => {
				this.root.find("[data-act]").prop("disabled", false);
			}
		);
	}
};
