// Mesure d'usage (PostHog) : charge la bibliothèque seulement si le site a une clé valide (`frappe.boot.cortex_analytics`,
// voir services/analytics.py). Sans clé, ou si la personne a activé « Ne pas me suivre » (DNT / Global Privacy Control),
// rien n'est chargé ni envoyé. Les clics, pages, erreurs et performances sont capturés; les enregistrements de session
// masquent les champs de saisie et le texte des données d'affaires (clients, montants, messages de l'assistant).
(function () {
	const cfg = frappe.boot && frappe.boot.cortex_analytics;
	if (!cfg || !cfg.key) return;
	if (navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true) return;

	window.cortex = window.cortex || {};
	// Événement métier explicite : cortex.track("devis_cree", { source: "assistant" }). Silencieux tant que la mesure n'est pas prête.
	cortex.track = function (event, props) {
		try {
			if (window.posthog && window.posthog.__loaded) window.posthog.capture(event, props || {});
		} catch (e) {
			// La mesure ne doit jamais gêner le travail.
		}
	};

	function pageProps() {
		const route = (frappe.get_route && frappe.get_route()) || [];
		// Le type de page et le nom du DocType, jamais le nom de l'enregistrement (il peut contenir un client ou un montant).
		return { cortex_view: route[0] || "", cortex_target: route[0] === "Form" || route[0] === "List" ? route[1] || "" : "" };
	}

	function start() {
		const ph = window.posthog;
		if (!ph || ph.__loaded) return;
		ph.init(cfg.key, {
			api_host: cfg.host,
			person_profiles: "identified_only",
			bootstrap: { distinctID: cfg.distinct_id },
			autocapture: { capture_copied_text: false },
			capture_pageview: false, // Frappe est une application à page unique : on envoie la page à chaque changement de route
			capture_pageleave: true,
			capture_performance: true,
			capture_exceptions: true,
			respect_dnt: true,
			mask_all_text: false,
			mask_all_element_attributes: !cfg.capture_pii,
			session_recording: {
				maskAllInputs: !cfg.capture_pii,
				maskTextSelector: cfg.mask_text_selector || undefined,
			},
			loaded: function (instance) {
				instance.identify(cfg.distinct_id, cfg.person || {});
				if (cfg.group && cfg.group.company) instance.group("company", cfg.group.company);
				instance.register({ cortex_app: "cortex_rental", cortex_lang: frappe.boot.lang || "fr" });
				instance.capture("$pageview", pageProps());
				if (frappe.router && frappe.router.on) {
					frappe.router.on("change", function () {
						instance.capture("$pageview", pageProps());
					});
				}
			},
		});
	}

	const script = document.createElement("script");
	script.async = true;
	script.crossOrigin = "anonymous";
	// Les ressources de PostHog viennent d'un domaine « -assets » parallèle à l'hôte d'envoi (région américaine ou européenne).
	script.src = cfg.host.replace(".i.posthog.com", "-assets.i.posthog.com") + "/static/array.js";
	script.onload = start;
	document.head.appendChild(script);
})();
