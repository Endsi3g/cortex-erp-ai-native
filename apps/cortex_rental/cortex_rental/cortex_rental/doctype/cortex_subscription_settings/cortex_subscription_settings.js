// Réglages d'abonnement : valeurs de départ modifiables (rien n'est facturé tant que les prix ne sont pas confirmés).
frappe.ui.form.on("Cortex Subscription Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Remplir avec les valeurs par défaut"), () => {
			frappe.confirm(__("Remplacer les valeurs actuelles par les valeurs de départ ? Rien n'est enregistré avant « Enregistrer »."), () => {
				frappe.call({ method: "cortex_rental.api.v1.subscriptions.default_settings", type: "GET" }).then((r) => {
					const d = ((r && r.message) || {}).data || {};
					const rows = d.plan_items || [];
					delete d.plan_items;
					Object.keys(d).forEach((k) => frm.set_value(k, d[k]));
					frm.clear_table("plan_items");
					rows.forEach((row) => Object.assign(frm.add_child("plan_items"), row));
					frm.refresh_field("plan_items");
					frappe.show_alert({ message: __("Valeurs de départ chargées : vérifiez, confirmez les prix, puis enregistrez."), indicator: "green" }, 7);
				});
			});
		});
	},
});
