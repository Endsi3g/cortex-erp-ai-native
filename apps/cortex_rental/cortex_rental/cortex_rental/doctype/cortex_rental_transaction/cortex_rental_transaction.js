// Formulaire natif d'une location : indicateur d'état, alertes de préparation, et les gestes du comptoir
// (réserver, demander le contrat, sortie par scan, retour). Toutes les règles et écritures restent côté serveur
// (cortex_rental.api.v1.*) ; ce script n'invente aucun état et ne contourne aucune approbation.

frappe.ui.form.on("Cortex Rental Transaction", {
	refresh(frm) {
		cortex_rental_transaction.set_indicator(frm);
		if (frm.is_new()) return;
		cortex_rental_transaction.show_readiness(frm);
		cortex_rental_transaction.add_actions(frm);
		cortex_rental_transaction.show_hold(frm);
		cortex_rental_transaction.show_shares(frm);
		cortex.dossier(frm);
	},
});

const cortex_rental_transaction = {
	set_indicator(frm) {
		const entry = cortex.RENTAL_STATES[frm.doc.rental_state];
		if (entry && !frm.is_new()) frm.page.set_indicator(entry[0], entry[1]);
	},

	show_readiness(frm) {
		const missing = [];
		if (!frm.doc.customer_account_ready) missing.push(__("compte client"));
		if (!frm.doc.insurance_ready) missing.push(__("assurance"));
		if (!frm.doc.payment_ready) missing.push(__("paiement ou dépôt"));
		if (missing.length && ["Quote", "Reservation"].includes(frm.doc.rental_state)) {
			frm.dashboard.add_comment(__("À confirmer avant le contrat : {0}.", [missing.join(", ")]), "orange", true);
		}
	},

	add_actions(frm) {
		if (frm.is_dirty()) return;
		const state = frm.doc.rental_state;
		const group = __("Actions");
		if (state === "Quote") {
			frm.add_custom_button(__("Partager avec le client"), () => this.share(frm), group);
			frm.add_custom_button(__("Réserver le matériel"), () => this.reserve(frm), group);
			frm.add_custom_button(__("Annuler le devis"), () => this.change_state(frm, "Cancelled"), group);
		} else if (state === "Reservation") {
			frm.add_custom_button(__("Demander le contrat"), () => this.request_contract(frm), group);
			frm.add_custom_button(__("Annuler la location"), () => this.change_state(frm, "Cancelled"), group);
		} else if (state === "Contract") {
			frm.add_custom_button(__("Sortie du matériel"), () => this.checkout(frm), group);
			frm.add_custom_button(__("Annuler la location"), () => this.change_state(frm, "Cancelled"), group);
		} else if (state === "Checked Out") {
			frm.add_custom_button(__("Retour du matériel"), () => this.checkin(frm), group);
			frm.add_custom_button(__("Ouvrir un litige"), () => this.change_state(frm, "Disputed"), group);
		} else if (state === "Returned") {
			frm.add_custom_button(__("Clôturer le dossier"), () => this.change_state(frm, "Closed"), group);
		} else if (state === "Disputed") {
			frm.add_custom_button(__("Clôturer le dossier"), () => this.change_state(frm, "Closed"), group);
			frm.add_custom_button(__("Annuler la location"), () => this.change_state(frm, "Cancelled"), group);
		}
		frm.page.set_inner_btn_group_as_primary(group);
	},

	// ---- Clôture, annulation, litige : la machine d'états reste côté serveur ----
	change_state(frm, to_state) {
		const texts = {
			Closed: [__("Clôturer le dossier"), __("La location sera close et la facture finale émise (moins l'acompte, avec les frais de retard s'il y a lieu)."), false],
			Cancelled: [__("Annuler"), __("Le matériel réservé est libéré. Une facture d'acompte non payée est annulée."), true],
			Disputed: [__("Ouvrir un litige"), __("Le dossier passe en litige : il reste ouvert jusqu'à sa clôture ou son annulation."), true],
		}[to_state];
		const run = (reason) =>
			cortex
				.call("rentals.change_state", { name: frm.doc.name, to_state, reason: reason || "", version: frm.doc.version }, { type: "POST" })
				.then((r) => {
					if (r && r.mutation_performed) frappe.show_alert({ message: __("Dossier mis à jour."), indicator: "green" });
					return frm.reload_doc();
				});
		if (texts[2]) {
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Motif (obligatoire)"), reqd: 1, description: texts[1] },
				(values) => run(values.reason),
				texts[0],
				texts[0]
			);
		} else {
			frappe.confirm(texts[1], () => run(""));
		}
	},

	// ---- Devis partagé : lien à copier ou courriel ; le client répond sur une page publique, sans compte ----
	share(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Partager le devis {0}", [frm.doc.name]),
			fields: [
				{
					fieldname: "channel",
					fieldtype: "Select",
					label: __("Comment l'envoyer ?"),
					options: [
						{ value: "Link", label: __("Lien à copier (partageable)") },
						{ value: "Email", label: __("Courriel au client") },
					],
					default: "Email",
				},
				{ fieldname: "recipient_email", fieldtype: "Data", options: "Email", label: __("Courriel"), depends_on: "eval:doc.channel=='Email'", mandatory_depends_on: "eval:doc.channel=='Email'" },
				{ fieldname: "recipient_name", fieldtype: "Data", label: __("Nom du destinataire"), depends_on: "eval:doc.channel=='Email'" },
				{ fieldname: "message", fieldtype: "Small Text", label: __("Message pour le client (facultatif)") },
				{ fieldname: "valid_days", fieldtype: "Int", label: __("Valide pendant (jours)"), default: 14 },
				{ fieldname: "result", fieldtype: "HTML" },
			],
			primary_action_label: __("Créer le lien"),
			primary_action: (values) => {
				cortex
					.call("quote_share.create_share", {
						rental_id: frm.doc.name,
						channel: values.channel,
						recipient_email: values.recipient_email || "",
						recipient_name: values.recipient_name || "",
						message: values.message || "",
						valid_days: values.valid_days || 14,
					})
					.then((r) => {
						if (!r) return;
						const url = frappe.utils.escape_html(r.url);
						const mail = r.channel === "Email" ? (r.email_sent ? __("Courriel envoyé.") : __("Le courriel n'a pas pu partir : copiez le lien et envoyez-le vous-même.")) : "";
						dialog.get_field("result").$wrapper.html(
							`<p class="text-muted">${mail} ${__("Ce lien n'est montré qu'une fois.")}</p><input class="form-control" readonly value="${url}" onclick="this.select()">`
						);
						dialog.set_primary_action(__("Copier le lien"), () => {
							frappe.utils.copy_to_clipboard(r.url);
							dialog.hide();
						});
						frm.reload_doc();
					});
			},
		});
		dialog.show();
	},

	// ---- Retenue du matériel : un devis retient les unités dans la disponibilité (services/holds.py) ----
	show_hold(frm) {
		if (frm.doc.rental_state !== "Quote") return;
		const group = __("Actions");
		const until = frm.doc.hold_until ? moment(frm.doc.hold_until) : null;
		const active = frm.doc.hold_status === "Active" && until && until.isAfter(moment());
		if (active) {
			frm.dashboard.add_comment(__("Matériel retenu dans la disponibilité jusqu'au {0}. La réservation reste la seule garantie.", [cortex.shortDateTime(frm.doc.hold_until)]), "green", true);
			frm.add_custom_button(__("Libérer la retenue"), () => this.hold_action(frm, "release_hold", __("Matériel libéré.")), group);
		} else if (frm.doc.hold_status === "Insufficient") {
			frm.dashboard.add_comment(frappe.utils.escape_html(frm.doc.hold_note || __("Disponibilité insuffisante : aucune retenue.")), "red", true);
			frm.add_custom_button(__("Reprendre la retenue"), () => this.hold_action(frm, "renew_hold", null), group);
		} else if (frm.doc.hold_status === "Released") {
			frm.dashboard.add_comment(__("Retenue libérée : le matériel n'est plus gardé pour ce devis."), "orange", true);
			frm.add_custom_button(__("Reprendre la retenue"), () => this.hold_action(frm, "renew_hold", null), group);
		} else if (frm.doc.hold_status === "Active") {
			frm.dashboard.add_comment(__("La retenue a expiré : le matériel n'est plus gardé pour ce devis."), "orange", true);
			frm.add_custom_button(__("Reprendre la retenue"), () => this.hold_action(frm, "renew_hold", null), group);
		}
	},

	hold_action(frm, method, done) {
		cortex.call(`rentals.${method}`, { name: frm.doc.name }, { type: "POST" }).then((r) => {
			if (method === "renew_hold") {
				const ok = r && r.status === "Active";
				frappe.show_alert({ message: ok ? __("Matériel retenu jusqu'au {0}.", [cortex.shortDateTime(r.until)]) : __("Disponibilité insuffisante : aucune retenue."), indicator: ok ? "green" : "red" }, 7);
			} else {
				frappe.show_alert({ message: done, indicator: "green" });
			}
			return frm.reload_doc();
		});
	},

	show_shares(frm) {
		if (!["Quote", "Reservation"].includes(frm.doc.rental_state)) return;
		cortex.call("quote_share.list_shares", { rental_id: frm.doc.name }, { type: "GET", freeze: false }).then((r) => {
			const shares = (r && r.shares) || [];
			const latest = shares[0];
			if (!latest) return;
			const names = { Active: __("En attente du client"), Accepted: __("Accepté par le client"), Declined: __("Refusé par le client"), "Changes Requested": __("Modification demandée"), Revoked: __("Révoqué"), Expired: __("Expiré") };
			const colors = { Active: "blue", Accepted: "green", Declined: "red", "Changes Requested": "orange", Revoked: "gray", Expired: "gray" };
			const note = latest.response_message ? ` — « ${frappe.utils.escape_html(latest.response_message)} »` : "";
			const who = latest.responder_name ? ` (${frappe.utils.escape_html(latest.responder_name)})` : "";
			const seen = latest.view_count ? __("vu {0} fois", [latest.view_count]) : __("pas encore ouvert");
			frm.dashboard.add_comment(`${__("Devis partagé")} : ${names[latest.effective_status] || latest.effective_status}${who}${note} · ${seen}`, colors[latest.effective_status] || "blue", true);
			if (latest.effective_status === "Accepted" && frm.doc.rental_state === "Quote") {
				frm.add_custom_button(__("Réserver maintenant"), () => this.reserve(frm), __("Actions"));
				if (latest.reservation_status === "Needs Review" && latest.reservation_note) {
					frm.dashboard.add_comment(frappe.utils.escape_html(latest.reservation_note), "orange", true);
				}
			}
			if (latest.effective_status === "Accepted" && latest.payment_status) {
				const pay = { Paid: __("acompte payé en ligne"), Pending: __("paiement de l'acompte en cours") }[latest.payment_status];
				if (pay) frm.dashboard.add_comment(__("Portail : {0}.", [pay]), latest.payment_status === "Paid" ? "green" : "blue", true);
			}
			if (latest.effective_status === "Active") {
				frm.add_custom_button(__("Révoquer le lien"), () => cortex.call("quote_share.revoke_share", { name: latest.name }).then(() => frm.reload_doc()), __("Actions"));
			}
		});
	},

	report(frm, message) {
		if (message && message.errors && message.errors.length) {
			frappe.msgprint({ title: __("Action non effectuée"), message: message.errors[0].message, indicator: "orange" });
		}
		return frm.reload_doc();
	},

	reserve(frm) {
		frappe.confirm(__("Réserver le matériel pour cette location ? La disponibilité est revérifiée par le serveur."), () => {
			cortex
				.call("rentals.request_reservation", { name: frm.doc.name, version: frm.doc.version })
				.then((r) => {
					if (r && r.mutation_performed) frappe.show_alert({ message: __("Matériel réservé."), indicator: "green" });
					return this.report(frm, r);
				});
		});
	},

	request_contract(frm) {
		frappe.confirm(
			__("Soumettre le contrat à l'approbation ? Une personne autorisée doit l'approuver avant la sortie."),
			() => {
				cortex
					.call("rentals.request_contract", { name: frm.doc.name, version: frm.doc.version })
					.then((r) => {
						if (r && r.approval_request_id) {
							frappe.show_alert(
								{
									message: __("Demande d'approbation {0} en attente.", [
										`<a href="/app/approval-request/${r.approval_request_id}">${r.approval_request_id}</a>`,
									]),
									indicator: "orange",
								},
								8
							);
						}
						return this.report(frm, r);
					});
			}
		);
	},

	// ---- Sortie : numéros de série alloués, balayés un à un (lecteur code-barres ou saisie) ----
	checkout(frm) {
		const parse = (text) => {
			try {
				return JSON.parse(text || "[]");
			} catch (e) {
				return [];
			}
		};
		const state = () =>
			(frm.doc.items || []).map((row) => ({
				item: row.item_name || row.item_code,
				assigned: parse(row.assigned_serials),
				scanned: parse(row.scanned_checkout_serials),
			}));
		const render = (dialog) => {
			const rows = state()
				.flatMap((line) =>
					line.assigned.map((serial) => {
						const done = line.scanned.includes(serial);
						return `<tr><td>${frappe.utils.escape_html(line.item)}</td><td>${frappe.utils.escape_html(serial)}</td>
							<td class="text-right"><span class="indicator-pill ${done ? "green" : "orange"}">${done ? __("Balayé") : __("À balayer")}</span></td></tr>`;
					})
				)
				.join("");
			dialog.get_field("progress").$wrapper.html(
				rows
					? `<table class="table table-sm"><tbody>${rows}</tbody></table>`
					: `<p class="text-muted">${__("Aucun numéro de série alloué à cette location.")}</p>`
			);
		};
		const dialog = new frappe.ui.Dialog({
			title: __("Sortie du matériel — {0}", [frm.doc.name]),
			fields: [
				{
					fieldname: "serial",
					fieldtype: "Data",
					options: "Barcode",
					label: __("Numéro de série (scanner ou saisir, puis Entrée)"),
				},
				{ fieldname: "progress", fieldtype: "HTML" },
			],
			primary_action_label: __("Terminer la sortie"),
			primary_action: () => {
				cortex.call("checkout.complete_checkout", { rental_id: frm.doc.name }).then(() => {
					dialog.hide();
					frappe.show_alert({ message: __("Sortie terminée."), indicator: "green" });
					frm.reload_doc();
				});
			},
		});
		const scan = () => {
			const serial = (dialog.get_value("serial") || "").trim();
			if (!serial) return;
			dialog.set_value("serial", "");
			cortex.call("checkout.record_checkout_scan", { rental_id: frm.doc.name, serial_number: serial }).then(() =>
				frm.reload_doc().then(() => render(dialog))
			);
		};
		dialog.show();
		dialog.get_field("serial").$input.on("keydown", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				scan();
			}
		});
		render(dialog);
	},

	// ---- Retour : état et destination de chaque ligne, puis enregistrement d'un Check-In audité ----
	checkin(frm) {
		const parse = (text) => {
			try {
				return JSON.parse(text || "[]");
			} catch (e) {
				return [];
			}
		};
		// Un article sérialisé se reçoit numéro par numéro (la destination s'applique à chaque unité).
		const lines = (frm.doc.items || [])
			.filter((row) => (row.returned_qty || 0) < (row.qty || 0))
			.flatMap((row) => {
				const base = { transaction_item: row.name, item_code: row.item_code, condition: "Good", disposition: "Return to Stock" };
				const serials = parse(row.assigned_serials);
				if (serials.length) {
					return serials.map((serial) => Object.assign({ serial_no: serial, expected_qty: 1, returned_qty: 1 }, base));
				}
				const remaining = (row.qty || 0) - (row.returned_qty || 0);
				return [Object.assign({ serial_no: row.serial_no || "", expected_qty: remaining, returned_qty: remaining }, base)];
			});
		if (!lines.length) {
			frappe.msgprint(__("Tout le matériel de cette location est déjà revenu."));
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Retour du matériel — {0}", [frm.doc.name]),
			size: "extra-large",
			fields: [
				{
					fieldname: "lines",
					fieldtype: "Table",
					label: __("Matériel à recevoir"),
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					data: lines,
					fields: [
						{ fieldname: "item_code", fieldtype: "Link", options: "Item", label: __("Article"), in_list_view: 1, read_only: 1, columns: 2 },
						{ fieldname: "serial_no", fieldtype: "Data", label: __("N° de série"), in_list_view: 1, read_only: 1, columns: 2 },
						{ fieldname: "returned_qty", fieldtype: "Float", label: __("Qté reçue"), in_list_view: 1, columns: 1 },
						{ fieldname: "condition", fieldtype: "Select", label: __("État"), options: "Good\nDamaged\nMissing", in_list_view: 1, columns: 2 },
						{ fieldname: "estimated_repair_cost", fieldtype: "Currency", label: __("Coût estimé ($)"), in_list_view: 1, columns: 1, description: __("Si abîmé") },
						{
							fieldname: "disposition",
							fieldtype: "Select",
							label: __("Destination"),
							options: "Return to Stock\nQuarantine\nRepair\nMissing\nWrite-off",
							in_list_view: 1,
							columns: 2,
						},
					],
				},
				{
					fieldname: "finalize_mode",
					fieldtype: "Select",
					label: __("Clôture"),
					options: [
						{ value: "auto", label: __("Automatique : le serveur décide selon les quantités reçues") },
						{ value: "partial", label: __("Retour partiel") },
						{ value: "full", label: __("Retour complet") },
						{ value: "settle_with_loss", label: __("Régler avec perte") },
					],
					default: "auto",
				},
				{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
			],
			primary_action_label: __("Enregistrer le retour"),
			primary_action: (values) => {
				const items = (values.lines || []).map((row) => ({
					transaction_item: row.transaction_item,
					item_code: row.item_code,
					serial_no: row.serial_no || null,
					expected_qty: row.expected_qty,
					returned_qty: row.returned_qty,
					condition: row.condition,
					disposition: row.disposition,
					estimated_repair_cost: row.condition === "Damaged" ? row.estimated_repair_cost || 0 : 0,
					damage_severity: row.condition === "Damaged" ? "Functional" : "None",
				}));
				cortex
					.call(
						"checkin.submit_checkin",
						{ transaction_id: frm.doc.name, items: JSON.stringify(items), finalize_mode: values.finalize_mode, notes: values.notes || "" },
						{ headers: { "Idempotency-Key": frappe.utils.get_random(24) } }
					)
					.then(() => {
						dialog.hide();
						frappe.show_alert({ message: __("Retour enregistré."), indicator: "green" });
						frm.reload_doc();
					});
			},
		});
		dialog.show();
	},
};
