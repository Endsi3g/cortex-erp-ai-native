"""Tests de charge et de concurrence sur HTTP réel (à lancer après `simulate_company.run`).

    bench --site cortex.local execute cortex_rental.dev_tools.charge_et_concurrence.run

Les requêtes passent par le serveur web (sessions de vrais utilisateurs de la société simulée), jamais par
des appels de service directs : on mesure donc aussi les verrous, les transactions et la sérialisation.
Résultat : /tmp/cortex_stress_metrics.json.
"""

import json
import statistics
import threading
import time
from datetime import datetime, timedelta

import frappe
import requests

from cortex_rental.dev_tools.simulate_company import COMPANY, COUNTERS, MANAGER, PASSWORD

BASE = "http://localhost:8000"
OUT = "/tmp/cortex_stress_metrics.json"
RESULTS = {}


def session(user):
    s = requests.Session()
    response = s.post(f"{BASE}/api/method/login", data={"usr": user, "pwd": PASSWORD}, timeout=30)
    response.raise_for_status()
    return s


def post(s, method, **data):
    started = time.perf_counter()
    response = s.post(f"{BASE}/api/method/{method}", data=data, timeout=60)
    return response, (time.perf_counter() - started) * 1000


def get(s, method, **params):
    started = time.perf_counter()
    response = s.get(f"{BASE}/api/method/{method}", params=params, timeout=60)
    return response, (time.perf_counter() - started) * 1000


def stats(values):
    values = sorted(values)
    if not values:
        return {}
    return {
        "n": len(values),
        "p50": round(statistics.median(values), 1),
        "p95": round(values[min(len(values) - 1, int(len(values) * 0.95))], 1),
        "max": round(values[-1], 1),
    }


def ensure_scarce_item():
    """Un article à 1 seul exemplaire non sérialisé, pour provoquer la course sur la dernière unité."""
    frappe.set_user("Administrator")
    code = "SIM-STRESS-1"
    if not frappe.db.exists("Item", code):
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": "Stabilisateur unique (test de charge)",
                "item_group": "All Item Groups",
                "stock_uom": "Unit",
                "is_stock_item": 0,
            }
        ).insert(ignore_permissions=True)
    if not frappe.db.exists("Cortex Rental Item Profile", {"item_code": code, "company": COMPANY}):
        frappe.get_doc(
            {
                "doctype": "Cortex Rental Item Profile",
                "company": COMPANY,
                "item_code": code,
                "item_name": "Stabilisateur unique (test de charge)",
                "category": "Grip & Rigging",
                "is_rental": 1,
                "is_serialized": 0,
                "total_quantity": 1,
                "daily_rate": 100,
                "replacement_value": 1000,
            }
        ).insert(ignore_permissions=True)
    frappe.db.commit()
    return code


