"""Politique de connexion plus stricte : verrouillage après 5 échecs consécutifs, pendant 5 minutes.

On ne touche aux valeurs que si elles sont encore celles livrées par Frappe (10 échecs, 60 secondes) : un réglage
choisi par l'administrateur n'est jamais écrasé."""

import frappe


def execute():
    settings = frappe.get_doc("System Settings")
    if int(settings.allow_consecutive_login_attempts or 0) in (0, 10):
        settings.allow_consecutive_login_attempts = 5
    if int(settings.allow_login_after_fail or 0) in (0, 60):
        settings.allow_login_after_fail = 300
    settings.flags.ignore_permissions = True
    settings.save()
