// Garde contre une erreur JavaScript de Frappe Charts (code tiers) : quand une page à graphiques est quittée ou redessinée
// vite, l'observateur de taille d'un graphique déjà détaché relance `draw()`, qui retire un nœud qui n'est plus son enfant
// (« NotFoundError : removeChild »). Le graphique n'est plus à l'écran : l'erreur est sans effet visible, mais elle salit la
// console et les mesures d'erreurs. On enrobe `draw()` de chaque graphique pour ignorer SEULEMENT cette erreur-là.
(function () {
	if (typeof frappe === "undefined" || !frappe.Chart || frappe.Chart.__cxSafe) return;
	const patched = new WeakSet();

	function guard(instance) {
		// `draw` vit sur le prototype de base du graphique : on remonte la chaîne jusqu'à celui qui le possède.
		let proto = Object.getPrototypeOf(instance);
		while (proto && !Object.prototype.hasOwnProperty.call(proto, "draw")) proto = Object.getPrototypeOf(proto);
		if (!proto || patched.has(proto) || typeof proto.draw !== "function") return;
		patched.add(proto);
		const draw = proto.draw;
		proto.draw = function () {
			try {
				return draw.apply(this, arguments);
			} catch (error) {
				if (error && error.name === "NotFoundError") return undefined; // nœud déjà retiré : le graphique est parti
				throw error;
			}
		};
	}

	const Original = frappe.Chart;
	frappe.Chart = new Proxy(Original, {
		construct(target, args, newTarget) {
			const instance = Reflect.construct(target, args, newTarget === frappe.Chart ? target : newTarget);
			try {
				guard(instance);
			} catch (e) {
				/* garde facultative : jamais d'erreur à cause d'elle */
			}
			return instance;
		},
	});
	frappe.Chart.__cxSafe = true;
})();
