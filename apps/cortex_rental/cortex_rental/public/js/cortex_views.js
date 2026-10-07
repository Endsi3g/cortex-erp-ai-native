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

// Une action sur une fiche passe le tenant de la fiche; le serveur valide toujours ce choix
// contre les sociétés autorisées à la personne (permissions/agent_scopes.py).
cortex.call_for_company = function (method, args, company, opts) {
	const options = Object.assign({}, opts || {});
	options.headers = Object.assign({}, options.headers || {});
	if (company) options.headers["X-Company-ID"] = company;
	return cortex.call(method, args, options);
};

// Date et heure courtes (« 24 sept., 09:00 ») pour que les colonnes des listes ne soient plus tronquées.
cortex.shortDateTime = function (value) {
	if (!value) return "";
	const m = moment(frappe.datetime.convert_to_user_tz ? frappe.datetime.convert_to_user_tz(value) : value);
	if (!m.isValid()) return value;
	// Intl donne les mois en français (« 3 août ») sans dépendre des locales de moment.
	return new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false }).format(m.toDate()).replace(" à ", ", ");
};

// Renomme le bouton principal d'une liste (« Ajouter Location » devient « Nouvelle location »).
cortex.renamePrimary = function (listview, label) {
	const apply = () => $(listview.page.btn_primary).find("span").first().text(label);
	apply();
	window.setTimeout(apply, 250);
};

cortex.INVOICE_STATES = {
	Issued: [__("Émise"), "blue"],
	"Partially Paid": [__("Partiellement payée"), "orange"],
	Paid: [__("Payée"), "green"],
	Cancelled: [__("Annulée"), "gray"],
};
cortex.SUPPORT_STATES = {
	Open: [__("Ouverte"), "orange"],
	"In Progress": [__("En cours"), "blue"],
	Resolved: [__("Résolue"), "green"],
};
