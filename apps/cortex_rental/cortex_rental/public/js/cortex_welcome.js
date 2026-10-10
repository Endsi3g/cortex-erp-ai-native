// Accueil personnalisé après la connexion (phase 11.1) : un voile court « Bienvenue, {prénom} » avec le nom (et le logo)
// de la société, en fondu doux, sans liste d'étapes. Une seule fois par connexion : la page de connexion pose un drapeau
// daté (sessionStorage) à l'envoi du formulaire; le Desk le lit, l'efface et affiche le voile. Un rechargement, un nouvel
// onglet ou un drapeau vieux de plus de 90 s n'affichent rien. Aucun appel serveur, aucune IA. Un clic ou une touche le ferme.
(function () {
	const KEY = "cortex_welcome";
	const FRESH_MS = 90000;
	const HOLD_MS = 1700;
	const REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

	function consumeFlag() {
		try {
			const raw = window.sessionStorage.getItem(KEY);
			window.sessionStorage.removeItem(KEY);
			const at = Number(raw);
			return !!raw && Number.isFinite(at) && Date.now() - at >= 0 && Date.now() - at < FRESH_MS;
		} catch (e) {
			return false; // stockage bloqué (navigation privée…) : pas de voile, jamais d'erreur
		}
	}

	function firstName() {
		const user = (frappe.boot && frappe.boot.user) || {};
		const first = (user.first_name || "").trim() || (user.full_name || frappe.session.user_fullname || "").trim().split(/\s+/)[0];
		return first && first !== "Administrator" ? first : "";
	}

	function show() {
		const home = (frappe.boot && frappe.boot.cortex_home) || {};
		const name = firstName();
		const company = (home.company || "").trim();
		const esc = frappe.utils.escape_html;
		const mark = home.company_logo
			? `<img class="cx-welcome-logo" src="${esc(home.company_logo)}" alt="" />`
			: `<span class="cx-welcome-mark" aria-hidden="true">${esc((company || name || "C").charAt(0).toUpperCase())}</span>`;
		const el = document.createElement("div");
		el.className = "cx-welcome" + (REDUCED ? " is-still" : "");
		el.setAttribute("role", "status");
		el.setAttribute("aria-live", "polite");
		el.innerHTML = `${mark}<h1 class="cx-welcome-title">${esc(name ? __("Bienvenue, {0}", [name]) : __("Bienvenue"))}</h1>${company ? `<p class="cx-welcome-company">${esc(company)}</p>` : ""}`;
		document.body.appendChild(el);
		let closed = false;
		const close = () => {
			if (closed) return;
			closed = true;
			document.removeEventListener("keydown", close);
			el.classList.add("is-leaving");
			window.setTimeout(() => el.remove(), REDUCED ? 0 : 450);
		};
		el.addEventListener("click", close);
		document.addEventListener("keydown", close);
		window.requestAnimationFrame(() => el.classList.add("is-in"));
		window.setTimeout(close, REDUCED ? 900 : HOLD_MS);
	}

	$(document).on("startup", function () {
		if (consumeFlag()) show();
	});
})();
