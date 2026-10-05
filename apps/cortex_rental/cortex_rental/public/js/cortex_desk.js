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


	// Guide de démarrage : zone vidéo à droite de la description, comme dans l'espace Comptabilité. Tant qu'aucune vidéo
	// n'est fournie (champ « intro_video_url » de l'étape), on affiche un emplacement clairement marqué « à venir ».
	function addVideoPlaceholder() {
		document.querySelectorAll(".onboarding-step-body").forEach((body) => {
			if (!body.textContent.trim() || body.querySelector(".video-player, .cx-video-block")) return;
			const block = document.createElement("div");
			block.className = "cx-video-block";
			block.innerHTML =
				'<h4 class="cx-video-title">' + __("Guide vidéo de Cortex Rental") + "</h4>" +
				'<p class="cx-video-text">' +
				__("Cette vidéo vous guidera pas à pas dans l'utilisation de Cortex Rental : créer une location, réserver le matériel, faire approuver le contrat, enregistrer les sorties et les retours, puis facturer.") +
				"</p>" +
				'<div class="cx-video-placeholder" role="img" aria-label="' + __("Vidéo du guide : à venir") + '">' +
				'<svg viewBox="0 0 24 24" width="36" height="36" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 8.5v7l6-3.5z" fill="currentColor"/></svg>' +
				"<span>" + __("Vidéo du guide : à venir") + "</span></div>";
			body.appendChild(block);
		});
	}

	$(document).on("startup", function () {
		preferMainWorkspace();
		let queued = false;
		new MutationObserver(() => {
			if (queued) return;
			queued = true;
			window.requestAnimationFrame(() => {
				queued = false;
				addVideoPlaceholder();
			});
		}).observe(document.body, { childList: true, subtree: true });
		const home = frappe.boot && frappe.boot.cortex_home;
		if (home && home.route && landedOnDefault()) {
			frappe.set_route(home.route);
		}
	});
})();
