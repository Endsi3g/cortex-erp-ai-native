// Arrivée sur le Desk : envoie la personne connectée vers l'espace d'arrivée défini par le serveur (Cortex Rental) quand elle
// arrive sur la page d'accueil par défaut d'ERPNext (`/app`, `/app/home`). Un lien direct vers un
// formulaire, une liste ou un espace de travail reste intact, et la redirection n'a lieu qu'une fois
// par chargement (on peut ensuite ouvrir l'espace « Accueil » à la demande).
(function () {
	const DEFAULT_LANDINGS = ["/app", "/app/home", "/desk", "/desk/home"];

	function landedOnDefault() {
		const path = window.location.pathname.replace(/\/+$/, "");
		return DEFAULT_LANDINGS.includes(path);
	}

	// Le fil d'Ariane prend le premier espace du module : plusieurs espaces partagent le module Cortex Rental,
	// on place l'espace principal en tête pour que « Location » s'affiche sous « Cortex Rental » et non « Cortex IA ».
	function preferMainWorkspace() {
		const map = frappe.boot && frappe.boot.module_wise_workspaces;
		const list = map && map["Cortex Rental"];
		if (list && list.includes("Cortex Rental")) {
			map["Cortex Rental"] = ["Cortex Rental"].concat(list.filter((name) => name !== "Cortex Rental"));
		}
	}


	// Guide vidéo de l'espace Cortex Rental : emplacement clairement marqué « à venir » tant qu'aucune vidéo n'est fournie.
	function videoBlock() {
		const block = document.createElement("section");
		block.className = "cx-video-block cx-guide-video";
		block.innerHTML =
			'<h4 class="cx-video-title">' + __("Guide vidéo de Cortex Rental") + "</h4>" +
			'<p class="cx-video-text">' +
			__("Cette vidéo vous guidera pas à pas dans l'utilisation de Cortex Rental : créer une location, réserver le matériel, faire approuver le contrat, enregistrer les sorties et les retours, puis facturer.") +
			"</p>" +
			'<div class="cx-video-placeholder" role="img" aria-label="' + __("Vidéo du guide : à venir") + '">' +
			'<svg viewBox="0 0 24 24" width="36" height="36" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 8.5v7l6-3.5z" fill="currentColor"/></svg>' +
			"<span>" + __("Vidéo du guide : à venir") + "</span></div>";
		return block;
	}

	// Carte « Terminer votre configuration » en haut de l'espace Cortex Rental : étapes réelles lues du serveur
	// (jamais inventées), visible pour le propriétaire tant que la configuration n'est pas terminée.
	function renderWorkspaceExtras() {
		const home = frappe.boot && frappe.boot.cortex_home;
		const route = frappe.get_route();
		if (route[0] !== "Workspaces" || route[1] !== "Cortex Rental") return;
		const host = document.querySelector(".layout-main-section");
		if (!host) return;
		document.querySelectorAll(".cx-setup-card, .cx-guide-video").forEach((n) => n.remove());
		host.insertBefore(videoBlock(), host.firstChild);
		if (!home || !home.setup_pending) return;
		frappe.call({ method: "cortex_rental.api.v1.onboarding.get_onboarding", type: "GET" }).then((r) => {
			const state = r && r.message && (r.message.data || r.message);
			if (!state || !state.steps || state.status === "Completed") return;
			document.querySelectorAll(".cx-setup-card").forEach((n) => n.remove());
			const esc = frappe.utils.escape_html;
			const p = state.progress || {};
			const card = document.createElement("section");
			card.className = "cx-setup-card";
			card.setAttribute("aria-label", __("Configuration de votre entreprise"));
			const items = state.steps
				.map((step) => {
					const tag = step.done ? "" : step.skipped ? __("Passée") : step.required ? __("Obligatoire") : "";
					return `<li><a href="/app/cortex-setup/${esc(step.key)}" class="${step.done ? "done" : ""}"><i>${step.done ? "✓" : ""}</i><span>${esc(__(step.title))}${tag ? `<small>${esc(tag)}</small>` : ""}</span></a></li>`;
				})
				.join("");
			card.innerHTML =
				`<div class="cx-setup-top"><div><h3>${__("Terminer la configuration de votre entreprise")}</h3>` +
				`<p>${__("{0} étapes sur {1} faites. Les étapes obligatoires nous permettent de vous aider rapidement en cas de besoin.", [p.done || 0, p.total || state.steps.length])}</p></div>` +
				`<a class="btn btn-primary btn-sm" href="/app/cortex-setup">${__("Continuer")}</a></div><ul class="cx-setup-list">${items}</ul>`;
			card.querySelectorAll("a").forEach((a) =>
				a.addEventListener("click", (e) => {
					e.preventDefault();
					frappe.set_route(a.getAttribute("href").replace(/^\/app\//, ""));
				})
			);
			host.insertBefore(card, host.firstChild);
		});
	}

	$(document).on("startup", function () {
		preferMainWorkspace();
		frappe.router.on("change", () => window.setTimeout(renderWorkspaceExtras, 400));
		const home = frappe.boot && frappe.boot.cortex_home;
		if (home && home.route && landedOnDefault()) {
			// Propriétaire dont les renseignements essentiels manquent : assistant plein écran à l'arrivée.
			frappe.set_route(home.setup_required_missing ? "cortex-setup" : home.route);
		}
	});
})();
