"""Vérifie la demande et la décision d'approbation pour chaque rôle de la société de simulation.

bench --site <site> execute cortex_rental.dev_tools.verifier_approbations.run
"""

import json
import random
import traceback
from datetime import datetime, timedelta

import frappe

from cortex_rental.dev_tools import simulate_company as sim

USERS = [sim.PROPRIO, sim.OWNER, sim.MANAGER, *sim.COUNTERS]


def _quote(user, rng):
    from cortex_rental.api.v1 import rentals

    customer = frappe.get_all("Customer", filters={"cortex_company": sim.COMPANY}, pluck="name", limit_page_length=1)[0]
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=rng.randint(1000, 2500))
    sim.as_user(user)
    frappe.local.form_dict = frappe._dict(
        {
            "customer_id": customer,
            "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (start + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "project_name": "Vérification approbations",
            "items": [{"item_code": "SIM-LGT-FRS", "quantity": 1}],
        }
    )
    return rentals.create_quote_draft()["entity_id"]


def run():
    from cortex_rental.api.v1 import approval_queue, rentals

    rng = random.Random(11)
    report = {}
    for requester in USERS:
        row = {}
        try:
            name = _quote(requester, rng)
            doc = frappe.get_doc("Cortex Rental Transaction", name)
            sim.as_user(requester)
            doc.transition_to("Reservation", "Vérification")
            frappe.db.set_value(
                "Cortex Rental Transaction",
                name,
                {"customer_account_ready": 1, "insurance_ready": 1, "payment_ready": 1},
                update_modified=False,
            )
            sim.as_user(requester)
            version = frappe.db.get_value("Cortex Rental Transaction", name, "version")
            result = rentals.request_contract(name=name, version=version)
            row["demande"] = result.get("status")
            approval = result.get("approval_request_id")
            row["decisions"] = {}
            for approver in USERS:
                if approver == requester:
                    sim.as_user(approver)
                    try:
                        approval_queue.decide_approval(name=approval, decision="reject", reason="essai auto-décision")
                        row["decisions"][approver] = "ACCEPTÉE (ne devrait pas)"
                    except Exception as exc:  # noqa: BLE001
                        row["decisions"][approver] = f"refusée : {str(exc)[:90]}"
                    continue
                sim.as_user(approver)
                try:
                    approval_queue.decide_approval(name=approval, decision="reject", reason="essai de refus")
                    row["decisions"][approver] = "refus enregistré"
                    break
                except Exception as exc:  # noqa: BLE001
                    row["decisions"][approver] = f"impossible : {str(exc)[:90]}"
        except Exception as exc:  # noqa: BLE001
            row["erreur"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            row["trace"] = traceback.format_exc()[-400:]
        report[requester] = row
    frappe.db.commit()
    print(json.dumps(report, ensure_ascii=False, indent=1))


SOLO = "Société Solo (essai)"
SOLO_USER = "solo.proprio@cortex.test"
SECOND_USER = "solo.gestionnaire@cortex.test"


def solo():
    """Société d'une seule personne : le propriétaire peut-il décider de sa propre demande ? Et plus dès qu'une
    autre personne autorisée arrive ?"""
    from frappe.utils.password import update_password

    from cortex_rental.api.v1 import approval_queue
    from cortex_rental.services import tenant_provisioning as tp

    out = {}
    frappe.set_user("Administrator")
    if not frappe.db.exists("Company", SOLO):
        tp.create_company(SOLO)
    if not frappe.db.exists("User", SOLO_USER):
        tp.create_user(SOLO_USER, "Sophie Solo", SOLO, sim.OWNER_ROLES)
    update_password(SOLO_USER, sim.PASSWORD)
    from cortex_rental.services import billing

    billing.ensure_settings(SOLO)
    if frappe.db.exists("User", SECOND_USER):
        frappe.db.set_value("User", SECOND_USER, "enabled", 0)

    def new_request(requester):
        frappe.set_user("Administrator")
        doc = frappe.get_doc(
            {
                "doctype": "Approval Request",
                "company": SOLO,
                "action": "rental.essai.sans_effet",
                "entity_type": "Customer",
                "entity_id": "essai",
                "status": "Pending",
                "requested_by_type": "Human",
                "requested_by_id": requester,
                "decision_reason": "Essai",
            }
        ).insert(ignore_permissions=True)
        return doc.name

    def decide(user, name, decision, reason=""):
        sim.as_user(user)
        try:
            approval_queue.decide_approval(name=name, decision=decision, reason=reason)
            return "OK"
        except Exception as exc:  # noqa: BLE001
            return f"refusé : {str(exc)[:110]}"

    def options(user, name):
        sim.as_user(user)
        return approval_queue.decision_options(name)

    # Par défaut l'auto-approbation est désactivée : le propriétaire seul ne peut pas décider de sa demande.
    frappe.db.set_value("Cortex Finance Settings", {"company": SOLO}, "allow_sole_approver_self_approval", 0)
    off = new_request(SOLO_USER)
    out["seul_desactive_options"] = options(SOLO_USER, off)
    out["seul_desactive_approuve"] = decide(SOLO_USER, off, "approve", "essai")
    decide(SOLO_USER, off, "withdraw", "retrait de l'essai")
    # Le propriétaire l'active lui-même, après avoir confirmé la lecture des risques.
    sim.as_user(SOLO_USER)
    try:
        approval_queue.set_self_approval(enabled=1, acknowledged=0)
        out["activation_sans_confirmation"] = "ACCEPTÉE (ne devrait pas)"
    except Exception as exc:  # noqa: BLE001
        out["activation_sans_confirmation"] = f"refusée : {str(exc)[:80]}"
    approval_queue.set_self_approval(enabled=1, acknowledged=1)
    a = new_request(SOLO_USER)
    out["seul_options"] = options(SOLO_USER, a)
    out["seul_approuve_sa_demande"] = decide(SOLO_USER, a, "approve", "Je suis seul")
    audit = frappe.get_all(
        "Audit Event",
        filters={"entity_id": "essai", "action": "rental.approval.approved"},
        fields=["after_state"],
        limit=1,
        order_by="creation desc",
    )
    out["audit_auto_approbation"] = bool(audit and "self_approved" in (audit[0].after_state or ""))

    frappe.set_user("Administrator")
    if not frappe.db.exists("User", SECOND_USER):
        tp.create_user(SECOND_USER, "Gaëtan Gestionnaire", SOLO, tp.ROLE_PRESETS["manager"]["roles"])
    frappe.db.set_value("User", SECOND_USER, "enabled", 1)
    update_password(SECOND_USER, sim.PASSWORD)
    b = new_request(SOLO_USER)
    out["deux_personnes_options"] = options(SOLO_USER, b)
    out["deux_personnes_auto_approbation"] = decide(SOLO_USER, b, "approve")
    out["deux_personnes_auto_refus"] = decide(SOLO_USER, b, "reject", "non")
    out["deux_personnes_retrait"] = decide(SOLO_USER, b, "withdraw", "Erreur de ma part")
    c = new_request(SOLO_USER)
    out["autre_personne_approuve"] = decide(SECOND_USER, c, "approve", "Ok")
    d = new_request(SECOND_USER)
    out["propriétaire_approuve_celle_de_lautre"] = decide(SOLO_USER, d, "approve")
    out["autre_ne_peut_pas_retirer_celle_de_lautre"] = decide(SECOND_USER, new_request(SOLO_USER), "withdraw")
    # désactiver un membre ferme ses sessions
    frappe.db.commit()
    print(json.dumps(out, ensure_ascii=False, indent=1))


def solo_prepare():
    """État de départ pour les captures : propriétaire seul, règle désactivée, une demande en attente."""
    frappe.set_user("Administrator")
    if frappe.db.exists("User", SECOND_USER):
        frappe.db.set_value("User", SECOND_USER, "enabled", 0)
    frappe.db.set_value("Cortex Finance Settings", {"company": SOLO}, "allow_sole_approver_self_approval", 0)
    customer = frappe.get_all("Customer", filters={"cortex_company": SOLO}, pluck="name", limit_page_length=1)
    if not customer:
        customer = [
            frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Client essai",
                    "customer_type": "Company",
                    "cortex_company": SOLO,
                }
            )
            .insert(ignore_permissions=True)
            .name
        ]
    doc = frappe.get_doc(
        {
            "doctype": "Approval Request",
            "company": SOLO,
            "action": "rental.transaction.transition_to_contract",
            "entity_type": "Customer",
            "entity_id": customer[0],
            "status": "Pending",
            "requested_by_type": "Human",
            "requested_by_id": SOLO_USER,
            "decision_reason": "Contrat soumis à l'approbation humaine",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    print(doc.name)
