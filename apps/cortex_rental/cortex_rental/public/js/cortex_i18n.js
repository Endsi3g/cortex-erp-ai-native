// Corrections de langue : quelques textes du Desk de Frappe sont écrits en anglais dans le code (sans passer par la
// traduction) ou reçoivent une étiquette non traduite. Ce script les remplace par leur équivalent français après le
// rendu, uniquement pour des textes exacts connus : les données saisies par les gens ne sont jamais modifiées.
(function () {
	const tr = (s) => (typeof __ === "function" ? __(s) : s);

	const EXACT = {
		"Begin typing for results.": "Commencez à saisir pour voir les résultats.",
		"Quarter Day": "Quart de journée",
		"Half Day": "Demi-journée",
	};
	const MONTHS = {
		January: "janvier", February: "février", March: "mars", April: "avril", May: "mai", June: "juin",
		July: "juillet", August: "août", September: "septembre", October: "octobre", November: "novembre", December: "décembre",
	};
	const PATTERNS = [
		[/^(\d+) Filters? Applied$/, (m) => (m[1] === "1" ? "1 filtre appliqué" : `${m[1]} filtres appliqués`)],
		[/^Filter based on (.+)$/, (m) => `Filtrer selon ${tr(m[1])}`],
		[/^Cliquez pour trier par (.+)$/, (m) => `Cliquez pour trier par ${tr(m[1])}`],
	];

	function translate(text, inGantt) {
		const t = text.trim();
		if (!t) return null;
		if (EXACT[t]) return EXACT[t];
		if (inGantt && MONTHS[t]) return MONTHS[t];
		for (const [re, fn] of PATTERNS) {
			const m = t.match(re);
			if (m) return fn(m);
		}
		return null;
	}

	// Valeurs stockées en anglais (états, types, catégories) que Frappe affiche telles quelles : on les traduit avec le
	// dictionnaire de traductions, seulement dans les zones où elles apparaissent (graphiques, cellules filtrables).
	const VALUE_AREAS = ".frappe-chart text, .chart-legend text, .chart-legend, a.filterable, a.filterable span";

	function translateValues() {
		document.querySelectorAll(VALUE_AREAS).forEach((el) => {
			if (el.children.length && el.tagName.toLowerCase() !== "a") return;
			const t = (el.textContent || "").trim();
			if (!t || el.children.length) return;
			const fr = tr(t);
			if (fr && fr !== t) el.textContent = fr;
		});
		document.querySelectorAll("a.filterable[title], a.filterable[data-original-title]").forEach((el) => {
			["title", "data-original-title"].forEach((attr) => {
				const v = el.getAttribute(attr);
				const m = v && v.match(/^(.+?): (.+)$/);
				if (m) {
					const fr = `${tr(m[1])}: ${tr(m[2])}`;
					if (fr !== v) el.setAttribute(attr, fr);
				}
			});
		});
	}

	function run() {
		translateValues();
		const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
		const nodes = [];
		while (walker.nextNode()) nodes.push(walker.currentNode);
		nodes.forEach((node) => {
			const parent = node.parentElement;
			if (!parent || ["SCRIPT", "STYLE", "TEXTAREA", "INPUT"].includes(parent.tagName)) return;
			const replaced = translate(node.textContent, !!parent.closest(".gantt"));
			if (replaced && replaced !== node.textContent.trim()) node.textContent = replaced;
		});
		document.querySelectorAll("[title], [data-original-title], [aria-label]").forEach((el) => {
			["title", "data-original-title", "aria-label"].forEach((attr) => {
				const value = el.getAttribute(attr);
				if (!value) return;
				const replaced = translate(value, false);
				if (replaced && replaced !== value) el.setAttribute(attr, replaced);
			});
		});
	}

	let scheduled = false;
	function schedule() {
		if (scheduled) return;
		scheduled = true;
		window.setTimeout(() => {
			scheduled = false;
			run();
		}, 150);
	}

	$(document).on("startup", () => {
		run();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	});
})();
