// Navigation Cortex : une barre latérale présente sur toutes les pages du Desk, limitée à ce qui sert vraiment, selon les
// droits de la personne. Elle remplace la liste des espaces de Frappe (Comptabilité, Vente, Stock, Qualité, etc.) que le
// propriétaire d'une société ne peut de toute façon pas ouvrir. Elle montre aussi qui est en ligne et ce que l'équipe
// vient de faire (journal d'audit, en temps réel quand le serveur de sockets est disponible, sinon par relève).
(function () {
	const ICONS = {
		home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>',
		file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>',
		calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8 14h3M13 14h3M8 17.5h3"/>',
		check: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 10"/>',
		swap: '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
		box: '<path d="M12 3 4 7v10l8 4 8-4V7z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
		barcode: '<path d="M4 6v12M8 6v12M12 6v12M16 6v12M20 6v12" stroke-width="1.6"/>',
		users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 5a3.5 3.5 0 0 1 0 6.5M18 14.2A6.5 6.5 0 0 1 21.5 20"/>',
		receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
		wallet: '<path d="M4 7a2 2 0 0 1 2-2h11v4"/><rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="16.5" cy="13.5" r="1.2"/>',
		chart: '<path d="M4 20V5M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
		spark: '<path d="M12 3c.6 4.2 2.8 6.4 7 7-4.2.6-6.4 2.8-7 7-.6-4.2-2.8-6.4-7-7 4.2-.6 6.4-2.8 7-7z"/>',
		shield: '<path d="M12 3 5 6v5c0 4.6 3 8.3 7 10 4-1.7 7-5.4 7-10V6z"/>',
		globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18"/>',
		sliders: '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
		help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.7.4-1.1.9-1.1 1.8M12 17h.01"/>',
		plus: '<path d="M12 5v14M5 12h14"/>',
		chevrons: '<path d="m13 6-6 6 6 6M19 6l-6 6 6 6"/>',
		menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
	};

	const ALL = () => true;
	const can = (doctype) => () => !!(frappe.model && frappe.model.can_read && frappe.model.can_read(doctype));
	const hasRole = (...roles) => () => roles.some((r) => (frappe.user_roles || []).includes(r));
	const workspace = (name) => () => ((frappe.boot && frappe.boot.allowed_workspaces) || []).some((w) => w.name === name);

	// Chaque entrée : route, libellé, icône, règle d'affichage, routes qu'elle « possède » (pour l'état actif).
	const GROUPS = [
		{
			title: "Opérations",
			items: [
				{ id: "home", label: "Tableau de bord", icon: "home", href: "/app/cortex-rental", owns: ["cortex-rental"], show: ALL },
				{ id: "rentals", label: "Locations", icon: "file", href: "/app/cortex-rental-transaction", owns: ["cortex-rental-transaction"], show: can("Cortex Rental Transaction") },
				{ id: "availability", label: "Disponibilité", icon: "calendar", href: "/app/cortex-availability", owns: ["cortex-availability"], show: can("Cortex Rental Transaction") },
				{ id: "approvals", label: "Approbations", icon: "check", href: "/app/approval-request", owns: ["approval-request"], show: can("Approval Request"), badge: "approvals" },
				{ id: "operations", label: "Sorties et retours", icon: "swap", href: "/app/cortex-operations", owns: ["cortex-operations", "cortex-check-in"], show: workspace("Cortex Operations") },
			],
		},
		{
			title: "Parc",
			items: [
				{ id: "catalog", label: "Catalogue", icon: "box", href: "/app/cortex-rental-item-profile", owns: ["cortex-rental-item-profile", "cortex-catalog"], show: can("Cortex Rental Item Profile") },
				{ id: "serials", label: "Numéros de série", icon: "barcode", href: "/app/serial-no", owns: ["serial-no"], show: can("Serial No") },
			],
		},
		{
			title: "Clients et finance",
			items: [
				{ id: "customers", label: "Clients", icon: "users", href: "/app/customer", owns: ["customer"], show: can("Customer") },
				{ id: "invoices", label: "Factures", icon: "receipt", href: "/app/cortex-rental-invoice", owns: ["cortex-rental-invoice"], show: can("Cortex Rental Invoice") },
				{ id: "payments", label: "Paiements", icon: "wallet", href: "/app/cortex-rental-payment", owns: ["cortex-rental-payment"], show: can("Cortex Rental Payment") },
				{ id: "finance", label: "Finance", icon: "chart", href: "/app/cortex-finance", owns: ["cortex-finance", "cortex-finance-settings", "consignment-payout", "consignment-owner"], reports: ["Créances par client", "Taxes perçues", "Versements de consignation", "Relevé propriétaire"], show: workspace("Cortex Finance") },
			],
		},
		{
			title: "Assistant",
			items: [{ id: "assistant", label: "Assistant IA", icon: "spark", href: "/app/cortex-home", owns: ["cortex-home", "cortex-ai"], show: ALL }],
		},
		{
			title: "Administration",
			items: [
				{ id: "admin", label: "Équipe et règles", icon: "shield", href: "/app/cortex-admin", owns: ["cortex-admin", "rental-pricing-rule", "user", "audit-event"], show: workspace("Cortex Admin") },
				{ id: "website", label: "Site Web", icon: "globe", href: "/app/website", owns: ["website"], show: hasRole("System Manager", "Website Manager") },
				{ id: "settings", label: "Paramètres", icon: "sliders", href: "/app/erpnext-settings", owns: ["erpnext-settings", "integrations", "build"], show: hasRole("System Manager") },
			],
		},
	];

	const REPORT_OWNER = { "Disponibilité du parc": "availability", "Prochains départs et retours": "operations", "Activité des clients": "customers" };
	const STORE = "cortex_nav_collapsed";
	const SHORT = window.matchMedia("(max-width: 1100px)");
	const PHONE = window.matchMedia("(max-width: 768px)");

	function svg(name, size) {
		return `<svg viewBox="0 0 24 24" width="${size || 18}" height="${size || 18}" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
	}

	function el(tag, attrs, html) {
		const node = document.createElement(tag);
		Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
		if (html !== undefined) node.innerHTML = html;
		return node;
	}

	function readCollapsed() {
		try {
			const stored = window.localStorage.getItem(STORE);
			if (stored !== null) return stored === "1";
		} catch (e) {
			// Stockage indisponible : on retombe sur la largeur de l'écran.
		}
		return SHORT.matches;
	}

	function writeCollapsed(value) {
		try {
			window.localStorage.setItem(STORE, value ? "1" : "0");
		} catch (e) {
			// Sans importance : la préférence ne sera pas conservée.
		}
	}

	function initials(name) {
		return (name || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
	}

	function tint(seed) {
		let h = 0;
		for (const c of seed || "") h = (h * 31 + c.charCodeAt(0)) % 360;
		return `hsl(${h} 38% 88%)`;
	}

	function shortName(name) {
		const parts = (name || "").trim().split(/\s+/);
		return parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1][0]}.` : parts[0] || "";
	}

	window.cortex = window.cortex || {};

	class Nav {
		constructor() {
			this.nodes = {};
			this.badges = {};
			this.build();
			this.bind();
			this.refreshActive();
			this.refreshBadge();
			this.refreshTeam();
		}

		build() {
			document.body.classList.add("cx-nav-on");
			document.body.classList.toggle("cx-nav-collapsed", readCollapsed());
			const nav = el("nav", { id: "cx-nav", "aria-label": __("Navigation principale") });
			const top = el("div", { class: "cx-nav-top" });
			const create = el("a", { class: "cx-nav-create", href: "/app/cortex-rental-transaction/new" }, `${svg("plus", 16)}<span class="cx-label">${__("Nouvelle location")}</span>`);
			create.setAttribute("title", __("Nouvelle location"));
			const toggle = el("button", { type: "button", class: "cx-nav-toggle", "aria-label": __("Réduire ou agrandir le menu"), title: __("Réduire ou agrandir le menu") }, svg("chevrons", 16));
			toggle.addEventListener("click", () => this.toggleCollapsed());
			top.append(create, toggle);
			if (!can("Cortex Rental Transaction")() || !frappe.model.can_create("Cortex Rental Transaction")) create.hidden = true;
			nav.appendChild(top);

			const scroll = el("div", { class: "cx-nav-scroll" });
			GROUPS.forEach((group) => {
				const items = group.items.filter((item) => {
					try {
						return item.show();
					} catch (e) {
						return false;
					}
				});
				if (!items.length) return;
				const section = el("section", { class: "cx-nav-group" });
				section.appendChild(el("h2", { class: "cx-nav-title" }, `<span class="cx-label">${__(group.title)}</span>`));
				items.forEach((item) => {
					const link = el("a", { class: "cx-nav-item", href: item.href, "data-id": item.id, title: __(item.label) });
					link.innerHTML = `<span class="cx-nav-icon">${svg(item.icon)}</span><span class="cx-label">${__(item.label)}</span>`;
					if (item.badge) {
						const badge = el("span", { class: "cx-badge", hidden: "", "aria-live": "polite" });
						link.appendChild(badge);
						this.badges[item.badge] = badge;
					}
					link.addEventListener("click", (e) => {
						if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
						e.preventDefault();
						frappe.set_route(item.href.replace(/^\/app\//, ""));
						this.closeDrawer();
					});
					this.nodes[item.id] = { link, item };
					section.appendChild(link);
				});
				scroll.appendChild(section);
			});
			nav.appendChild(scroll);

			const team = el("div", { class: "cx-team", hidden: "" });
			team.innerHTML = `
				<button type="button" class="cx-team-head" aria-expanded="false" aria-controls="cx-activity">
					<span class="cx-team-dot"></span>
					<span class="cx-label cx-team-count"></span>
				</button>
				<ul class="cx-team-list" aria-label="${__("Équipe")}"></ul>`;
			nav.appendChild(team);
			this.nodes.team = team;

			const activity = el("div", { id: "cx-activity", class: "cx-activity", role: "dialog", "aria-label": __("Activité récente"), hidden: "" });
			document.body.appendChild(activity);
			this.nodes.activity = activity;
			team.querySelector(".cx-team-head").addEventListener("click", () => this.toggleActivity());
			document.addEventListener("click", (e) => {
				if (!activity.hidden && !activity.contains(e.target) && !team.contains(e.target)) this.toggleActivity(false);
			});
			document.addEventListener("keydown", (e) => {
				if (e.key === "Escape") {
					this.toggleActivity(false);
					this.closeDrawer();
				}
			});

			const backdrop = el("div", { id: "cx-nav-backdrop" });
			backdrop.addEventListener("click", () => this.closeDrawer());
			document.body.append(nav, backdrop);
			this.nodes.nav = nav;

			// Bouton « menu » de la barre du haut sur téléphone.
			const brand = document.querySelector("header.navbar .navbar-brand");
			if (brand && !document.querySelector(".cx-nav-burger")) {
				const burger = el("button", { type: "button", class: "cx-nav-burger", "aria-label": __("Ouvrir le menu"), "aria-expanded": "false" }, svg("menu", 20));
				burger.addEventListener("click", () => this.toggleDrawer());
				brand.parentNode.insertBefore(burger, brand);
				this.nodes.burger = burger;
			}
		}

		bind() {
			cortex.currentRoute = window.location.pathname;
			const refresh = () => {
				cortex.previousRoute = cortex.currentRoute;
				cortex.currentRoute = window.location.pathname;
				this.refreshActive();
				this.closeDrawer();
			};
			frappe.router.on("change", refresh);
			SHORT.addEventListener("change", () => {
				if (window.localStorage && window.localStorage.getItem(STORE) === null) document.body.classList.toggle("cx-nav-collapsed", SHORT.matches);
			});
			frappe.realtime && frappe.realtime.on("cortex_activity", (data) => this.onLiveActivity(data));
			this.ping();
			window.setInterval(() => this.ping(), 60000);
			window.setInterval(() => {
				this.refreshTeam();
				this.refreshBadge();
			}, 45000);
			document.addEventListener("visibilitychange", () => {
				if (document.visibilityState === "visible") {
					this.ping();
					this.refreshTeam();
				}
			});
		}

		// --- état actif
		currentOwner() {
			const parts = window.location.pathname.replace(/^\/app\/?/, "").split("/").map(decodeURIComponent);
			const first = parts[0] || "";
			if (first === "query-report") return REPORT_OWNER[parts[1]] || (this.nodes.finance && this.nodes.finance.item.reports.includes(parts[1]) ? "finance" : "rentals");
			for (const [id, { item }] of Object.entries(this.nodes)) {
				if (item && item.owns && item.owns.includes(first)) return id;
			}
			return null;
		}

		refreshActive() {
			const active = this.currentOwner();
			Object.entries(this.nodes).forEach(([id, node]) => {
				if (!node.link) return;
				const on = id === active;
				node.link.classList.toggle("active", on);
				if (on) node.link.setAttribute("aria-current", "page");
				else node.link.removeAttribute("aria-current");
			});
		}

		// --- menu
		toggleCollapsed() {
			const next = !document.body.classList.contains("cx-nav-collapsed");
			document.body.classList.toggle("cx-nav-collapsed", next);
			writeCollapsed(next);
		}

		toggleDrawer() {
			const open = !document.body.classList.contains("cx-nav-open");
			document.body.classList.toggle("cx-nav-open", open);
			if (this.nodes.burger) this.nodes.burger.setAttribute("aria-expanded", String(open));
		}

		closeDrawer() {
			document.body.classList.remove("cx-nav-open");
			if (this.nodes.burger) this.nodes.burger.setAttribute("aria-expanded", "false");
		}

		// --- pastille « à traiter »
		refreshBadge() {
			const badge = this.badges.approvals;
			if (!badge || !can("Approval Request")()) return;
			frappe
				.xcall("frappe.client.get_count", { doctype: "Approval Request", filters: { status: "Pending" } })
				.then((count) => {
					badge.textContent = count > 99 ? "99+" : String(count);
					badge.hidden = !count;
					badge.setAttribute("aria-label", __("{0} approbation(s) en attente", [count]));
				})
				.catch(() => {
					badge.hidden = true;
				});
		}

		// --- équipe et activité
		ping() {
			if (document.visibilityState === "hidden") return;
			frappe.xcall("cortex_rental.api.v1.presence.ping", {}, "POST").catch(() => {});
		}

		refreshTeam() {
			frappe
				.call({ method: "cortex_rental.api.v1.presence.team_activity_snapshot", type: "GET", freeze: false })
				.then((r) => this.renderTeam(r.message))
				.catch(() => {
					this.nodes.team.hidden = true;
				});
		}

		onLiveActivity(data) {
			window.clearTimeout(this.liveTimer);
			this.liveTimer = window.setTimeout(() => {
				this.refreshTeam();
				if (data && data.entity_type === "Approval Request") this.refreshBadge();
				this.refreshBadge();
			}, 600);
			this.pulse = data && data.actor;
		}

		renderTeam(data) {
			const team = this.nodes.team;
			if (!data || !data.team || data.team.length < 1) {
				team.hidden = true;
				return;
			}
			team.hidden = false;
			team.querySelector(".cx-team-count").textContent = __("{0} en ligne", [data.online_count]);
			team.querySelector(".cx-team-dot").classList.toggle("on", data.online_count > 0);
			const list = team.querySelector(".cx-team-list");
			list.innerHTML = "";
			data.team.slice(0, 6).forEach((m) => {
				const li = el("li", { class: "cx-member" + (m.online ? " online" : ""), title: `${m.full_name}${m.last_action ? " — " + m.last_action : ""}` });
				li.appendChild(this.avatar(m));
				list.appendChild(li);
			});
			this.renderActivity(data);
		}

		avatar(m) {
			const avatar = el("span", { class: "cx-avatar", style: `background-color:${tint(m.user)}` });
			if (m.image) avatar.style.backgroundImage = `url("${encodeURI(m.image)}")`;
			else avatar.textContent = initials(m.full_name);
			avatar.appendChild(el("i", { class: "cx-presence" }));
			return avatar;
		}

		renderActivity(data) {
			const panel = this.nodes.activity;
			panel.innerHTML = `<h3>${__("Équipe")}</h3>`;
			const people = el("ul", { class: "cx-people" });
			data.team.forEach((m) => {
				const li = el("li", { class: m.online ? "online" : "" });
				const text = el("span", { class: "cx-member-text" });
				const name = el("b");
				name.textContent = m.is_me ? `${m.full_name} (${__("vous")})` : m.full_name;
				const what = el("small");
				what.textContent = m.last_action ? `${m.last_action} · ${frappe.datetime.prettyDate(m.last_action_at)}` : m.online ? __("En ligne") : __("Hors ligne");
				text.append(name, what);
				li.append(this.avatar(m), text);
				people.appendChild(li);
			});
			panel.appendChild(people);
			panel.appendChild(el("h3", { class: "cx-activity-title" }, __("Activité récente")));
			const rows = data.activity || [];
			if (!rows.length) {
				panel.appendChild(el("p", { class: "cx-activity-empty" }, __("Aucune activité pour l'instant.")));
				return;
			}
			const list = el("ul");
			rows.forEach((row) => {
				const li = el("li");
				const link = el("a", { href: `/app/${frappe.router.slug(row.entity_type)}/${encodeURIComponent(row.entity_id)}` });
				const who = el("b");
				who.textContent = shortName(row.actor);
				link.append(who, document.createTextNode(` ${row.text} `));
				const ref = el("span", { class: "cx-ref" });
				ref.textContent = row.entity_id;
				const when = el("time");
				when.textContent = frappe.datetime.prettyDate(row.at);
				link.append(ref, when);
				li.appendChild(link);
				list.appendChild(li);
			});
			panel.appendChild(list);
		}

		toggleActivity(force) {
			const panel = this.nodes.activity;
			const open = force === undefined ? panel.hidden : force;
			panel.hidden = !open;
			this.nodes.team.querySelector(".cx-team-head").setAttribute("aria-expanded", String(open));
		}
	}

	// --- barre du haut : recherche lisible et raccourcis de l'aide
	function tidyNavbar() {
		const search = document.getElementById("navbar-search");
		if (search && !search.dataset.cx) {
			search.dataset.cx = "1";
			search.setAttribute("placeholder", __("Rechercher…"));
			search.setAttribute("aria-label", __("Rechercher ou taper une commande"));
			search.setAttribute("title", __("Rechercher ou taper une commande ({0})", [frappe.utils.is_mac() ? "⌘ G" : "Ctrl G"]));
		}
	}

	window.cortex = Object.assign(window.cortex || {}, {
		openAssistant() {
			window.dispatchEvent(new KeyboardEvent("keydown", { key: "j", ctrlKey: true, bubbles: true }));
			return false;
		},
		showShortcuts(event) {
			if (frappe.ui.toolbar && frappe.ui.toolbar.show_shortcuts) frappe.ui.toolbar.show_shortcuts(event);
			return false;
		},
	});

	$(document).on("startup", () => {
		if (!frappe.session || frappe.session.user === "Guest") return;
		// Les filtres rapides de Frappe (Assigné à, Établi par, Balises) sont masqués par défaut : la barre Cortex prend la place.
		// Un clic sur le bouton de la liste les réaffiche, et ce choix est conservé.
		try {
			if (window.localStorage.getItem("show_sidebar") === null) window.localStorage.setItem("show_sidebar", "false");
		} catch (e) {
			// Stockage indisponible : on garde le comportement de Frappe.
		}
		const roles = frappe.user_roles || [];
		if (!roles.length) return;
		window.requestAnimationFrame(() => {
			tidyNavbar();
			new Nav();
			new MutationObserver(tidyNavbar).observe(document.querySelector("header.navbar") || document.body, { childList: true, subtree: true });
		});
	});
})();
