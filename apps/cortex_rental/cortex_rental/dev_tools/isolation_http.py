"""Isolation entre sociétés par HTTP réel : une personne d'une société ne doit jamais voir ni modifier les données d'une autre.

    python3 apps/cortex_rental/cortex_rental/dev_tools/isolation_http.py http://localhost:8000

Prérequis : la société de simulation (`simulate_company`) et la société d'essai du fuzz (`fuzz_endpoints.prepare`).
Le « propriétaire Fuzz » tente de lire, lister, modifier et chercher des données de la société simulée par toutes les
voies : API Cortex, API de ressources de Frappe, rapports, recherche globale. Code de sortie 1 s'il y a une fuite.
"""

import json
import sys

import requests

PASSWORD = "Sim-Pass-2026!"
INTRUS = "fuzz.proprio@example.com"
VICTIME = "sim.proprio@cortex.test"
VICTIME_SOCIETE = "Simulation Plateau Montréal"


def login(base, user):
    s = requests.Session()
    s.headers["X-Frappe-Site-Name"] = "cortex.local"
    s.post(f"{base}/api/method/login", data={"usr": user, "pwd": PASSWORD}, timeout=30).raise_for_status()
    return s


def run(base="http://localhost:8000"):
    victim = login(base, VICTIME)
    intruder = login(base, INTRUS)
    leaks, checks = [], 0

    def sample(doctype, fields):
        r = victim.get(
            f"{base}/api/method/frappe.client.get_list",
            params={"doctype": doctype, "fields": json.dumps(fields), "limit_page_length": 3},
        )
        return [row["name"] for row in r.json().get("message", [])]

    ids = {
        "Cortex Rental Transaction": sample("Cortex Rental Transaction", ["name"]),
        "Cortex Rental Invoice": sample("Cortex Rental Invoice", ["name"]),
        "Cortex Rental Payment": sample("Cortex Rental Payment", ["name"]),
        "Customer": sample("Customer", ["name"]),
        "Approval Request": sample("Approval Request", ["name"]),
        "Audit Event": sample("Audit Event", ["name"]),
        "Cortex Rental Item Profile": sample("Cortex Rental Item Profile", ["name"]),
    }

    # Contrôle positif : la victime lit bien ses propres données (sinon un « OK » ne prouverait rien).
    own = (ids["Cortex Rental Transaction"] or [""])[0]
    control = victim.get(f"{base}/api/resource/Cortex Rental Transaction/{own}")
    control_ok = control.status_code == 200 and own in control.text

    def check(label, response, forbidden):
        nonlocal checks
        checks += 1
        body = response.text
        hit = [f for f in forbidden if f and f in body and response.status_code == 200]
        if hit:
            leaks.append({"voie": label, "status": response.status_code, "fuite": hit[:3]})

    for doctype, names in ids.items():
        for name in names:
            slug = doctype
            # 1. lecture directe par l'API de ressources et par frappe.client
            check(f"resource {doctype}", intruder.get(f"{base}/api/resource/{slug}/{name}"), [name])
            check(
                f"client.get {doctype}",
                intruder.get(f"{base}/api/method/frappe.client.get", params={"doctype": doctype, "name": name}),
                [name],
            )
            # 2. modification
            r = intruder.put(f"{base}/api/resource/{slug}/{name}", json={"modified_by": INTRUS})
            checks += 1
            if r.status_code == 200:
                leaks.append({"voie": f"PUT {doctype}", "status": 200, "fuite": [name]})
        # 3. liste filtrée sur l'autre société
        r = intruder.get(
            f"{base}/api/method/frappe.client.get_list",
            params={"doctype": doctype, "fields": json.dumps(["name"]), "limit_page_length": 50},
        )
        check(f"get_list {doctype}", r, names)
        r = intruder.get(
            f"{base}/api/method/frappe.desk.reportview.get",
            params={"doctype": doctype, "fields": json.dumps(["name"]), "limit_page_length": 50},
        )
        check(f"reportview {doctype}", r, names)
        r = intruder.get(f"{base}/api/method/frappe.desk.search.search_link", params={"doctype": doctype, "txt": ""})
        check(f"search_link {doctype}", r, names)

    # 4. endpoints Cortex avec des identifiants de l'autre société
    rental = (ids["Cortex Rental Transaction"] or [""])[0]
    customer = (ids["Customer"] or [""])[0]
    calls = [
        ("rentals.get_rental", {"name": rental}),
        ("rentals.get_rental", {"rental_id": rental}),
        ("dossier.get_dossier", {"doctype": "Cortex Rental Transaction", "name": rental}),
        ("quote_share.list_shares", {"rental_id": rental}),
        ("customers.get_customer_summary", {"customer": customer}),
        ("customers.customer_summary", {"customer_id": customer}),
    ]
    for path, params in calls:
        for method in ("get", "post"):
            r = getattr(intruder, method)(
                f"{base}/api/method/cortex_rental.api.v1.{path}",
                **({"params": params} if method == "get" else {"data": params}),
            )
            check(f"{path} ({method})", r, [rental, customer] if r.status_code == 200 else [])
    # 5. rapports filtrés sur la société de la victime
    for report in (
        "Disponibilité du parc",
        "Créances par client",
        "Taxes perçues",
        "Journal comptable",
        "Utilisation du parc",
    ):
        r = intruder.post(
            f"{base}/api/method/frappe.desk.query_report.run",
            data={"report_name": report, "filters": json.dumps({"company": VICTIME_SOCIETE})},
        )
        checks += 1
        if (
            r.status_code == 200
            and "Simulation" in r.text
            and VICTIME_SOCIETE in r.text
            and '"result": []' not in r.text
        ):
            rows = r.json().get("message", {}).get("result", [])
            if rows:
                leaks.append({"voie": f"rapport {report}", "status": 200, "fuite": [f"{len(rows)} ligne(s)"]})
    report = {
        "verifications": checks,
        "controle_positif": control_ok,
        "fuites": leaks,
        "verdict": "OK" if (not leaks and control_ok) else "FUITE" if leaks else "TEST NON PROBANT",
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return report


if __name__ == "__main__":
    result = run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
    sys.exit(0 if not result["fuites"] else 1)
