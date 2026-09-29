// Host for the Cortex screens built with Vue 3 + Frappe UI (public/frontend, `npm run build:desk`).
//
// Each Desk Page (cortex-ops-overview, cortex-rentals, ...) is a thin shell that calls
// `cortex_rental.host.mount(wrapper)`. The Desk keeps the URL, the breadcrumbs, the navbar and the
// workspace sidebar; the bundle renders the screen inside `.cortex-root` and hands every
// page-changing link back to `frappe.set_route`.
//
// Plain script (not an esbuild bundle) on purpose: Frappe UI does not build under `bench build`'s
// esbuild, so the screens are built by Vite and loaded here as an ES module.

frappe.provide("cortex_rental");

(function () {
	const BASE = "/assets/cortex_rental/frontend/dist-desk";
	const ENTRY = `${BASE}/cortex-desk.js`;
	const STYLE = `${BASE}/cortex-desk.css`;
	// SPA paths that live in a Desk page with another name.
	const ROUTE_ALIASES = [[/^\/app\/cortex-rental\/new$/, ["cortex-transaction-composer"]]];
	// A Workspace slug always wins over a Page of the same name, and the hub / group workspaces own
	// `cortex-rental` and `cortex-operations`. The screens behind those SPA paths are registered
	// under other Page names.
	const PAGE_ALIASES = { "cortex-operations": "cortex-ops-overview", "cortex-rental": "cortex-rental-detail" };
	const SPA_ALIASES = Object.fromEntries(Object.entries(PAGE_ALIASES).map(([spa, page]) => [page, spa]));

	let modulePromise = null;

	function version() {
		return (frappe.boot && (frappe.boot.build_version || frappe.boot.versions?.frappe)) || "";
	}

	function ensureStyle() {
		if (document.getElementById("cortex-desk-style")) return;
		const link = document.createElement("link");
		link.id = "cortex-desk-style";
		link.rel = "stylesheet";
		link.href = `${STYLE}?v=${encodeURIComponent(version())}`;
		document.head.appendChild(link);
	}

	function loadModule() {
		if (!modulePromise) {
			ensureStyle();
			modulePromise = import(`${ENTRY}?v=${encodeURIComponent(version())}`).catch((error) => {
				modulePromise = null;
				throw error;
			});
		}
		return modulePromise;
	}

	function toDeskRoute(fullPath) {
		const [pathname, query = ""] = fullPath.split("?");
		const options = query ? Object.fromEntries(new URLSearchParams(query)) : null;
		for (const [pattern, route] of ROUTE_ALIASES) {
			if (pattern.test(pathname)) return { route, options };
		}
		const route = pathname
			.replace(/^\/app\//, "")
			.split("/")
			.filter(Boolean)
			.map(decodeURIComponent);
		if (PAGE_ALIASES[route[0]]) route[0] = PAGE_ALIASES[route[0]];
		return { route, options };
	}

	function navigate(fullPath) {
		const { route, options } = toDeskRoute(fullPath);
		frappe.route_options = options;
		frappe.set_route(...route);
	}

	function currentPath() {
		const route = (frappe.get_route && frappe.get_route()) || [];
		const query = frappe.route_options ? new URLSearchParams(frappe.route_options).toString() : "";
		frappe.route_options = null;
		if (route[0] === "cortex-transaction-composer") return `/app/cortex-rental/new${query ? `?${query}` : ""}`;
		if (SPA_ALIASES[route[0]]) route[0] = SPA_ALIASES[route[0]];
		return `/app/${route.map(encodeURIComponent).join("/")}${query ? `?${query}` : ""}`;
	}

	function showFailure(host, error) {
		const message = document.createElement("div");
		message.setAttribute("role", "alert");
		message.style.cssText = "max-width:40rem;margin:2rem auto;padding:1rem 1.5rem;border:1px solid #d0e0d7;border-radius:8px;background:#fff;font:14px/1.5 Inter,system-ui,sans-serif;color:#08120d";
		const title = document.createElement("strong");
		title.textContent = "L'interface Cortex n'a pas pu se charger.";
		const detail = document.createElement("p");
		detail.style.margin = "0.5rem 0 0";
		detail.textContent =
			"Le bundle est peut-être absent: exécutez « npm run build:desk » dans apps/cortex_rental/cortex_rental/public/frontend, puis « bench build » et rechargez. " +
			`Détail: ${error && error.message ? error.message : error}`;
		message.append(title, detail);
		host.replaceChildren(message);
	}

	function unmount(wrapper) {
		if (wrapper.__cortexScreen) {
			wrapper.__cortexScreen.unmount();
			wrapper.__cortexScreen = null;
		}
	}

	async function mount(wrapper) {
		const $main = $(wrapper).find(".layout-main-section");
		$(wrapper).find(".page-head").hide();
		$main.css({ padding: 0 });

		unmount(wrapper);
		const host = document.createElement("div");
		host.className = "cortex-root";
		$main.empty().append(host);

		const path = currentPath();
		try {
			const bundle = await loadModule();
			wrapper.__cortexScreen = await bundle.mountCortexScreen(host, { path, navigate });
		} catch (error) {
			showFailure(host, error);
		}
	}

	cortex_rental.host = { mount, unmount, toDeskRoute };

	// A company owner with an unfinished setup lands on the assistant once per browser session, only
	// from the Desk home: any other destination (or a later visit) is left alone.
	$(document).on("startup", function () {
		const pending = frappe.boot && frappe.boot.cortex_onboarding;
		if (!pending) return;
		let seen = false;
		try {
			seen = sessionStorage.getItem("cortex_onboarding_prompted") === "1";
		} catch (e) {}
		const path = window.location.pathname.replace(/\/+$/, "");
		if (seen || !["/app", "/app/home"].includes(path)) return;
		try {
			sessionStorage.setItem("cortex_onboarding_prompted", "1");
		} catch (e) {}
		frappe.set_route(pending.route);
	});
})();
