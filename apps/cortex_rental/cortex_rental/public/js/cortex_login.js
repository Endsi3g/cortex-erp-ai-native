// Cortex login behaviour, loaded after Frappe's login.js (templates/includes/login/login.js).
//
// Adds, without replacing Frappe's login/2FA/social code paths:
//  - inline messages and a busy state on the primary button (instead of writing errors in the button)
//  - the two-step access request (public/api: cortex_rental.api.v1.access.request_access)
//  - the forgot-password flow with an in-page confirmation and a resend cooldown
// French copy on purpose: the whole page is served in French (see www/login.py).
(function () {
	"use strict";
	if (!window.jQuery || !window.login || !window.frappe) return;
	var $ = window.jQuery;

	var COOLDOWN_SECONDS = 60;
	var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
	var FREE_DOMAINS = ["gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "yahoo.ca", "icloud.com", "proton.me", "protonmail.com"];

	// ---- messages and busy state -------------------------------------------------------------
	function alertFor(node) {
		return $(node).closest("section, .login-content").find("[data-cx-alert]").first();
	}

	function showAlert(node, message, kind) {
		var $box = alertFor(node);
		$box.removeClass("cx-alert--error cx-alert--success cx-alert--info").addClass("cx-alert--" + (kind || "error")).text(message).prop("hidden", false);
	}

	function clearAlert(node) {
		alertFor(node).prop("hidden", true).text("");
	}

	function fieldError(id, message) {
		var $input = $("#" + id);
		var $note = $('[data-cx-error-for="' + id + '"]');
		if (message) {
			$input.attr("aria-invalid", "true").attr("aria-describedby", ($input.attr("aria-describedby") || "").replace(/\s?err_\w+/g, "") + " err_" + id);
			$note.attr("id", "err_" + id).text(message).prop("hidden", false);
		} else {
			$input.removeAttr("aria-invalid");
			$note.prop("hidden", true).text("");
		}
	}

	function setBusy($button, busy) {
		if (!$button.length) return;
		if (busy) {
			$button.data("cx-label", $button.data("cx-label") || $button.text());
			$button.prop("disabled", true).attr("aria-busy", "true").addClass("is-busy");
		} else {
			$button.prop("disabled", false).removeAttr("aria-busy").removeClass("is-busy");
			if ($button.data("cx-label")) $button.text($button.data("cx-label"));
		}
	}

	function primaryButton() {
		return $("section:visible .btn-primary:visible").first();
	}

	// Frappe writes status text into the button ("Verifying...", errors): route it to our regions.
	login.set_status = function (message, color) {
		var $button = primaryButton();
		if (color === "red") {
			setBusy($button, false);
			showAlert($button, message, "error");
		} else if (color === "green") {
			setBusy($button, false);
			showAlert($button, message, "success");
		} else {
			clearAlert($button);
			setBusy($button, true);
		}
	};

	login.set_invalid = function (message) {
		$(".login-content.page-card").addClass("invalid-login");
		setTimeout(function () {
			$(".login-content.page-card").removeClass("invalid-login");
		}, 500);
		login.set_status(message, "red");
		$("#login_password").trigger("focus").trigger("select");
	};

	// ---- countdown for resend buttons --------------------------------------------------------
	function startCooldown($button, label) {
		var remaining = COOLDOWN_SECONDS;
		$button.prop("disabled", true);
		var timer = setInterval(function () {
			remaining -= 1;
			if (remaining <= 0) {
				clearInterval(timer);
				$button.prop("disabled", false).text(label);
			} else {
				$button.text(label + " (" + remaining + " s)");
			}
		}, 1000);
		$button.text(label + " (" + remaining + " s)");
	}

	// Plain fetch instead of frappe.call: Frappe pops its own dialogs on errors (rate limit, 500),
	// and these forms must answer inline and keep what the visitor typed.
	function callServer(method, args) {
		var deferred = $.Deferred();
		fetch("/api/method/" + method, {
			method: "POST",
			credentials: "same-origin",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
				"X-Frappe-CSRF-Token": window.csrf_token || frappe.csrf_token || "",
			},
			body: new URLSearchParams(args || {}).toString(),
		})
			.then(function (response) {
				if (!response.ok) {
					deferred.reject(response.status);
					return null;
				}
				return response.json().then(function (json) {
					deferred.resolve(json && json.message);
				});
			})
			.catch(function () {
				deferred.reject(0);
			});
		return deferred.promise();
	}

	function failureMessage(status) {
		if (status === 429) return "Trop de tentatives. Patientez quelques minutes avant de réessayer.";
		return "La connexion au serveur a échoué. Vos informations sont conservées : réessayez dans un instant.";
	}

	// ---- forgot password ---------------------------------------------------------------------
	function bindForgot() {
		var $form = $(".form-forgot");
		var $sent = $('[data-cx-sent="forgot"]');
		var lastEmail = "";

		function send(email, $button, label) {
			setBusy($button, true);
			clearAlert($button);
			return callServer("frappe.core.doctype.user.user.reset_password", { user: email })
				.done(function () {
					lastEmail = email;
					$form.prop("hidden", true).addClass("hide");
					$(".for-forgot .cx-lead").prop("hidden", true);
					$sent.find("[data-cx-sent-email]").text(email);
					$sent.prop("hidden", false).trigger("focus");
					startCooldown($sent.find("[data-cx-resend]"), "Renvoyer le lien");
				})
				.fail(function (status) {
					showAlert($button, failureMessage(status), "error");
				})
				.always(function () {
					setBusy($button, false);
				});
		}

		$form.off("submit").on("submit", function (event) {
			event.preventDefault();
			var email = ($("#forgot_email").val() || "").trim();
			fieldError("forgot_email", "");
			if (!EMAIL_RE.test(email)) {
				fieldError("forgot_email", "Saisissez une adresse courriel valide, par exemple nom@entreprise.com.");
				$("#forgot_email").trigger("focus");
				return false;
			}
			send(email, $form.find(".btn-primary"), "Réinitialiser le mot de passe");
			return false;
		});

		$sent.find("[data-cx-resend]").on("click", function () {
			var $button = $(this);
			$button.prop("disabled", true);
			callServer("frappe.core.doctype.user.user.reset_password", { user: lastEmail }).done(function () {
				showAlert($sent, "Lien renvoyé à " + lastEmail + ".", "success");
				startCooldown($button, "Renvoyer le lien");
			}).fail(function (status) {
				$button.prop("disabled", false);
				showAlert($sent, failureMessage(status), "error");
			});
		});

		$sent.find("[data-cx-edit]").on("click", function () {
			$sent.prop("hidden", true);
			$form.prop("hidden", false).removeClass("hide");
			$(".for-forgot .cx-lead").prop("hidden", false);
			clearAlert($sent);
			$("#forgot_email").trigger("focus");
		});
	}

	// ---- access request (two steps) ----------------------------------------------------------
	function bindSignup() {
		var $form = $("[data-cx-signup]");
		if (!$form.length) return;
		var $sent = $('[data-cx-sent="signup"]');
		var payload = null;

		function goTo(step) {
			$form.find("[data-cx-step]").prop("hidden", true);
			$form.find('[data-cx-step="' + step + '"]').prop("hidden", false);
			$form.find("[data-cx-progress]").removeClass("is-current is-done").removeAttr("aria-current").each(function () {
				var n = Number($(this).data("cx-progress"));
				if (n < step) $(this).addClass("is-done");
				if (n === step) $(this).addClass("is-current").attr("aria-current", "step");
			});
			clearAlert($form);
			$form.find('[data-cx-step="' + step + '"] input:visible').first().trigger("focus");
		}

		function validateStep1() {
			var ok = true;
			var name = ($("#signup_fullname").val() || "").trim();
			var email = ($("#signup_email").val() || "").trim().toLowerCase();
			fieldError("signup_fullname", "");
			fieldError("signup_email", "");
			if (!name) {
				fieldError("signup_fullname", "Indiquez votre nom complet.");
				ok = false;
			}
			if (!EMAIL_RE.test(email)) {
				fieldError("signup_email", "Saisissez une adresse courriel valide, par exemple camille@entreprise.com.");
				ok = false;
			} else if (FREE_DOMAINS.indexOf(email.split("@")[1]) !== -1) {
				fieldError("signup_email", "Utilisez votre courriel professionnel : les adresses personnelles ne sont pas acceptées.");
				ok = false;
			}
			if (!ok) $form.find('[aria-invalid="true"]').first().trigger("focus");
			return ok;
		}

		function validateStep2() {
			var ok = true;
			fieldError("signup_company", "");
			fieldError("signup_terms", "");
			if (!($("#signup_company").val() || "").trim()) {
				fieldError("signup_company", "Indiquez le nom de l'entreprise.");
				ok = false;
			}
			if (!$("#signup_terms").is(":checked")) {
				fieldError("signup_terms", "Acceptez les conditions pour envoyer la demande.");
				ok = false;
			}
			if (!ok) $form.find('[aria-invalid="true"]').first().trigger("focus");
			return ok;
		}

		function collect() {
			return {
				full_name: ($("#signup_fullname").val() || "").trim(),
				email: ($("#signup_email").val() || "").trim().toLowerCase(),
				company_name: ($("#signup_company").val() || "").trim(),
				job_title: ($("#signup_title").val() || "").trim(),
				team_size: $('input[name="signup_team"]:checked').val() || "",
				accept_terms: $("#signup_terms").is(":checked") ? 1 : 0,
				website: $("#signup_website").val() || "",
			};
		}

		function showSent(email) {
			$form.prop("hidden", true).addClass("hide");
			$sent.find("[data-cx-sent-email]").text(email);
			$sent.prop("hidden", false).trigger("focus");
			startCooldown($sent.find("[data-cx-resend]"), "Renvoyer le lien");
		}

		function place(code, message) {
			var map = { invalid_email: ["signup_email", 1], free_email: ["signup_email", 1], domain_not_allowed: ["signup_email", 1], terms: ["signup_terms", 2] };
			var target = map[code];
			if (target) {
				goTo(target[1]);
				fieldError(target[0], message);
				$("#" + target[0]).trigger("focus");
			} else {
				showAlert($form, message, "error");
			}
		}

		$form.find("[data-cx-next]").on("click", function () {
			if (validateStep1()) goTo(2);
		});
		$form.find("[data-cx-back]").on("click", function () {
			goTo(1);
		});

		$form.off("submit").on("submit", function (event) {
			event.preventDefault();
			if ($form.find('[data-cx-step="1"]').is(":visible")) {
				if (validateStep1()) goTo(2);
				return false;
			}
			if (!validateStep1()) return goTo(1), false;
			if (!validateStep2()) return false;
			payload = collect();
			var $button = $form.find("[data-cx-submit]");
			setBusy($button, true);
			clearAlert($form);
			callServer("cortex_rental.api.v1.access.request_access", payload)
				.done(function (result) {
					if (result && result.ok) showSent(payload.email);
					else place(result && result.code, (result && result.message) || "La demande n'a pas pu être envoyée.");
				})
				.fail(function (status) {
					showAlert($form, failureMessage(status), "error");
				})
				.always(function () {
					setBusy($button, false);
				});
			return false;
		});

		$sent.find("[data-cx-resend]").on("click", function () {
			var $button = $(this);
			$button.prop("disabled", true);
			callServer("cortex_rental.api.v1.access.request_access", payload).done(function () {
				showAlert($sent, "Lien renvoyé à " + payload.email + ".", "success");
				startCooldown($button, "Renvoyer le lien");
			}).fail(function (status) {
				$button.prop("disabled", false);
				showAlert($sent, failureMessage(status), "error");
			});
		});

		$sent.find("[data-cx-edit]").on("click", function () {
			$sent.prop("hidden", true);
			$form.prop("hidden", false).removeClass("hide");
			goTo(1);
		});
	}

	frappe.ready(function () {
		bindForgot();
		bindSignup();
		// Password visibility toggle: keep Frappe's behaviour, expose state to assistive tech.
		$(".toggle-password").attr("aria-pressed", "false").on("click", function () {
			$(this).attr("aria-pressed", $(this).attr("aria-pressed") === "true" ? "false" : "true");
		});
		$(document).trigger("cortex_login_ready");
	});
})();
