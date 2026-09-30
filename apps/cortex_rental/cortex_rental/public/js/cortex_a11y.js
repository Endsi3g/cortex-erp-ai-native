// Accessibilité du Desk : Frappe génère des boutons-icônes, cases à cocher, listes déroulantes et menus sans nom
// accessible. Ce script ajoute les noms (en français) et les rôles manquants sur les écrans Cortex et ERPNext,
// sans changer le comportement. Il ne touche que les éléments sans nom et s'exécute après chaque changement du DOM
// (regroupé sur une image d'animation).
(function () {
	const t = (text) => (typeof __ === "function" ? __(text) : text);

	function name(el, text) {
		if (text && !el.hasAttribute("aria-label") && !el.hasAttribute("aria-labelledby")) {
			el.setAttribute("aria-label", String(text).replace(/\s+/g, " ").trim());
		}
	}

	function visibleText(el) {
		return (el.textContent || "").replace(/\s+/g, " ").trim();
	}

	function tooltip(el) {
		return el.getAttribute("data-original-title") || el.getAttribute("title") || "";
	}

	function fixViewport() {
		const meta = document.querySelector('meta[name="viewport"]');
		if (meta && /user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b/.test(meta.content)) {
			meta.content = "width=device-width, initial-scale=1.0";
		}
	}

	const RULES = [
		// Menus déroulants déclarés sur <a> sans href.
		['a[data-toggle="dropdown"][aria-haspopup]:not([href]):not([data-cx-a11y])', (el) => {
			el.setAttribute("data-cx-a11y", "1");
			const inner = el.querySelector("button");
			if (inner) {
				// L'<a> enveloppe déjà un vrai bouton : le bouton porte l'état, l'<a> devient neutre.
				inner.setAttribute("aria-haspopup", "true");
				el.removeAttribute("aria-haspopup");
				el.removeAttribute("aria-expanded");
				el.setAttribute("role", "presentation");
				return;
			}
			el.setAttribute("role", "button");
			if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "0");
			if (!visibleText(el)) name(el, tooltip(el) || t("Plus d'actions"));
		}],
		// Boutons sans texte : titre Frappe, sinon rôle connu.
		["button:not([aria-label]), a[role=button]:not([aria-label])", (el) => {
			if (visibleText(el) || el.getAttribute("aria-labelledby")) return;
			if (el.classList.contains("drop-icon")) {
				const item = el.closest(".desk-sidebar-item, .sidebar-item-container");
				const label = item && item.querySelector(".sidebar-item-label");
				name(el, t("Afficher ou masquer les sous-éléments") + (label ? " : " + visibleText(label) : ""));
			} else if (el.classList.contains("chart-menu")) {
				name(el, t("Options du graphique"));
			} else if (tooltip(el)) {
				name(el, tooltip(el));
			} else if (el.classList.contains("btn-modal-close") || el.classList.contains("close")) {
				name(el, t("Fermer"));
			}
		}],
		// Boutons « + » de la barre latérale des formulaires.
		[".add-assignment-btn:not([aria-label])", (el) => name(el, t("Assigner"))],
		[".add-attachment-btn:not([aria-label])", (el) => name(el, t("Ajouter une pièce jointe"))],
		[".add-tags-btn:not([aria-label])", (el) => name(el, t("Ajouter une étiquette"))],
		[".share-doc-btn:not([aria-label])", (el) => name(el, t("Partager"))],
		// Champs des formulaires : l'étiquette visible n'est pas reliée au champ par Frappe.
		[".frappe-control input:not([type=checkbox]):not([type=hidden]):not([aria-label]):not([id]), .frappe-control textarea:not([aria-label]):not([id])", (el) => {
			const control = el.closest(".frappe-control");
			const label = control && control.querySelector(".control-label, .label-area");
			name(el, (label && visibleText(label)) || el.getAttribute("placeholder") || el.getAttribute("data-fieldname"));
		}],
		[".scroll-to-top:not([aria-label])", (el) => name(el, t("Haut de la page"))],
		// Tables de formulaire (grilles) et sélecteur d'heure.
		["input.grid-row-check:not([aria-label])", (el) => {
			const row = el.closest(".grid-row");
			name(el, row && row.classList.contains("grid-heading-row") ? t("Tout sélectionner") : t("Sélectionner la ligne"));
		}],
		[".datepicker--time input[type=range]:not([aria-label])", (el) => {
			const labels = { hours: t("Heures"), minutes: t("Minutes"), seconds: t("Secondes") };
			name(el, labels[el.getAttribute("name")] || t("Heure"));
		}],
		// Diagramme de Gantt : zone défilante atteignable au clavier.
		[".gantt-container:not([tabindex])", (el) => {
			el.setAttribute("tabindex", "0");
			el.setAttribute("role", "region");
			name(el, t("Diagramme de Gantt"));
		}],
		// Cases à cocher des listes.
		["input.list-row-checkbox:not([aria-label])", (el) => {
			name(el, t("Sélectionner {0}", [el.getAttribute("data-name") || ""]));
		}],
		["input.list-check-all:not([aria-label])", (el) => name(el, t("Tout sélectionner"))],
		// Listes déroulantes de filtres.
		["select:not([aria-label]):not([id])", (el) => {
			const control = el.closest(".frappe-control");
			name(el, el.getAttribute("placeholder") || (control && tooltip(control)) || el.getAttribute("data-fieldname"));
		}],
		// Tables de rapport (DataTable).
		["input.dt-filter:not([aria-label])", (el) => name(el, t("Filtre de colonne"))],
		["textarea.dt-paste-target:not([aria-label])", (el) => name(el, t("Zone de collage"))],
		// Barres latérales dont les <li> ne sont pas de vrais enfants de <ul> : pas de sémantique de liste.
		["ul.sidebar-menu:not([role])", (el) => {
			el.setAttribute("role", "presentation");
			el.querySelectorAll("li").forEach((li) => li.setAttribute("role", "presentation"));
		}],
		["ul.sidebar-menu[role=presentation] li:not([role])", (el) => el.setAttribute("role", "presentation")],
	];

	function run() {
		fixViewport();
		RULES.forEach(([selector, apply]) => {
			document.querySelectorAll(selector).forEach((el) => {
				try {
					apply(el);
				} catch (e) {
					// Un élément inattendu ne doit jamais casser le Desk.
				}
			});
		});
	}

	let scheduled = false;
	function schedule() {
		if (scheduled) return;
		scheduled = true;
		window.requestAnimationFrame(() => {
			scheduled = false;
			run();
		});
	}

	$(document).on("startup", () => {
		run();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	});
})();
