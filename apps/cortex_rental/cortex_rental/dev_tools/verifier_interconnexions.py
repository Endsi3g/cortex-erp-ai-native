"""Vérification sur le banc des fonctions interconnectées (société de simulation) :
frais de dommages et de pertes, écritures comptables équilibrées, rapport d'utilisation, vue client 360°, outils IA.

    bench --site <site> execute cortex_rental.dev_tools.verifier_interconnexions.run
"""

import json
import random
from collections import defaultdict
from datetime import datetime, timedelta

import frappe

from cortex_rental.dev_tools import simulate_company as sim

OUT = "/tmp/cortex_interconnexions.json"


def _serialized_item():
    rows = frappe.get_all(
        "Cortex Rental Item Profile",
        filters={
            "company": sim.COMPANY,
            "is_serialized": 1,
            "replacement_value": [">", 0],
            "item_code": ["like", "SIM-%"],
        },
        fields=["item_code", "replacement_value", "daily_rate"],
        order_by="replacement_value asc",
        limit_page_length=20,
    )
    for row in rows:
        free = frappe.db.count(
            "Serial No", {"company": sim.COMPANY, "item_code": row.item_code, "cortex_status": "Active"}
        )
        if free >= 2:
            return row
    raise RuntimeError("Aucun équipement sérialisé libre en simulation : lancer la simulation d'abord.")


