"""Jeu de données de démonstration pour tester l'assistant et les écrans de bout en bout.

    bench --site <site> execute cortex_rental.dev_tools.jeu_de_demo.run

Ce qu'il fait, dans la société de simulation seulement :
- retire les articles de test (« SIM-STRESS-… ») laissés par le test de charge dans le catalogue ;
- crée quelques devis de démonstration (clients et équipes différents) ;
- passe deux d'entre eux en réservation ;
- crée trois demandes d'approbation en attente, faites par trois personnes différentes ;
- n'invente aucune décision : rien n'est approuvé ni refusé.

Pour repartir de zéro : `…jeu_de_demo.reinitialiser`. Sûr à relancer : les devis de démonstration portent un nom de projet « Démo · … » et ne sont créés qu'une fois.
Refuse de s'exécuter hors d'un site de développement (`developer_mode`) ou sans `cortex_allow_demo_seed` dans la
configuration du site : ces données n'ont pas leur place en production.
"""

from datetime import datetime, timedelta

import frappe

from cortex_rental.dev_tools import simulate_company as sim

PREFIX = "Démo · "

# (projet, client, début dans N jours, durée en jours, équipement, qui fait la demande, étape)
PLAN = [
    ("Tournage publicitaire", 0, 9, 2, [("SIM-CAM-ALX", 1), ("SIM-AUD-BOM", 1)], sim.COUNTERS[0], "approval"),
    ("Série web, jour 3", 1, 12, 3, [("SIM-AUD-ZXN", 2)], sim.COUNTERS[1], "approval"),
    ("Clip musical", 2, 15, 1, [("SIM-LGT-FRS", 2)], sim.MANAGER, "approval"),
    ("Corporatif Mile-End", 3, 18, 2, [("SIM-AUD-SEN", 2)], sim.COUNTERS[0], "reservation"),
    ("Reportage Gaspé", 4, 21, 4, [("SIM-AUD-BOM", 1)], sim.COUNTERS[1], "reservation"),
    ("Soumission en cours", 5, 25, 2, [("SIM-CAM-ALX", 1)], sim.COUNTERS[0], "quote"),
]


def _guard() -> None:
    conf = frappe.conf
    if not (conf.get("developer_mode") or conf.get("cortex_allow_demo_seed")):
        raise frappe.PermissionError(
            "Jeu de démonstration refusé : ce site n'est pas un site de développement "
            "(activez `developer_mode` ou `cortex_allow_demo_seed` seulement sur un site de test)."
        )
    if frappe.db.get_value("Company", sim.COMPANY, "name") is None:
        raise frappe.DoesNotExistError(
            f"La société de simulation « {sim.COMPANY} » n'existe pas : lancez d'abord la simulation."
        )


def retirer_articles_de_test() -> int:
    """Retire du catalogue les articles de test de charge ; garde l'article ERPNext s'il sert déjà dans des locations."""
    frappe.set_user("Administrator")
    removed = 0
    for name in frappe.get_all(
        "Cortex Rental Item Profile",
        filters={"company": sim.COMPANY, "item_code": ["like", "SIM-STRESS%"]},
        pluck="name",
    ):
        frappe.delete_doc("Cortex Rental Item Profile", name, force=True, ignore_permissions=True)
        removed += 1
    frappe.db.commit()
    return removed


def _customers() -> list:
    return frappe.get_all(
        "Customer", filters={"cortex_company": sim.COMPANY}, pluck="name", order_by="name asc", limit_page_length=10
    )


def _existing() -> set:
    return {
        p
        for p in frappe.get_all(
            "Cortex Rental Transaction",
            filters={"company": sim.COMPANY, "project_name": ["like", f"{PREFIX}%"]},
            pluck="project_name",
        )
    }


def _quote(user: str, customer: str, project: str, start: datetime, days: int, items: list) -> str:
    from cortex_rental.api.v1 import rentals

    sim.as_user(user)
    frappe.local.form_dict = frappe._dict(
        {
            "customer_id": customer,
            "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
            "ends_at": (start + timedelta(days=days)).replace(hour=17).strftime("%Y-%m-%d %H:%M:%S"),
            "project_name": project,
            "items": [{"item_code": code, "quantity": qty} for code, qty in items],
            "notes": "Jeu de démonstration.",
        }
    )
    return rentals.create_quote_draft()["entity_id"]


def _to_reservation(user: str, name: str) -> None:
    sim.as_user(user)
    frappe.get_doc("Cortex Rental Transaction", name).transition_to("Reservation", "Jeu de démonstration")


def _request_contract(user: str, name: str) -> str:
    """Prépare les prérequis et soumet le contrat à l'approbation d'une autre personne."""
    from cortex_rental.api.v1 import rentals

    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        {"customer_account_ready": 1, "insurance_ready": 1, "payment_ready": 1},
        update_modified=False,
    )
    sim.as_user(user)
    version = frappe.db.get_value("Cortex Rental Transaction", name, "version")
    return rentals.request_contract(name=name, version=version).get("approval_request_id") or ""


def reinitialiser() -> dict:
    """Supprime les devis de démonstration et leurs demandes d'approbation, puis recrée le jeu (démo répétable)."""
    _guard()
    frappe.set_user("Administrator")
    names = frappe.get_all(
        "Cortex Rental Transaction",
        filters={"company": sim.COMPANY, "project_name": ["like", f"{PREFIX}%"]},
        pluck="name",
    )
    for name in names:
        for approval in frappe.get_all("Approval Request", filters={"entity_id": name}, pluck="name"):
            frappe.delete_doc("Approval Request", approval, force=True, ignore_permissions=True)
        frappe.delete_doc("Cortex Rental Transaction", name, force=True, ignore_permissions=True)
    frappe.db.commit()
    return run()


def run() -> dict:
    _guard()
    report = {"articles_retires": retirer_articles_de_test(), "devis": [], "demandes": [], "ignores": []}
    customers = _customers()
    if not customers:
        raise frappe.DoesNotExistError("Aucun client dans la société de simulation.")
    done = _existing()
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for project, customer_index, offset, days, items, user, stage in PLAN:
        label = PREFIX + project
        if label in done:
            report["ignores"].append(label)
            continue
        try:
            name = _quote(
                user, customers[customer_index % len(customers)], label, today + timedelta(days=offset), days, items
            )
            if stage in ("reservation", "approval"):
                _to_reservation(user, name)
            report["devis"].append({"devis": name, "projet": label, "etape": stage})
            if stage == "approval":
                approval = _request_contract(user, name)
                report["demandes"].append({"demande": approval, "devis": name, "par": user})
        except Exception as exc:  # noqa: BLE001 - on poursuit : un article manquant ne doit pas bloquer le reste
            report["ignores"].append(f"{label} : {type(exc).__name__}: {str(exc)[:120]}")
            frappe.db.rollback()
    frappe.db.commit()
    frappe.set_user("Administrator")
    print(frappe.as_json(report))
    return report
