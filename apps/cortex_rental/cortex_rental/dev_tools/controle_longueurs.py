"""Cherche les colonnes texte qui contiennent des valeurs démesurées (> 5 000 caractères) : signe d'un champ sans limite.

    bench --site cortex.local execute cortex_rental.dev_tools.controle_longueurs.run

Lecture seule. À lancer après le fuzz (`fuzz_endpoints`), qui envoie des textes de 100 000 caractères à chaque endpoint.
"""

import frappe

SEUIL = 5000


def run():
    tables = frappe.db.sql(
        "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() "
        "AND (table_name LIKE 'tabCortex%%' OR table_name IN ('tabCustomer','tabApproval Request','tabAudit Event',"
        "'tabUser','tabAddress','tabNotification Log','tabComment','tabRental Pricing Rule'))",
        as_list=True,
    )
    trouves = []
    for (table,) in tables:
        colonnes = frappe.db.sql(
            "SELECT column_name FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s "
            "AND data_type IN ('varchar','text','longtext','mediumtext')",
            (table,),
            as_list=True,
        )
        for (colonne,) in colonnes:
            maximum = frappe.db.sql(f"SELECT MAX(CHAR_LENGTH(`{colonne}`)) FROM `{table}`")[0][0] or 0
            if maximum > SEUIL:
                trouves.append((table, colonne, int(maximum)))
    for ligne in sorted(trouves, key=lambda x: -x[2]):
        print(ligne)
    print(f"{len(trouves)} colonne(s) au-delà de {SEUIL} caractères")
    return len(trouves)
