// Arrivée sur le Desk : envoie la personne connectée vers l'Accueil Cortex (écran IA) quand elle
// arrive sur la page d'accueil par défaut d'ERPNext (`/app`, `/app/home`). Un lien direct vers un
// formulaire, une liste ou un espace de travail reste intact, et la redirection n'a lieu qu'une fois
// par chargement (on peut ensuite ouvrir l'espace « Accueil » à la demande).
(function () {
	const DEFAULT_LANDINGS = ["/app", "/app/home", "/desk", "/desk/home"];

	function landedOnDefault() {
		const path = window.location.pathname.replace(/\/+$/, "");
		return DEFAULT_LANDINGS.includes(path);
	}

	$(document).on("startup", function () {
		const home = frappe.boot && frappe.boot.cortex_home;
		if (home && home.route && landedOnDefault()) {
			frappe.set_route(home.route);
		}
	});
})();
