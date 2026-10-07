// Sous-titre de chaque page : une phrase qui dit à quoi sert l'écran, sous le titre (listes, espaces, pages et rapports).
// Les textes sont ceux du produit, en français ; aucune donnée n'est inventée ici.
(function () {
	const T = (s) => (typeof __ === "function" ? __(s) : s);

	const SUBTITLES = {
		// Espaces et pages
		"cortex-rental": "Vue d'ensemble de votre activité de location : ce qui part, ce qui revient et ce qui attend une décision.",
		"cortex-operations": "Sorties, retours et contrôles du matériel : tout ce qui se passe au comptoir aujourd'hui.",
		"cortex-catalog": "Votre catalogue : équipements loués, tarifs journaliers, forfaits et règles de prix.",
		"cortex-warehouse": "Le parc physique : numéros de série, état du matériel, quarantaine et réparations.",
		"cortex-finance": "Facturation, encaissements, taxes (TPS et TVQ), écritures comptables et versements de consignation.",
		"cortex-ai": "L'assistant consulte vos données et prépare des propositions. Vous décidez : rien n'est confirmé sans votre approbation.",
		"cortex-home": "L'assistant consulte vos données et prépare des propositions. Vous décidez : rien n'est confirmé sans votre approbation.",
		"cortex-admin": "Équipe et rôles, règles tarifaires, réglages de l'assistant et journal d'audit de votre société.",
		"cortex-setup": "Les informations de votre entreprise et les premiers réglages, étape par étape.",
		"cortex-account/profil": "Votre identité dans Cortex : photo, nom, téléphone, et ce qui vous attend aujourd'hui.",
		"cortex-account/statistiques": "Ce que vous avez fait, avec des chiffres tirés de vos dossiers. Chaque chiffre ouvre la liste qui le compose.",
		"cortex-account/approbations": "Les demandes que vous avez faites et les décisions que vous avez prises, avec le motif.",
		"cortex-account/activite": "Votre historique complet, ou celui de l'équipe : qui a fait quoi, et qui a confirmé.",
		"cortex-account/securite": "Votre mot de passe, les appareils connectés (avec déconnexion à distance) et vos connexions récentes.",
		"cortex-account/notifications": "Vos alertes dans l'application et par courriel : choisissez celles qui vous servent.",
		"cortex-account/societe": "Votre société, votre rôle, ce que votre compte peut faire et l'équipe.",
		"cortex-availability": "Combien d'unités de chaque équipement restent libres, jour par jour. Indicatif : le serveur revérifie au moment de réserver.",
		// Listes (DocTypes)
		"cortex-rental-transaction": "Chaque location regroupe un client, une période et le matériel loué. Elle avance de Devis à Clos : réservation, contrat approuvé, sortie, retour.",
		"approval-request": "Les décisions à prendre : un humain approuve ou refuse chaque contrat. L'assistant propose, il ne décide jamais.",
		"cortex-rental-item-profile": "Les équipements que votre société loue : tarif journalier, valeur de remplacement, catégorie, quantité ou numéros de série.",
		"serial-no": "Chaque exemplaire physique du matériel et son état : actif, en réparation, manquant ou en quarantaine.",
		customer: "Les clients de votre société (productions, agences, studios). Ils figurent sur les devis, les contrats et les factures.",
		"cortex-rental-invoice": "Factures d'acompte (à la réservation) et finales (à la clôture), avec TPS et TVQ. Émises automatiquement par Cortex.",
		"cortex-rental-payment": "Paiements et remboursements reçus, liés à une facture. Un paiement enregistré ne se modifie pas.",
		"cortex-finance-settings": "Taux de taxes, acompte, échéance des factures et règle des frais de retard de votre société.",
		"cortex-journal-entry": "Écritures comptables équilibrées, générées à chaque facture et paiement, prêtes pour votre comptable.",
		"cortex-support-request": "Vos questions, problèmes et suggestions pour l'équipe Cortex.",
		"cortex-check-in": "Les retours de matériel : état constaté, pièces manquantes et décision (remise en stock, réparation, quarantaine).",
		"cortex-inbound-request": "Les demandes entrantes (courriel, formulaire) à transformer en devis.",
		"consignment-payout": "Les versements dus aux propriétaires de matériel en consignation, calculés à chaque location.",
		"consignment-owner": "Les propriétaires de matériel en consignation et leur pourcentage.",
		"rental-pricing-rule": "Les règles de prix, par exemple : une semaine se facture 3 jours.",
		"audit-event": "Le journal d'audit : qui a fait quoi et quand. Il ne se modifie jamais.",
		"cortex-ai-settings": "Le modèle d'IA utilisé, les outils autorisés et le budget mensuel de votre société.",
		// Rapports
		"Disponibilité du parc": "Pour une période donnée : le parc, ce qui est réservé et ce qui reste libre.",
		"Prochains départs et retours": "Ce qui doit partir et revenir dans les prochains jours, y compris les retours en retard.",
		"Activité des clients": "Nombre de locations et montant par client.",
		"Utilisation du parc": "Jours loués, taux d'utilisation et revenu par équipement, pour savoir quoi racheter et quoi retirer.",
		"Créances par client": "Les factures encore ouvertes, classées selon leur retard de paiement.",
		"Taxes perçues": "TPS et TVQ facturées par mois : la base de votre déclaration de taxes.",
		"Versements de consignation": "Ce qui est dû à chaque propriétaire en consignation.",
		"Relevé propriétaire": "Le détail des locations et des montants pour un propriétaire de matériel.",
		"Journal comptable": "Toutes les écritures comptables d'une période, avec leur source.",
		"Balance de vérification": "Total des débits et des crédits par compte : doit toujours s'équilibrer.",
	};

	function key() {
		const parts = window.location.pathname.replace(/^\/app\/?/, "").split("/").map(decodeURIComponent);
		const first = parts[0] || "";
		if (first === "query-report") return parts[1];
		if (first === "cortex-account") return `cortex-account/${parts[1] || "profil"}`;
		if (parts.length === 1 || parts[1] === "view" || first === "cortex-availability") return first;
		return null; // formulaires : le titre est le nom de la fiche
	}

	const parts = () => window.location.pathname.replace(/^\/app\/?/, "").split("/").map(decodeURIComponent);

	// Le titre de la page est celui de l'entrée de la barre latérale (« Locations », pas « Location »).
	function alignTitle(page) {
		const here = cortex.NAV && cortex.NAV.locate(parts());
		const p = parts();
		if (!here || p[0] === "query-report" || p[0] === "cortex-home") return;
		if (!(p.length === 1 || p[1] === "view")) return;
		if (here.item.href.replace(/^\/app\//, "") !== p[0]) return;
		const title = page.querySelector(".page-head .title-text");
		const label = T(here.item.label);
		if (title && title.textContent !== label) title.textContent = label;
	}

	// Fil d'Ariane : « Groupe › Page › Fiche », dans la langue de l'interface.
	function breadcrumbs() {
		const list = document.getElementById("navbar-breadcrumbs");
		const p = parts();
		const here = cortex.NAV && cortex.NAV.locate(p);
		if (list && p[0] === "cortex-account" && here) {
			list.innerHTML = `<li><span class="cx-bc-group">${T(here.group.title)}</span></li><li><span>${T(here.item.label)}</span></li>`;
			list.style.display = "";
			return;
		}
		if (list && p[0] === "cortex-home") {
			// « Assistant IA › Conversation » : « Assistant IA » ramène à l'écran d'accueil sans effacer l'historique.
			const inChat = !!(window.cortex_home_state && window.cortex_home_state.inChat);
			list.innerHTML = "";
			const first = document.createElement("li");
			if (inChat) {
				const a = document.createElement("a");
				a.href = "/app/cortex-home";
				a.textContent = T("Assistant IA");
				a.addEventListener("click", (event) => {
					event.preventDefault();
					window.dispatchEvent(new CustomEvent("cortex-home:reset"));
				});
				first.appendChild(a);
				const second = document.createElement("li");
				const span = document.createElement("span");
				span.textContent = T("Conversation");
				second.appendChild(span);
				list.append(first, second);
			} else {
				const span = document.createElement("span");
				span.textContent = T("Assistant IA");
				first.appendChild(span);
				list.appendChild(first);
			}
			list.style.display = "";
			return;
		}
		if (!list || !here) return;
		const crumbs = [{ text: T(here.group.title) }];
		const mainSlug = here.item.href.replace(/^\/app\//, "");
		crumbs.push({ text: T(here.item.label), href: here.item.href, last: p[0] === mainSlug && (p.length === 1 || p[1] === "view") });
		if (p[0] === "query-report") crumbs.push({ text: T(p[1]) });
		else if (p[0] !== mainSlug) crumbs.push({ text: T(p[0].replace(/-/g, " ")), href: `/app/${p[0]}` });
		if (p[0] === mainSlug && p.length > 1 && p[1] !== "view") {
			crumbs.push({ text: p[1].startsWith("new-") ? T("Nouveau") : here.item.categories ? T(p[1]) : p[1] });
		}
		list.innerHTML = "";
		crumbs.forEach((crumb, index) => {
			const li = document.createElement("li");
			const isLast = index === crumbs.length - 1;
			if (crumb.href && !isLast) {
				const a = document.createElement("a");
				a.href = crumb.href;
				a.textContent = crumb.text;
				li.appendChild(a);
			} else {
				const span = document.createElement("span");
				span.textContent = crumb.text;
				if (index === 0) span.className = "cx-bc-group";
				li.appendChild(span);
			}
			list.appendChild(li);
		});
		list.style.display = "";
	}

	function apply() {
		document.querySelectorAll(".page-container").forEach((page) => {
			if (page.style.display !== "none") alignTitle(page);
		});
		breadcrumbs();
		const sub = SUBTITLES[key()];
		document.querySelectorAll(".page-container").forEach((page) => {
			if (page.style.display === "none") return;
			const slot = page.querySelector(".page-head .title-area .sub-heading");
			if (!slot) return;
			if (!sub) {
				if (slot.dataset.cx) {
					slot.textContent = "";
					slot.classList.add("hide");
					delete slot.dataset.cx;
				}
				return;
			}
			const text = T(sub);
			if (slot.textContent !== text) slot.textContent = text;
			slot.dataset.cx = "1";
			slot.classList.remove("hide");
			slot.classList.add("cx-page-sub");
		});
	}

	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		window.requestAnimationFrame(() => {
			queued = false;
			apply();
		});
	}

	$(document).on("startup", () => {
		const native = frappe.breadcrumbs.update.bind(frappe.breadcrumbs);
		frappe.breadcrumbs.update = function () {
			native();
			breadcrumbs();
		};
		schedule();
		window.addEventListener("cortex-home:state", schedule);
		new MutationObserver(schedule).observe(document.getElementById("body") || document.body, { childList: true, subtree: true });
	});
	cortex.pageSubtitles = SUBTITLES;
})();
