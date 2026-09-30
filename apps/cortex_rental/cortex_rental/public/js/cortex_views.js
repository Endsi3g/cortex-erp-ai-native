// Constructions natives Cortex pour le Desk : libellés d'état français, couleurs d'indicateurs et appels d'API.
// Chargé sur toutes les pages Desk (hooks.py → app_include_js) ; les fichiers `*_list.js`, `*.js` et `*_calendar.js`
// des DocTypes s'en servent. Aucun état n'est inventé : les valeurs viennent toujours du serveur.
frappe.provide("cortex");

cortex.RENTAL_STATES = {
	Quote: [__("Devis"), "gray"],
	Reservation: [__("Réservation"), "blue"],
	Contract: [__("Contrat"), "purple"],
	"Checked Out": [__("Sorti"), "orange"],
	Returned: [__("Retourné"), "green"],
	Closed: [__("Clos"), "green"],
	Cancelled: [__("Annulé"), "red"],
	Disputed: [__("Litige"), "red"],
	Quarantine: [__("Quarantaine"), "yellow"],
};

cortex.APPROVAL_STATES = {
	Pending: [__("En attente"), "orange"],
	Approved: [__("Approuvée"), "green"],
	Rejected: [__("Refusée"), "red"],
	Expired: [__("Expirée"), "gray"],
};

// Retourne le tuple attendu par `listview_settings.get_indicator` : [libellé, couleur, filtre].
cortex.indicator = function (map, field) {
	return function (doc) {
		const entry = map[doc[field]];
		if (!entry) return [doc[field], "gray", `${field},=,${doc[field]}`];
		return [entry[0], entry[1], `${field},=,${doc[field]}`];
	};
};

// Appel d'une API `cortex_rental.api.v1.*`. Les erreurs du serveur s'affichent dans la fenêtre Frappe habituelle.
cortex.call = function (method, args, opts) {
	return frappe
		.call(Object.assign({ method: `cortex_rental.api.v1.${method}`, args }, opts || {}))
		.then((r) => r.message);
};
