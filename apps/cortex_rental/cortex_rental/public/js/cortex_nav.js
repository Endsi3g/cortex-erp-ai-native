// Navigation Cortex : barre latérale présente sur toutes les pages du Desk, dans l'esprit de celle de Claude (marque et
// bouton de repli en haut, « Nouvelle location » comme première entrée, catégories repliables), avec les icônes des
// espaces d'origine. Elle ne garde que ce qui sert, selon les droits de la personne. L'indicateur « en ligne » de
// l'équipe vit dans la barre du haut (et non dans la barre latérale) ; il est mis à jour en temps réel.
(function () {
	const icon = (name, cls) => `<svg class="icon ${cls || "icon-md"}" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
	const PLUS = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>';
	const CHEVRON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>';
	const PANEL = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="4.5" width="17" height="15" rx="3"/><path d="M9.5 4.5v15"/></svg>';
	const MENU = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>';

	const ALL = () => true;
	const can = (doctype) => () => !!(frappe.model && frappe.model.can_read && frappe.model.can_read(doctype));
	const hasRole = (...roles) => () => roles.some((r) => (frappe.user_roles || []).includes(r));
	const workspace = (name) => () => ((frappe.boot && frappe.boot.allowed_workspaces) || []).some((w) => w.name === name);

	// Catégories de la grille de disponibilité (valeurs stockées ; libellés français via la traduction). Une seule
	// liste pour la barre et pour la page : quand la société pourra configurer ses catégories, on la lira du serveur.
	window.cortex = window.cortex || {};
	cortex.CATEGORIES = cortex.CATEGORIES || ["Lighting", "Power & Batteries", "Camera Bodies", "Cinema Lenses", "Grip & Rigging", "Monitors & Wireless Video", "Audio"];

	// Icônes : celles des espaces d'origine (assets, calendar, stock, list-alt, money-coins-1, message…).
	const GROUPS = [
		{
			title: "Opérations",
			items: [
				{ id: "home", label: "Tableau de bord", icon: "assets", href: "/app/cortex-rental", owns: ["cortex-rental"], show: ALL },
				{ id: "rentals", label: "Locations", icon: "sell", href: "/app/cortex-rental-transaction", owns: ["cortex-rental-transaction"], show: can("Cortex Rental Transaction") },
				{ id: "availability", label: "Disponibilité", icon: "calendar", href: "/app/cortex-availability", owns: ["cortex-availability"], show: can("Cortex Rental Transaction"), categories: true },
				{ id: "approvals", label: "Approbations", icon: "quality", href: "/app/approval-request", owns: ["approval-request"], show: can("Approval Request"), badge: "approvals" },
				{ id: "operations", label: "Sorties et retours", icon: "stock", href: "/app/cortex-operations", owns: ["cortex-operations", "cortex-check-in"], show: workspace("Cortex Operations") },
			],
		},
		{
			title: "Assistant",
			items: [{ id: "assistant", label: "Assistant IA", icon: "message-1", href: "/app/cortex-home", owns: ["cortex-home", "cortex-ai"], show: ALL }],
		},
		{
			title: "Parc",
			items: [
				{ id: "catalog", label: "Catalogue", icon: "list-alt", href: "/app/cortex-rental-item-profile", owns: ["cortex-rental-item-profile", "cortex-catalog"], show: can("Cortex Rental Item Profile") },
				{ id: "serials", label: "Numéros de série", icon: "retail", href: "/app/serial-no", owns: ["serial-no", "cortex-warehouse"], show: can("Serial No") },
			],
		},
		{
			title: "Clients et finance",
			items: [
				{ id: "customers", label: "Clients", icon: "customer", href: "/app/customer", owns: ["customer"], show: can("Customer") },
				{ id: "invoices", label: "Factures", icon: "file", href: "/app/cortex-rental-invoice", owns: ["cortex-rental-invoice"], show: can("Cortex Rental Invoice") },
				{ id: "payments", label: "Paiements", icon: "accounting", href: "/app/cortex-rental-payment", owns: ["cortex-rental-payment"], show: can("Cortex Rental Payment") },
				{ id: "finance", label: "Finance", icon: "money-coins-1", href: "/app/cortex-finance", owns: ["cortex-finance", "cortex-finance-settings", "consignment-payout", "consignment-owner", "cortex-journal-entry"], reports: ["Créances par client", "Taxes perçues", "Versements de consignation", "Relevé propriétaire", "Journal comptable", "Balance de vérification"], show: workspace("Cortex Finance") },
			],
		},
		{
			title: "Administration",
			bottom: true,
			items: [
				{ id: "admin", label: "Équipe et règles", icon: "setting-gear", href: "/app/cortex-admin", owns: ["cortex-admin", "rental-pricing-rule", "user", "audit-event", "cortex-ai-settings"], show: workspace("Cortex Admin") },
				{ id: "website", label: "Site Web", icon: "website", href: "/app/website", owns: ["website"], show: hasRole("System Manager", "Website Manager") },
				{ id: "settings", label: "Paramètres", icon: "setting", href: "/app/erpnext-settings", owns: ["erpnext-settings", "integrations", "build"], show: hasRole("System Manager") },
			],
		},
	];

	const REPORT_OWNER = { "Disponibilité du parc": "availability", "Prochains départs et retours": "operations", "Activité des clients": "customers" };
	const STORE = "cortex_nav_collapsed";
	const GROUP_STORE = "cortex_nav_groups";
	const SHORT = window.matchMedia("(max-width: 1100px)");

	function el(tag, attrs, html) {
		const node = document.createElement(tag);
		Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
		if (html !== undefined) node.innerHTML = html;
		return node;
	}

	function store(key, value) {
		try {
			if (value === undefined) return window.localStorage.getItem(key);
			window.localStorage.setItem(key, value);
		} catch (e) {
			// Stockage indisponible : la préférence ne sera pas conservée.
		}
		return null;
	}

	const initials = (name) => (name || "?").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
	const shortName = (name) => {
		const parts = (name || "").trim().split(/\s+/);
		return parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1][0]}.` : parts[0] || "";
	};
	function tint(seed) {
		let h = 0;
		for (const c of seed || "") h = (h * 31 + c.charCodeAt(0)) % 360;
		return `hsl(${h} 38% 88%)`;
	}

	class Nav {
		constructor() {
			this.nodes = {};
			this.badges = {};
			this.groups = JSON.parse(store(GROUP_STORE) || "{}");
			this.build();
			this.buildPresence();
			this.bind();
			this.refreshActive();
			this.refreshBadge();
			this.refreshTeam();
		}

		// --- construction
		build() {
			document.body.classList.add("cx-nav-on");
			const saved = store(STORE);
			document.body.classList.toggle("cx-nav-collapsed", saved === null ? SHORT.matches : saved === "1");

			const nav = el("nav", { id: "cx-nav", "aria-label": __("Navigation principale") });
			const head = el("div", { class: "cx-nav-head" });
			const brand = el("a", { class: "cx-brand", href: "/app/cortex-rental", "aria-label": "Cortex" }, `<img src="${frappe.boot.app_logo_url || "/assets/cortex_rental/images/cortex-logo.svg"}" alt="" width="26" height="26"><span class="cx-label">Cortex</span>`);
			const toggle = el("button", { type: "button", class: "cx-nav-toggle", "aria-label": __("Réduire ou agrandir le menu"), title: __("Réduire ou agrandir le menu") }, PANEL);
			toggle.addEventListener("click", () => this.toggleCollapsed());
			head.append(brand, toggle);
			nav.appendChild(head);

			const scroll = el("div", { class: "cx-nav-scroll" });
			const identity = this.identity();
			if (identity) scroll.appendChild(identity);
			if (can("Cortex Rental Transaction")() && frappe.model.can_create("Cortex Rental Transaction")) {
				const create = el("a", { class: "cx-new", href: "/app/cortex-rental-transaction/new", title: __("Nouvelle location") }, `<span class="cx-new-plus">${PLUS}</span><span class="cx-label">${__("Nouvelle location")}</span>`);
				create.addEventListener("click", (e) => this.go(e, create.getAttribute("href")));
				scroll.appendChild(create);
			}

			GROUPS.forEach((group) => {
				const items = group.items.filter((item) => {
					try {
						return item.show();
					} catch (e) {
						return false;
					}
				});
				if (!items.length) return;
				const open = this.groups[group.title] !== false;
				const section = el("section", { class: "cx-group" + (open ? "" : " closed") + (group.bottom ? " cx-group-bottom" : "") });
				const title = el("button", { type: "button", class: "cx-group-title", "aria-expanded": String(open) }, `<span class="cx-label">${__(group.title)}</span><span class="cx-chev">${CHEVRON}</span>`);
				const body = el("div", { class: "cx-group-body" });
				const inner = el("div", { class: "cx-group-inner" });
				title.addEventListener("click", () => {
					const closed = section.classList.toggle("closed");
					title.setAttribute("aria-expanded", String(!closed));
					this.groups[group.title] = !closed;
					store(GROUP_STORE, JSON.stringify(this.groups));
				});
				items.forEach((item) => inner.appendChild(this.item(item)));
				body.appendChild(inner);
				section.append(title, body);
				scroll.appendChild(section);
			});
			nav.appendChild(scroll);
			nav.appendChild(this.account());

			const backdrop = el("div", { id: "cx-nav-backdrop" });
			backdrop.addEventListener("click", () => this.closeDrawer());
			document.body.append(nav, backdrop);
			this.nodes.nav = nav;

			// Bouton « menu » de la barre du haut (téléphone).
			const navbarBrand = document.querySelector("header.navbar .navbar-brand");
			if (navbarBrand && !document.querySelector(".cx-nav-burger")) {
				const burger = el("button", { type: "button", class: "cx-nav-burger", "aria-label": __("Ouvrir le menu"), "aria-expanded": "false" }, MENU);
				burger.addEventListener("click", () => this.toggleDrawer());
				navbarBrand.parentNode.insertBefore(burger, navbarBrand);
				this.nodes.burger = burger;
			}
		}

		// Profil en bas de la barre (comme Claude) : avatar, nom, courriel et menu (profil, déconnexion).
		account() {
			const me = frappe.session.user;
			const name = frappe.session.user_fullname || me;
			const image = frappe.user_info(me).image;
			const esc = frappe.utils.escape_html;
			const mark = image
				? `<img class="cx-avatar" src="${esc(image)}" alt="" width="30" height="30">`
				: `<span class="cx-avatar cx-avatar-initials" style="background:${tint(me)}">${esc(initials(name))}</span>`;
			const box = el("div", { class: "cx-account" });
			const trigger = el("button", { type: "button", class: "cx-account-btn", "aria-haspopup": "menu", "aria-expanded": "false", title: name });
			trigger.innerHTML = `${mark}<span class="cx-label cx-account-text"><strong>${esc(name)}</strong><small>${esc(me)}</small></span><span class="cx-label cx-account-more">${CHEVRON}</span>`;
			const menu = el("div", { class: "cx-account-menu", role: "menu", hidden: "" });
			const entry = (label, run) => {
				const b = el("button", { type: "button", role: "menuitem", class: "cx-account-item" }, esc(label));
				b.addEventListener("click", () => {
					menu.hidden = true;
					trigger.setAttribute("aria-expanded", "false");
					run();
				});
				return b;
			};
			menu.append(
				entry(__("Mon profil"), () => frappe.set_route("Form", "User", me)),
				entry(__("Aide et support"), () => frappe.new_doc("Cortex Support Request")),
				entry(__("Se déconnecter"), () => frappe.app.logout())
			);
			trigger.addEventListener("click", () => {
				menu.hidden = !menu.hidden;
				trigger.setAttribute("aria-expanded", String(!menu.hidden));
			});
			document.addEventListener("click", (e) => {
				if (!menu.hidden && !box.contains(e.target)) {
					menu.hidden = true;
					trigger.setAttribute("aria-expanded", "false");
				}
			});
			box.append(menu, trigger);
			return box;
		}

		// Société de la personne connectée : logo et nom, sous la marque (lecture seule, fournis par le serveur).
		identity() {
			const home = (frappe.boot && frappe.boot.cortex_home) || {};
			if (!home.company) return null;
			const card = el("a", { class: "cx-company", href: "/app/cortex-rental", title: home.company });
			const mark = home.company_logo
				? `<img src="${frappe.utils.escape_html(home.company_logo)}" alt="" width="28" height="28">`
				: `<span class="cx-company-initials" style="background:${tint(home.company)}">${frappe.utils.escape_html(initials(home.company))}</span>`;
			card.innerHTML = `${mark}<span class="cx-label cx-company-text"><strong>${frappe.utils.escape_html(home.company)}</strong><small>${__("Votre société")}</small></span>`;
			card.addEventListener("click", (e) => this.go(e, "/app/cortex-rental"));
			return card;
		}

		item(item) {
			const wrap = el("div", { class: "cx-item-wrap" });
			const link = el("a", { class: "cx-nav-item", href: item.href, "data-id": item.id, title: __(item.label) });
			link.innerHTML = `<span class="cx-nav-icon">${icon(item.icon)}</span><span class="cx-label">${__(item.label)}</span>`;
			if (item.badge) {
				const badge = el("span", { class: "cx-badge", hidden: "", "aria-live": "polite" });
				link.appendChild(badge);
				this.badges[item.badge] = badge;
			}
			link.addEventListener("click", (e) => this.go(e, item.href));
			wrap.appendChild(link);
			this.nodes[item.id] = { link, item, wrap };
			if (item.categories) {
				const sub = el("div", { class: "cx-sub" });
				const subInner = el("div", { class: "cx-sub-inner" });
				cortex.CATEGORIES.forEach((value) => {
					const href = `${item.href}/${encodeURIComponent(value)}`;
					const child = el("a", { class: "cx-sub-item", href, "data-category": value }, `<span class="cx-label">${__(value)}</span>`);
					child.addEventListener("click", (e) => this.go(e, href));
					subInner.appendChild(child);
				});
				sub.appendChild(subInner);
				wrap.appendChild(sub);
				this.nodes[item.id].sub = sub;
			}
			return wrap;
		}

		go(event, href) {
			if (event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
			event.preventDefault();
			frappe.set_route(href.replace(/^\/app\//, "").split("/").map(decodeURIComponent));
			this.closeDrawer();
		}

		// --- indicateur « en ligne » dans la barre du haut
		buildPresence() {
			const list = document.querySelector("header.navbar .navbar-collapse ul.navbar-nav");
			if (!list || list.querySelector(".cx-presence-li")) return;
			const li = el("li", { class: "nav-item cx-presence-li", hidden: "" });
			li.innerHTML = `<button type="button" class="cx-pill" aria-expanded="false" aria-controls="cx-activity" title="${__("Équipe en ligne")}"><span class="cx-stack"></span><span class="cx-pill-count"></span></button>`;
			list.insertBefore(li, list.firstChild);
			const panel = el("div", { id: "cx-activity", class: "cx-activity", role: "dialog", "aria-label": __("Activité de l'équipe"), hidden: "" });
			document.body.appendChild(panel);
			this.nodes.presence = li;
			this.nodes.activity = panel;
			li.querySelector(".cx-pill").addEventListener("click", () => this.toggleActivity());
			document.addEventListener("click", (e) => {
				if (!panel.hidden && !panel.contains(e.target) && !li.contains(e.target)) this.toggleActivity(false);
			});
		}

		bind() {
			cortex.currentRoute = window.location.pathname;
			frappe.router.on("change", () => {
				cortex.previousRoute = cortex.currentRoute;
				cortex.currentRoute = window.location.pathname;
				this.refreshActive();
				this.closeDrawer();
			});
			SHORT.addEventListener("change", () => {
				if (store(STORE) === null) document.body.classList.toggle("cx-nav-collapsed", SHORT.matches);
			});
			document.addEventListener("keydown", (e) => {
				if (e.key === "Escape") {
					this.toggleActivity(false);
					this.closeDrawer();
				}
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
		parts() {
			return window.location.pathname.replace(/^\/app\/?/, "").split("/").map(decodeURIComponent);
		}

		currentOwner() {
			const parts = this.parts();
			const first = parts[0] || "";
			if (first === "query-report") return REPORT_OWNER[parts[1]] || (this.nodes.finance && this.nodes.finance.item.reports.includes(parts[1]) ? "finance" : "rentals");
			for (const [id, node] of Object.entries(this.nodes)) {
				if (node.item && node.item.owns && node.item.owns.includes(first)) return id;
			}
			return null;
		}

		refreshActive() {
			const active = this.currentOwner();
			const parts = this.parts();
			Object.entries(this.nodes).forEach(([id, node]) => {
				if (!node.link) return;
				const on = id === active;
				node.link.classList.toggle("active", on);
				if (on) node.link.setAttribute("aria-current", "page");
				else node.link.removeAttribute("aria-current");
				if (node.sub) {
					node.sub.classList.toggle("open", on);
					node.sub.querySelectorAll(".cx-sub-item").forEach((child) => {
						child.classList.toggle("active", on && parts[1] === child.dataset.category);
					});
				}
			});
			// Le groupe de la page courante s'ouvre s'il était replié.
			const current = this.nodes[active];
			if (current && current.wrap) {
				const section = current.wrap.closest(".cx-group");
				if (section && section.classList.contains("closed")) section.classList.remove("closed");
			}
		}

		// --- menu
		toggleCollapsed() {
			const next = !document.body.classList.contains("cx-nav-collapsed");
			document.body.classList.toggle("cx-nav-collapsed", next);
			store(STORE, next ? "1" : "0");
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
					if (this.nodes.presence) this.nodes.presence.hidden = true;
				});
		}

		// Devis accepté par un client et pas encore réservé : alerte avec un bouton « Réserver ».
		offerReservation(data) {
			if (!data || !data.reserve || !frappe.model.can_write("Cortex Rental Transaction")) return;
			const name = data.reserve;
			const actions = {};
			actions[__("Réserver")] = () =>
				frappe.xcall("cortex_rental.api.v1.rentals.request_reservation", { name }, "POST").then((r) => {
					const failed = r && r.errors && r.errors.length;
					frappe.show_alert(
						{ message: failed ? r.errors[0].message : __("Matériel réservé pour {0}.", [name]), indicator: failed ? "orange" : "green" },
						8
					);
					if (cur_frm && cur_frm.doc && cur_frm.doc.name === name) cur_frm.reload_doc();
				});
			actions[__("Ouvrir")] = () => frappe.set_route("Form", "Cortex Rental Transaction", name);
			frappe.show_alert({ message: `${frappe.utils.escape_html(data.actor || "")} ${frappe.utils.escape_html(data.text || "")}`, indicator: "orange" }, 20, actions);
		}

		onLiveActivity(data) {
			this.offerReservation(data);
			window.clearTimeout(this.liveTimer);
			this.liveTimer = window.setTimeout(() => {
				this.refreshTeam();
				this.refreshBadge();
			}, 600);
		}

		avatar(m) {
			const avatar = el("span", { class: "cx-avatar" + (m.online ? " online" : ""), style: `background-color:${tint(m.user)}` });
			if (m.image) avatar.style.backgroundImage = `url("${encodeURI(m.image)}")`;
			else avatar.textContent = initials(m.full_name);
			avatar.appendChild(el("i", { class: "cx-presence" }));
			return avatar;
		}

		renderTeam(data) {
			const li = this.nodes.presence;
			if (!li) return;
			if (!data || !data.team || !data.team.length) {
				li.hidden = true;
				return;
			}
			li.hidden = false;
			li.querySelector(".cx-pill-count").textContent = __("{0} en ligne", [data.online_count]);
			li.classList.toggle("live", data.online_count > 0);
			const stack = li.querySelector(".cx-stack");
			stack.innerHTML = "";
			data.team.filter((m) => m.online).slice(0, 3).forEach((m) => stack.appendChild(this.avatar(m)));
			this.renderActivity(data);
		}

		renderActivity(data) {
			const panel = this.nodes.activity;
			panel.innerHTML = `<h3>${__("Équipe")}</h3>`;
			const people = el("ul", { class: "cx-people" });
			data.team.forEach((m) => {
				const row = el("li", { class: m.online ? "online" : "" });
				const text = el("span", { class: "cx-member-text" });
				const name = el("b");
				name.textContent = m.is_me ? `${m.full_name} (${__("vous")})` : m.full_name;
				const what = el("small");
				what.textContent = m.last_action ? `${m.last_action} · ${frappe.datetime.prettyDate(m.last_action_at)}` : m.online ? __("En ligne") : __("Hors ligne");
				text.append(name, what);
				row.append(this.avatar(m), text);
				people.appendChild(row);
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
				const item = el("li");
				const link = el("a", { href: `/app/${frappe.router.slug(row.entity_type)}/${encodeURIComponent(row.entity_id)}` });
				const who = el("b");
				who.textContent = shortName(row.actor);
				link.append(who, document.createTextNode(` ${row.text} `));
				const ref = el("span", { class: "cx-ref" });
				ref.textContent = row.entity_id;
				const when = el("time");
				when.textContent = frappe.datetime.prettyDate(row.at);
				link.append(ref, when);
				item.appendChild(link);
				list.appendChild(item);
			});
			panel.appendChild(list);
		}

		toggleActivity(force) {
			const panel = this.nodes.activity;
			if (!panel) return;
			const open = force === undefined ? panel.hidden : force;
			panel.hidden = !open;
			const pill = this.nodes.presence && this.nodes.presence.querySelector(".cx-pill");
			if (pill) pill.setAttribute("aria-expanded", String(open));
		}
	}

	// --- barre du haut : recherche lisible
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
		if (!(frappe.user_roles || []).length) return;
		// Les filtres rapides de Frappe (Assigné à, Établi par, Balises) sont masqués par défaut : un clic sur leur bouton
		// dans la liste les réaffiche, et ce choix est conservé.
		if (store("show_sidebar") === null) store("show_sidebar", "false");
		window.requestAnimationFrame(() => {
			tidyNavbar();
			new Nav();
			new MutationObserver(tidyNavbar).observe(document.querySelector("header.navbar") || document.body, { childList: true, subtree: true });
		});
	});
})();
