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

	$(document).on("startup", function () {
		preferMainWorkspace();
		const home = frappe.boot && frappe.boot.cortex_home;
		if (home && home.route && landedOnDefault()) {
			frappe.set_route(home.route);
		}
	});
})();