def run_threads(targets):
    results = [None] * len(targets)

    def wrap(i, fn):
        try:
            results[i] = fn()
        except Exception as exc:  # noqa: BLE001
            results[i] = exc

    threads = [threading.Thread(target=wrap, args=(i, fn)) for i, fn in enumerate(targets)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def race_last_unit(code, customers, workers=12):
    """12 comptoirs réservent en même temps la seule unité d'un article : exactement 1 doit réussir."""
    start = (datetime.now() + timedelta(days=500 + int(time.time()) % 3000)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=2)
    sessions = [session(COUNTERS[i % len(COUNTERS)]) for i in range(workers)]
    names = []
    for i, s in enumerate(sessions):
        response, _ = post(
            s,
            "cortex_rental.api.v1.rentals.create_quote_draft",
            customer_id=customers[i],
            starts_at=start.strftime("%Y-%m-%d %H:%M:%S"),
            ends_at=end.strftime("%Y-%m-%d %H:%M:%S"),
            items=json.dumps([{"item_code": code, "quantity": 1}]),
        )
        names.append(response.json()["message"]["entity_id"])
    barrier = threading.Barrier(workers)

    def attempt(i):
        def go():
            barrier.wait()
            return post(sessions[i], "cortex_rental.api.v1.rentals.request_reservation", name=names[i])

        return go

    outcomes = run_threads([attempt(i) for i in range(workers)])
    ok = refused = errors = 0
    latencies = []
    for item in outcomes:
        if isinstance(item, Exception):
            errors += 1
            continue
        response, ms = item
        latencies.append(ms)
        if response.status_code == 200:
            ok += 1
        elif response.status_code in (417, 409, 400, 403):
            refused += 1
        else:
            errors += 1
    frappe.db.rollback()
    reserved = frappe.db.count("Cortex Rental Transaction", {"name": ["in", names], "rental_state": "Reservation"})
    RESULTS["course_derniere_unite"] = {
        "tentatives": workers,
        "succes_http": ok,
        "refus_http": refused,
        "erreurs_inattendues": errors,
        "reservations_en_base": reserved,
        "attendu": "exactement 1",
        "verdict": "OK" if reserved == 1 and errors == 0 else "ÉCHEC",
        "latence_ms": stats(latencies),
    }
    return names


def race_approval(customers, workers=8):
    """Une demande d'approbation décidée 8 fois en même temps : une seule décision doit compter."""
    frappe.set_user("Administrator")
    code = frappe.get_all(
        "Cortex Rental Item Profile",
        filters={"company": COMPANY, "is_serialized": 0, "total_quantity": [">", 5]},
        pluck="item_code",
        limit=1,
    )[0]
    start = (datetime.now() + timedelta(days=300)).replace(hour=9, minute=0, second=0, microsecond=0)
    counter = session(COUNTERS[0])
    response, _ = post(
        counter,
        "cortex_rental.api.v1.rentals.create_quote_draft",
        customer_id=customers[0],
        starts_at=start.strftime("%Y-%m-%d %H:%M:%S"),
        ends_at=(start + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        items=json.dumps([{"item_code": code, "quantity": 1}]),
    )
    name = response.json()["message"]["entity_id"]
    post(counter, "cortex_rental.api.v1.rentals.request_reservation", name=name)
    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        {"customer_account_ready": 1, "insurance_ready": 1, "payment_ready": 1},
        update_modified=False,
    )
    frappe.db.commit()
    response, _ = post(counter, "cortex_rental.api.v1.rentals.request_contract", name=name)
    approval = response.json()["message"]["approval_request_id"]
    managers = [session(MANAGER) for _ in range(workers)]
    barrier = threading.Barrier(workers)

    def attempt(s):
        def go():
            barrier.wait()
            return post(
                s,
                "cortex_rental.api.v1.approval_queue.decide_approval",
                name=approval,
                decision="approve",
                reason="Test",
            )

        return go

    outcomes = run_threads([attempt(s) for s in managers])
    codes = [o[0].status_code for o in outcomes if not isinstance(o, Exception)]
    frappe.db.rollback()
    audit = frappe.db.count("Audit Event", {"entity_id": name, "action": ["like", "%approval%"], "company": COMPANY})
    status = frappe.db.get_value("Approval Request", approval, "status")
    state = frappe.db.get_value("Cortex Rental Transaction", name, "rental_state")
    RESULTS["course_approbation"] = {
        "decisions_simultanees": workers,
        "codes_http": sorted(codes),
        "statut_final": status,
        "etat_location": state,
        "evenements_audit_approbation": audit,
        "verdict": "OK" if status == "Approved" and state == "Contract" and codes.count(200) >= 1 else "À EXAMINER",
    }


def idempotence(customers):
    """Même clé d'idempotence, 6 envois en parallèle : une seule location créée."""
    code = frappe.get_all(
        "Cortex Rental Item Profile", filters={"company": COMPANY, "is_serialized": 0}, pluck="item_code", limit=1
    )[0]
    start = (datetime.now() + timedelta(days=400)).replace(hour=9, minute=0, second=0, microsecond=0)
    key = f"stress-{int(time.time())}"
    sessions = [session(COUNTERS[0]) for _ in range(6)]
    barrier = threading.Barrier(6)
    body = {
        "customer_id": customers[1],
        "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
        "ends_at": (start + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "items": json.dumps([{"item_code": code, "quantity": 1}]),
    }

    def attempt(s):
        def go():
            barrier.wait()
            return s.post(
                f"{BASE}/api/method/cortex_rental.api.v1.rentals.create_quote_draft",
                data=body,
                headers={"Idempotency-Key": key},
                timeout=60,
            )

        return go

    outcomes = run_threads([attempt(s) for s in sessions])
    ids = {
        o.json().get("message", {}).get("entity_id")
        for o in outcomes
        if not isinstance(o, Exception) and o.status_code == 200
    }
    RESULTS["idempotence"] = {
        "envois_paralleles": 6,
        "locations_distinctes_creees": len(ids - {None}),
        "codes_http": sorted(o.status_code for o in outcomes if not isinstance(o, Exception)),
        "verdict": "OK" if len(ids - {None}) == 1 else "ÉCHEC",
    }


def benchmarks():
    """Lectures au volume simulé (≈470 locations, ~2 100 lignes) : p50/p95 sur 20 appels chacune."""
    s = session(MANAGER)
    today = datetime.now().date()
    cases = {
        "liste_locations_20": ("cortex_rental.api.v1.rentals.list_rentals", {"page": 1, "page_size": 20}),
        "liste_locations_filtre_etat": ("cortex_rental.api.v1.rentals.list_rentals", {"state": "Checked Out"}),
        "grille_dispo_7j": (
            "cortex_rental.api.v1.availability.get_matrix",
            {"starts_at": str(today), "ends_at": str(today + timedelta(days=7))},
        ),
        "grille_dispo_30j": (
            "cortex_rental.api.v1.availability.get_matrix",
            {"starts_at": str(today), "ends_at": str(today + timedelta(days=30))},
        ),
        "file_approbations": ("cortex_rental.api.v1.approval_queue.list_approval_requests", {"status": "pending"}),
    }
    out = {}
    for label, (method, params) in cases.items():
        times, failures = [], 0
        for _ in range(20):
            response, ms = get(s, method, **params)
            times.append(ms)
            failures += response.status_code != 200
        out[label] = {**stats(times), "echecs": failures}
    reports = [
        "Disponibilité du parc",
        "Prochains départs et retours",
        "Activité des clients",
        "Relevé propriétaire",
        "Versements de consignation",
    ]
    for report in reports:
        times, failures = [], 0
        for _ in range(10):
            response, ms = post(
                s,
                "frappe.desk.query_report.run",
                report_name=report,
                filters=json.dumps({"company": COMPANY}),
            )
            times.append(ms)
            failures += response.status_code != 200
        out[f"rapport:{report}"] = {**stats(times), "echecs": failures}
    for doctype in ("Cortex Rental Transaction", "Serial No", "Audit Event", "Customer"):
        times = []
        for _ in range(10):
            response, ms = get(
                s,
                "frappe.desk.reportview.get",
                doctype=doctype,
                fields=json.dumps(["name"]),
                limit_page_length=20,
            )
            times.append(ms)
        out[f"vue_liste:{doctype}"] = stats(times)
    for workspace in ("Cortex", "Accueil Cortex"):
        times = []
        for _ in range(5):
            response, ms = get(s, "frappe.desk.desktop.get_desktop_page", page=json.dumps({"name": workspace}))
            times.append(ms)
        out[f"espace:{workspace}"] = {**stats(times), "http": response.status_code}
    times = []
    for _ in range(10):
        response, ms = get(s, "frappe.sessions.get")
        times.append(ms)
    out["demarrage_session(bootinfo)"] = stats(times)
    RESULTS["lectures"] = out


def concurrent_load(workers=16, seconds=20):
    """Charge mixte : 16 utilisateurs qui lisent la liste, la grille et la file pendant 20 s."""
    deadline = time.time() + seconds
    times, failures = [], [0]
    lock = threading.Lock()
    today = datetime.now().date()

    def worker():
        s = session(MANAGER)
        while time.time() < deadline:
            for method, params in (
                ("cortex_rental.api.v1.rentals.list_rentals", {"page": 1, "page_size": 20}),
                (
                    "cortex_rental.api.v1.availability.get_matrix",
                    {"starts_at": str(today), "ends_at": str(today + timedelta(days=14))},
                ),
                ("cortex_rental.api.v1.approval_queue.list_approval_requests", {"status": "pending"}),
            ):
                response, ms = get(s, method, **params)
                with lock:
                    times.append(ms)
                    failures[0] += response.status_code != 200

    run_threads([worker for _ in range(workers)])
    RESULTS["charge_mixte"] = {
        "utilisateurs": workers,
        "duree_s": seconds,
        "requetes": len(times),
        "debit_req_s": round(len(times) / seconds, 1),
        "echecs": failures[0],
        **stats(times),
    }


def nettoyer():
    """Supprime les locations créées par ces tests (dates à plus de 60 jours, hors période simulée) et leurs traces."""
    frappe.set_user("Administrator")
    limite = datetime.now() + timedelta(days=60)
    noms = frappe.get_all(
        "Cortex Rental Transaction", filters={"company": COMPANY, "starts_at": [">=", limite]}, pluck="name"
    )
    frappe.flags.dev_cleanup = True  # seul ce script de développement peut supprimer factures et paiements
    for nom in noms:
        for doctype, champ in (
            ("Cortex Rental Payment", "rental_transaction"),
            ("Cortex Rental Invoice", "rental_transaction"),
            ("Approval Request", "entity_id"),
        ):  # le journal d'audit est immuable
            for lien in frappe.get_all(doctype, filters={champ: nom}, pluck="name"):
                frappe.delete_doc(doctype, lien, force=True, ignore_permissions=True)
        frappe.delete_doc("Cortex Rental Transaction", nom, force=True, ignore_permissions=True)
    frappe.db.commit()
    print(f"{len(noms)} location(s) de test supprimée(s)")


def run():
    frappe.init(site=frappe.local.site) if not getattr(frappe.local, "site", None) else None
    frappe.set_user("Administrator")
    customers = frappe.get_all("Customer", filters={"cortex_company": COMPANY}, pluck="name", limit=20)
    code = ensure_scarce_item()
    race_last_unit(code, customers)
    race_approval(customers)
    idempotence(customers)
    benchmarks()
    concurrent_load()
    nettoyer()
    with open(OUT, "w") as handle:
        json.dump(RESULTS, handle, indent=2, ensure_ascii=False)
    print(json.dumps(RESULTS, indent=2, ensure_ascii=False))
