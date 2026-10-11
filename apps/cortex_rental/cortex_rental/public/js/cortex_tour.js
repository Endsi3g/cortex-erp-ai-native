// Visite guidée de Cortex (phase 11.4) : halo + bulles, pas à pas. Elle OUVRE chaque page, entoure l'élément réel
// (l'entrée de la barre latérale, ou la zone de saisie de l'Assistant) et dit où est la page et à quoi elle sert, puis
// explique le chemin d'une location. Déterministe : textes écrits ici, aucun modèle d'IA, aucun jeton.
//
// - Automatique UNE fois par personne, à la première arrivée sur l'Assistant IA après l'onboarding (état gardé côté
//   serveur : Cortex User Preference.tour_seen_at, lu au démarrage dans frappe.boot.cortex_tour).
// - Relançable : « Visite guidée de Cortex » dans le menu Aide et dans le menu utilisateur.
// - Passable à tout moment (bouton « Passer la visite » ou Échap). Rien n'est modifié pendant la visite.
// - Une étape dont la page n'existe pas pour cette personne (rôle) est sautée, jamais inventée.
(function () {
	if (typeof frappe === "undefined") return;
	window.cortex = window.cortex || {};

	const STEPS = [
		{
			id: "intro",
			center: true,
			title: "Visite guidée de Cortex",
			text: "En deux minutes, voyez où se trouve chaque page et comment une location avance, de la demande au paiement. Rien n'est modifié pendant la visite et vous pouvez la quitter à tout moment (touche Échap).",
		},
		{
			id: "assistant",
			nav: "assistant",
			target: ".ch-input, .ch-composer textarea, textarea",
			title: "Assistant IA",
			text: "Votre page d'accueil. Écrivez ce que vous voulez faire (« devis pour… », « retards de retour ») ou ouvrez un questionnaire guidé. L'assistant propose, vous décidez : rien n'est enregistré sans votre approbation.",
		},
		{ id: "home", nav: "home", title: "Tableau de bord", text: "Le portrait du jour : locations en cours, retours attendus, factures à surveiller, avec des raccourcis vers ce qui demande votre attention." },
		{ id: "rentals", nav: "rentals", title: "Locations", text: "Toutes vos locations, du devis à la facture. Ouvrez-en une pour voir son état, son matériel, ses prix et ses documents; créez-en une avec « Nouvelle location »." },
		{ id: "availability", nav: "availability", title: "Disponibilité", text: "La grille du matériel libre ou réservé, jour par jour. Elle sert à répondre au client avant de faire le devis; le serveur revérifie toujours la disponibilité au moment de réserver." },
		{ id: "approvals", nav: "approvals", title: "Approbations", text: "Les demandes qui attendent une personne (contrat, exception). Vous voyez ce qui est demandé et par qui, puis vous approuvez ou refusez avec un motif." },
		{ id: "operations", nav: "operations", title: "Sorties et retours", text: "Le comptoir : préparer les sorties, enregistrer les retours (numéros de série, état du matériel) et repérer les retards." },
		{ id: "catalog", nav: "catalog", title: "Catalogue", text: "Chaque équipement avec son tarif journalier, sa valeur de remplacement, son dépôt et son parc. C'est ici que les prix des devis prennent leur source." },
		{ id: "serials", nav: "serials", title: "Numéros de série", text: "Les unités suivies une à une (caméras, optiques…). Chaque sortie et chaque retour les consultent." },
		{ id: "customers", nav: "customers", title: "Clients", text: "Vos clients et leur historique : devis ouverts, locations en cours, solde dû." },
		{ id: "invoices", nav: "invoices", title: "Factures", text: "Les factures émises (acompte, location, frais), leur solde et leur échéance." },
		{ id: "payments", nav: "payments", title: "Paiements", text: "Les paiements reçus ou remboursés, rattachés à leurs factures." },
		{ id: "finance", nav: "finance", title: "Finance", text: "Vue d'ensemble de la facturation : facturé, encaissé, à recevoir, taxes perçues, consignation et journal comptable." },
		{
			id: "cycle",
			center: true,
			title: "Le chemin d'une location",
			chips: ["Demande", "Devis", "Réservation", "Contrat", "Sortie", "Retour", "Facture", "Paiement"],
			text: "Une location suit ce chemin. À chaque étape, Cortex vérifie les règles (disponibilité, approbation, documents). L'assistant peut préparer l'étape; c'est vous qui approuvez.",
		},
		{ id: "templates", nav: "templates", title: "Modèles de secteur", text: "Un point de départ pour votre domaine (catégories, règles de prix, réglages). Vous voyez tout avant d'appliquer, et vous pouvez annuler." },
		{ id: "admin", nav: "admin", title: "Équipe et règles", text: "Les personnes, leurs rôles, les règles de prix et les réglages de l'assistant." },
		{ id: "account", nav: "acct-profil", title: "Mon compte", text: "Votre profil, vos statistiques, vos approbations, l'activité, la sécurité et vos notifications." },
		{
			id: "end",
			center: true,
			title: "C'est tout",
			text: "Vous pouvez relancer cette visite quand vous voulez : menu Aide, ou le menu à votre nom (en haut à droite).",
		},
	];

	const REDUCED = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
	const esc = (v) => frappe.utils.escape_html(String(v == null ? "" : v));
	let tour = null;
	let autoTried = false;

	const wait = (ms) => new Promise((r) => window.setTimeout(r, ms));

	async function settled(route) {
		// Laisse la route changer et les appels réseau finir (au plus ~3 s) : jamais d'attente infinie.
		const slug = route.replace(/^\/app\//, "");
		for (let i = 0; i < 20; i++) {
			const now = window.location.pathname.replace(/^\/app\//, "");
			if (now === slug || now.startsWith(slug)) break;
			await wait(120);
		}
		for (let i = 0; i < 12; i++) {
			if (!window.jQuery || window.jQuery.active === 0) break;
			await wait(120);
		}
		await wait(REDUCED() ? 80 : 320);
	}

	class Tour {
		constructor(manual) {
			this.manual = !!manual;
			this.origin = window.location.pathname;
			this.steps = [];
			this.index = -1;
			this.closed = false;
			this.build();
		}

		build() {
			this.shield = document.createElement("div");
			this.shield.className = "cx-tour-shield";
			this.halo = document.createElement("div");
			this.halo.className = "cx-tour-halo";
			this.halo.hidden = true;
			this.bubble = document.createElement("div");
			this.bubble.className = "cx-tour-bubble";
			this.bubble.setAttribute("role", "dialog");
			this.bubble.setAttribute("aria-modal", "true");
			this.bubble.setAttribute("aria-label", __("Visite guidée de Cortex"));
			document.body.append(this.shield, this.halo, this.bubble);
			document.body.classList.add("cx-tour-on");
			this.onKey = (e) => this.key(e);
			this.onResize = () => this.current && this.place(this.current.el, this.current.step);
			document.addEventListener("keydown", this.onKey, true);
			window.addEventListener("resize", this.onResize);
			this.shield.addEventListener("click", (e) => e.stopPropagation());
		}

		key(e) {
			if (e.key === "Escape") return e.preventDefault(), e.stopPropagation(), this.close();
			if (e.key === "ArrowRight") return e.preventDefault(), this.go(1);
			if (e.key === "ArrowLeft") return e.preventDefault(), this.go(-1);
			if (e.key === "Tab") {
				const f = [...this.bubble.querySelectorAll("button")].filter((b) => !b.disabled);
				if (!f.length) return;
				const first = f[0];
				const last = f[f.length - 1];
				if (e.shiftKey && document.activeElement === first) e.preventDefault(), last.focus();
				else if (!e.shiftKey && document.activeElement === last) e.preventDefault(), first.focus();
				else if (!this.bubble.contains(document.activeElement)) e.preventDefault(), first.focus();
			}
		}

		// Les étapes dont l'entrée de navigation n'existe pas pour cette personne (rôle) sont retirées d'avance.
		plan() {
			return STEPS.filter((s) => !s.nav || navItem(s.nav));
		}

		async start() {
			this.steps = this.plan();
			await this.go(1);
		}

		async go(dir) {
			if (this.busy || this.closed) return;
			const next = this.index + dir;
			if (next < 0) return;
			if (next >= this.steps.length) return this.close(true);
			this.busy = true;
			try {
				this.index = next;
				await this.show(this.steps[next]);
			} finally {
				this.busy = false;
			}
		}

		async show(step) {
			let el = null;
			if (step.nav) {
				const item = navItem(step.nav);
				openGroupOf(item);
				const href = item.getAttribute("href") || "";
				if (href && window.location.pathname !== href) {
					frappe.set_route(href.replace(/^\/app\//, ""));
					await settled(href);
				}
				el = (step.target && document.querySelector(step.target)) || navItem(step.nav);
				if (step.target && !document.querySelector(step.target)) el = navItem(step.nav);
			}
			if (this.closed) return;
			this.current = { step, el };
			this.render(step);
			this.place(el, step);
			const nextBtn = this.bubble.querySelector("[data-tour=next]");
			if (nextBtn) nextBtn.focus({ preventScroll: true });
		}

		render(step) {
			const total = this.steps.length;
			const pos = this.index + 1;
			const last = pos === total;
			const chips = step.chips
				? `<ol class="cx-tour-chips">${step.chips.map((c, i) => `<li><b>${i + 1}</b>${esc(__(c))}</li>`).join("")}</ol>`
				: "";
			this.bubble.innerHTML = `
				<div class="cx-tour-count" aria-live="polite">${esc(__("Étape {0} sur {1}", [pos, total]))}<i style="width:${Math.round((pos / total) * 100)}%"></i></div>
				<h3 class="cx-tour-title">${esc(__(step.title))}</h3>
				<p class="cx-tour-text">${esc(__(step.text))}</p>
				${chips}
				<div class="cx-tour-actions">
					<button type="button" class="cx-tour-skip" data-tour="skip">${esc(last ? __("Fermer") : __("Passer la visite"))}</button>
					<span class="cx-tour-spacer"></span>
					<button type="button" class="cx-tour-prev" data-tour="prev" ${this.index === 0 ? "disabled" : ""}>${esc(__("Précédent"))}</button>
					<button type="button" class="cx-tour-next" data-tour="next">${esc(last ? __("Terminer") : this.index === 0 ? __("Commencer") : __("Suivant"))}</button>
				</div>`;
			this.bubble.querySelector("[data-tour=skip]").addEventListener("click", () => this.close());
			this.bubble.querySelector("[data-tour=prev]").addEventListener("click", () => this.go(-1));
			this.bubble.querySelector("[data-tour=next]").addEventListener("click", () => this.go(1));
		}

		place(el, step) {
			const vw = window.innerWidth;
			const vh = window.innerHeight;
			const bw = Math.min(360, vw - 24);
			this.bubble.style.width = `${bw}px`;
			const rect = el && el.getBoundingClientRect();
			const visible = rect && rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < vh;
			if (!visible) {
				// Pas d'élément à entourer (étape de texte, ou barre latérale cachée sur petit écran) : bulle au centre.
				this.halo.hidden = true;
				this.bubble.classList.add("is-center");
				this.bubble.style.left = `${Math.max(12, (vw - bw) / 2)}px`;
				this.bubble.style.top = `${Math.max(12, (vh - this.bubble.offsetHeight) / 2)}px`;
				return;
			}
			if (el.scrollIntoView) el.scrollIntoView({ block: "nearest", inline: "nearest" });
			const r = el.getBoundingClientRect();
			const pad = 6;
			this.halo.hidden = false;
			this.bubble.classList.remove("is-center");
			Object.assign(this.halo.style, { top: `${r.top - pad}px`, left: `${r.left - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px` });
			const bh = this.bubble.offsetHeight;
			let left = r.right + 18;
			let top = r.top + r.height / 2 - bh / 2;
			if (left + bw > vw - 12) {
				// Pas de place à droite : sous l'élément (ou au-dessus s'il est en bas de l'écran).
				left = Math.min(Math.max(12, r.left), vw - bw - 12);
				top = r.bottom + 14 + bh > vh - 12 ? r.top - bh - 14 : r.bottom + 14;
			}
			this.bubble.style.left = `${left}px`;
			this.bubble.style.top = `${Math.min(Math.max(12, top), vh - bh - 12)}px`;
		}

		close(completed) {
			if (this.closed) return;
			this.closed = true;
			document.removeEventListener("keydown", this.onKey, true);
			window.removeEventListener("resize", this.onResize);
			[this.shield, this.halo, this.bubble].forEach((n) => n.remove());
			document.body.classList.remove("cx-tour-on");
			tour = null;
			markSeen();
			// On revient là où la personne était (ou à l'Assistant IA pour la visite automatique).
			const back = this.origin.replace(/^\/app\//, "");
			if (back && window.location.pathname !== this.origin) frappe.set_route(back);
			if (completed) frappe.show_alert({ message: __("Visite terminée. Relancez-la depuis le menu Aide."), indicator: "green" }, 5);
		}
	}

	function navItem(id) {
		return document.querySelector(`#cx-nav .cx-nav-item[data-id="${id}"]`);
	}

	// Les groupes repliés de la barre latérale sont ouverts pour que l'entrée soit visible (sans mémoriser ce choix).
	function openGroupOf(item) {
		const group = item && item.closest(".cx-group");
		if (!group || !group.classList.contains("closed")) return;
		group.classList.remove("closed");
		const title = group.querySelector(".cx-group-title");
		if (title) title.setAttribute("aria-expanded", "true");
		group.dataset.auto = "1"; // se referme tout seul quand on quitte la page (voir cortex_nav.js)
	}

	function markSeen() {
		if (frappe.boot) frappe.boot.cortex_tour = Object.assign({}, frappe.boot.cortex_tour, { seen: true });
		frappe.call({ method: "cortex_rental.api.v1.tour.mark_seen", type: "POST", freeze: false, silent: true }).catch(() => {});
	}

	function start(manual) {
		if (tour) return tour;
		tour = new Tour(manual);
		tour.start();
		return tour;
	}

	cortex.tour = { start: () => start(true), steps: () => STEPS.slice(), running: () => !!tour };

	// --- Lancement automatique : une seule fois par personne, à l'arrivée sur l'Assistant IA après l'onboarding ---
	function maybeAutoStart() {
		const boot = frappe.boot || {};
		if (autoTried || tour || !boot.cortex_tour || boot.cortex_tour.seen) return;
		if (boot.cortex_home && boot.cortex_home.setup_pending) return;
		if (window.innerWidth < 900) return; // petit écran : la visite se lance à la demande (menu Aide)
		if ((window.location.pathname.replace(/^\/app\//, "").split("/")[0] || "") !== "cortex-home") return;
		if (document.querySelector(".cx-welcome")) return window.setTimeout(maybeAutoStart, 700); // après l'accueil personnalisé
		autoTried = true;
		// Le « boot » de Frappe est mis en cache : on confirme auprès du serveur avant d'imposer la visite.
		frappe
			.call({ method: "cortex_rental.api.v1.tour.get_state", type: "GET", freeze: false, silent: true })
			.then((r) => {
				const seen = !r || !r.message || !r.message.data || r.message.data.seen !== false;
				if (seen) {
					boot.cortex_tour.seen = true;
					return;
				}
				window.setTimeout(() => !tour && start(false), 600);
			})
			.catch(() => {}); // sans réponse du serveur, pas de visite imposée
	}

	// --- Entrées de menu pour la relancer (Aide, et menu utilisateur : l'Assistant plein écran n'a pas d'Aide) ---
	function addMenuEntries() {
		["#toolbar-help", "#toolbar-user"].forEach((sel) => {
			const menu = document.querySelector(sel);
			if (!menu || menu.querySelector("[data-cx-tour]")) return;
			const a = document.createElement("a");
			a.className = "dropdown-item";
			a.href = "#";
			a.dataset.cxTour = "1";
			a.textContent = __("Visite guidée de Cortex");
			a.addEventListener("click", (e) => {
				e.preventDefault();
				$(menu).closest(".dropdown").find(".dropdown-menu").removeClass("show");
				cortex.tour.start();
			});
			menu.insertBefore(a, menu.firstChild);
		});
	}

	$(document).on("startup", function () {
		[600, 1800, 4000].forEach((ms) => window.setTimeout(addMenuEntries, ms));
		frappe.router.on("change", () => window.setTimeout(maybeAutoStart, 400));
		window.setTimeout(maybeAutoStart, 1200);
	});
})();
