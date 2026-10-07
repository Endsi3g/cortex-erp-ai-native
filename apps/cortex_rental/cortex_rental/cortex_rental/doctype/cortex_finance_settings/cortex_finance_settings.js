// Réglages financiers : modèles de taxes canadiens (le serveur valide, borne les taux et audite le changement).
frappe.ui.form.on("Cortex Finance Settings", {
	refresh(frm) {
		if (!frappe.model.can_write("Cortex Finance Settings")) return;
		// Conditions du contrat : le modèle de départ s'insère puis s'adapte librement.
		frm.add_custom_button(__("Insérer le modèle par défaut"), () => {
			const apply = () => cortex.call("billing.default_terms", {}, { type: "GET" }).then((r) => {
				const data = (r || {}).data || r || {};
				frm.set_value("contract_terms", data.text || "");
			});
			if (frm.doc.contract_terms) frappe.confirm(__("Remplacer les conditions actuelles par le modèle par défaut ?"), apply);
			else apply();
		}, __("Contrat"));
		if (frm.is_new()) return;
		frm.add_custom_button(__("Appliquer un modèle de taxes"), () => {
			cortex.call("billing.tax_presets", {}, { type: "GET" }).then((r) => {
				const data = (r || {}).data || r || {};
				const options = data.presets.map((p) => ({ value: p.key, label: __(p.label) }));
				frappe.prompt(
					[
						{ fieldtype: "Select", fieldname: "preset", label: __("Modèle"), options, default: data.matches === "custom" ? "qc" : data.matches, reqd: 1 },
						{ fieldtype: "HTML", fieldname: "note", options: `<p class="text-muted">${__(data.not_covered)} ${__("Confirmez les taux avec votre comptable.")}</p>` },
					],
					(values) => cortex.call("billing.apply_tax_preset", { preset: values.preset }, { type: "POST" }).then(() => frm.reload_doc()),
					__("Modèles de taxes"),
					__("Appliquer")
				);
			});
		}, __("Actions"));
	},
});