def run():
    frappe.set_user("Administrator")
    checks = {}
    settings = (
        frappe.get_doc("Cortex Finance Settings", {"company": sim.COMPANY})
        if frappe.db.exists("Cortex Finance Settings", {"company": sim.COMPANY})
        else None
    )
    if settings is None:
        raise RuntimeError("Réglages financiers de la simulation introuvables.")
    settings.damage_billing_enabled = 1
    settings.missing_billing_percent = 100
    settings.save(ignore_permissions=True)
    frappe.db.commit()

    item = _serialized_item()
    customer = frappe.get_all("Customer", filters={"cortex_company": sim.COMPANY}, pluck="name", limit_page_length=1)[0]
    rng = random.Random(7)
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=rng.randint(400, 900))
    end = start + timedelta(days=3)
    from cortex_rental.api.v1 import rentals

    sim.as_user(sim.COUNTERS[0])
    frappe.local.form_dict = frappe._dict(
        {
            "customer_id": customer,
            "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": end.strftime("%Y-%m-%d %H:%M:%S"),
            "project_name": "Vérification dommages",
            "items": [{"item_code": item.item_code, "quantity": 2}],
        }
    )
    name = rentals.create_quote_draft()["entity_id"]
    record = {"name": name, "counter": sim.COUNTERS[0], "start": start.date(), "end": end.date()}
    checks["devis_retient_le_materiel"] = frappe.db.get_value("Cortex Rental Transaction", name, "hold_status")

    schedule = defaultdict(list)
    sim.EVENTS.clear()
    sim.progress_rental(random.Random(3), record, datetime.now().date(), datetime.now().date(), {}, schedule)
    # progress_rental annule parfois : on force le chemin heureux si besoin
    state = frappe.db.get_value("Cortex Rental Transaction", name, "rental_state")
    checks["etat_apres_progression"] = state
    if state != "Contract":
        checks["verdict"] = "ECHEC : le dossier n'a pas atteint l'état Contrat"
        json.dump(checks, open(OUT, "w"), ensure_ascii=False, indent=1)
        print(json.dumps(checks, ensure_ascii=False, indent=1))
        return
    sim.do_checkout(name, record, random.Random(5), schedule)

    from cortex_rental.services.checkin import process_checkin

    sim.as_user(sim.COUNTERS[0])
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    row = doc.items[0]
    serials = frappe.parse_json(row.assigned_serials or "[]")
    items = []
    for serial, cond in zip(serials, ("Damaged", "Missing")):
        items.append(
            {
                "transaction_item": row.name,
                "item_code": row.item_code,
                "serial_no": serial,
                "expected_qty": 1,
                "returned_qty": 0 if cond == "Missing" else 1,
                "condition": cond,
                "disposition": "Repair" if cond == "Damaged" else "Missing",
                "damage_severity": "Functional" if cond == "Damaged" else "Blocking",
                "damage_type": "Physical / Impact" if cond == "Damaged" else "Missing Parts",
                "estimated_repair_cost": 250 if cond == "Damaged" else 0,
            }
        )
    process_checkin(sim.COMPANY, frappe.session.user, name, items, "auto", "Vérification")
    sim.as_user(sim.MANAGER)
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    checks["etat_apres_retour"] = doc.rental_state
    if doc.rental_state == "Returned":
        doc.transition_to("Closed", "Vérification")
    final = frappe.db.get_value(
        "Cortex Rental Invoice",
        {"rental_transaction": name, "invoice_type": "Final", "status": ["!=", "Cancelled"]},
        ["name", "total", "subtotal"],
        as_dict=True,
    )
    lines = (
        frappe.get_all(
            "Cortex Rental Invoice Line",
            filters={"parent": final.name} if final else {"name": "-"},
            fields=["description", "line_kind", "amount"],
        )
        if final
        else []
    )
    checks["facture_finale"] = final
    checks["lignes"] = lines
    damage = [l for l in lines if l.line_kind == "Damage"]
    expected_missing = round(item.replacement_value * 1 * 1.0, 2)
    checks["lignes_dommages"] = {
        "attendu": {"abime": 250.0, "perdu": expected_missing},
        "obtenu": sorted(round(l.amount, 2) for l in damage),
    }
    # écritures de la facture : débits = crédits, compte des dommages utilisé
    journals = (
        frappe.get_all(
            "Cortex Journal Entry",
            filters={"company": sim.COMPANY, "source_doctype": "Cortex Rental Invoice", "source_name": final.name},
            pluck="name",
        )
        if final
        else []
    )
    entries = (
        frappe.get_all(
            "Cortex Journal Entry Line",
            filters={"parent": ["in", journals]},
            fields=["account_name", "debit", "credit"],
        )
        if journals
        else []
    )
    checks["ecritures"] = {
        "ecritures": len(journals),
        "debit": round(sum(e.debit for e in entries), 2),
        "credit": round(sum(e.credit for e in entries), 2),
        "compte_dommages": [e.account_name for e in entries if "Dommages" in (e.account_name or "")],
    }

    # rapport d'utilisation
    from cortex_rental.cortex_rental.report.utilisation_du_parc.utilisation_du_parc import execute

    sim.as_user(sim.MANAGER)
    columns, data, _, chart = execute({"company": sim.COMPANY})
    checks["rapport"] = {"colonnes": len(columns), "lignes": len(data), "premiere": data[0] if data else None}

    # vue client 360° et outils IA
    from cortex_rental.permissions.agent_scopes import get_company_context
    from cortex_rental.services import customer_360
    from cortex_rental.services.ai import tools

    summary = customer_360.summary(customer, sim.COMPANY)
    checks["client_360"] = {k: summary.get(k) for k in ("rentals_count", "late_returns", "billing")}
    try:
        checks["outil_retards"] = tools.execute("late_returns", {"limit": 3})
        checks["outil_client"] = {
            k: v
            for k, v in tools.execute("customer_summary", {"customer": customer}).items()
            if k in ("rentals_count", "billing", "error")
        }
        checks["contexte_societe"] = get_company_context()
    except Exception as exc:  # noqa: BLE001
        checks["outil_erreur"] = str(exc)[:200]
    ok = (
        checks["lignes_dommages"]["obtenu"] == sorted([250.0, expected_missing])
        and checks["ecritures"]["debit"] == checks["ecritures"]["credit"]
        and bool(checks["ecritures"]["compte_dommages"])
    )
    checks["verdict"] = "OK" if ok else "A VERIFIER"
    frappe.db.commit()
    json.dump(checks, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(checks, ensure_ascii=False, indent=1, default=str))


def demo_retenues():
    """Crée quelques devis de la semaine prochaine (société de simulation) pour voir les retenues dans la grille."""
    from cortex_rental.api.v1 import rentals

    customers = frappe.get_all("Customer", filters={"cortex_company": sim.COMPANY}, pluck="name", limit_page_length=3)
    items = ["SIM-AUD-SND", "SIM-AUD-SEN", "SIM-AUD-ZXN"]
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    made = []
    for index, (customer, code) in enumerate(zip(customers, items)):
        start = base + timedelta(days=2 + index * 2)
        sim.as_user(sim.COUNTERS[0])
        frappe.local.form_dict = frappe._dict(
            {
                "customer_id": customer,
                "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
                "ends_at": (start + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "project_name": "Démonstration retenue",
                "items": [{"item_code": code, "quantity": 2}],
            }
        )
        name = rentals.create_quote_draft()["entity_id"]
        made.append((name, frappe.db.get_value("Cortex Rental Transaction", name, "hold_status")))
    frappe.db.commit()
    print(made)
