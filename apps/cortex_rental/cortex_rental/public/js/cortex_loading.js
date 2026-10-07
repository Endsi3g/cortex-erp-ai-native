// Chargement par page : une fine barre en haut et un contenu légèrement estompé entre le changement de route et la
// fin des appels réseau. Rien n'est affiché sur une navigation instantanée (délai de 180 ms), jamais plus de 10 s,
// et `prefers-reduced-motion` supprime l'animation (la barre reste fixe).
(function () {
	if (typeof frappe === "undefined" || !frappe.router) return;
	let bar = null;
	let showTimer = null;
	let pollTimer = null;
	let safetyTimer = null;

	function ensureBar() {
		if (bar) return bar;
		bar = document.createElement("div");
		bar.className = "cx-route-bar";
		bar.hidden = true;
		bar.setAttribute("role", "progressbar");
		bar.setAttribute("aria-label", __("Chargement de la page"));
		bar.setAttribute("aria-busy", "true");
		document.body.appendChild(bar);
		return bar;
	}

	function stop() {
		window.clearTimeout(showTimer);
		window.clearInterval(pollTimer);
		window.clearTimeout(safetyTimer);
		document.body.classList.remove("cx-route-loading");
		if (bar) bar.hidden = true;
	}

	function start() {
		stop();
		showTimer = window.setTimeout(() => {
			ensureBar().hidden = false;
			document.body.classList.add("cx-route-loading");
		}, 180);
		// Fin du chargement : plus aucune requête en cours pendant deux relevés de suite.
		let quiet = 0;
		pollTimer = window.setInterval(() => {
			const active = window.jQuery ? window.jQuery.active : 0;
			quiet = active === 0 ? quiet + 1 : 0;
			if (quiet >= 2) stop();
		}, 140);
		safetyTimer = window.setTimeout(stop, 10000);
	}

	$(document).on("startup", () => frappe.router.on("change", start));
})();
