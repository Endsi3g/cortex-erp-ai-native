"""Simulate about three months of a real rental company, for stress-testing and auditing Cortex.

DEVELOPMENT ONLY. Run on a bench, never on a production site:

    bench --site cortex.local execute cortex_rental.dev_tools.simulate_company.run

It provisions its own company ("Simulation Plateau Montréal") with its own people, goes through the same service and
API functions the screens use (quote, reservation, contract approval, check-out by scan, check-in, dispute,
cancellation), processes simulated days in chronological order, and writes timings and integrity findings to
`/tmp/cortex_sim_metrics.json`. Nothing here is shown to customers: every record belongs to the simulation company.
"""

import json
import random
import statistics
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import frappe

COMPANY = "Simulation Plateau Montréal"
PASSWORD = "Sim-Pass-2026!"
OWNER = "sim.owner@cortex.test"
PROPRIO = "sim.proprio@cortex.test"  # propriétaire complet : rôle « Cortex System Manager » et tous les rôles Cortex
MANAGER = "sim.manager@cortex.test"
OWNER_ROLES = [
    "Cortex System Manager",
    "Rental Manager",
    "Cortex Operations Manager",
    "Cortex Finance Manager",
    "Cortex Inventory Manager",
    "Cortex Consignment Manager",
    "Cortex Account Reviewer",
]
COUNTERS = ["sim.comptoir1@cortex.test", "sim.comptoir2@cortex.test"]
METRICS_PATH = "/tmp/cortex_sim_metrics.json"
LOG_PATH = "/tmp/cortex_sim.log"

CATALOG = [
    # (prefix, nom, catégorie, sérialisé, quantité, tarif/jour, valeur de remplacement)
    ("CAM-ALX", "Caméra ARRI Alexa 35", "Camera Bodies", 1, 4, 1500, 75000),
    ("CAM-MIN", "Caméra ARRI Alexa Mini LF", "Camera Bodies", 1, 3, 1200, 60000),
    ("CAM-RED", "Caméra RED V-Raptor", "Camera Bodies", 1, 3, 900, 38000),
    ("CAM-FX6", "Caméra Sony FX6", "Camera Bodies", 1, 6, 350, 7500),
    ("CAM-BMP", "Caméra Blackmagic Pocket 6K", "Camera Bodies", 1, 5, 150, 3000),
    ("LNS-CKE", "Objectifs Cooke S4/i (série de 5)", "Cinema Lenses", 1, 3, 800, 45000),
    ("LNS-ZSP", "Objectifs Zeiss Supreme Prime (série de 6)", "Cinema Lenses", 1, 2, 1100, 70000),
    ("LNS-ANG", "Zoom Angénieux 24-290 mm", "Cinema Lenses", 1, 2, 650, 38000),
    ("LNS-SIG", "Objectifs Sigma Cine (série de 3)", "Cinema Lenses", 1, 4, 220, 9000),
    ("LGT-APU", "Projecteur Aputure 1200d Pro", "Lighting", 1, 6, 250, 6000),
    ("LGT-ARR", "Projecteur ARRI SkyPanel S60", "Lighting", 1, 8, 180, 7500),
    ("LGT-NAN", "Panneau Nanlite Forza 500", "Lighting", 1, 8, 90, 2500),
    ("LGT-KIT", "Trousse LED Astera (8 tubes)", "Lighting", 1, 4, 300, 12000),
    ("LGT-FRS", "Fresnel Tungstène 2 kW", "Lighting", 0, 12, 45, 900),
    ("GRP-CST", "Pied C-Stand Avenger 40 po", "Grip & Rigging", 0, 40, 18, 220),
    ("GRP-DLY", "Dolly Panther Fluid", "Grip & Rigging", 1, 3, 450, 14000),
    ("GRP-JIB", "Grue Jib 12 pi", "Grip & Rigging", 1, 2, 380, 9000),
    ("GRP-SND", "Sacs de sable 25 lb", "Grip & Rigging", 0, 60, 4, 35),
    ("GRP-FLG", "Drapeaux et réflecteurs (ensemble)", "Grip & Rigging", 0, 15, 25, 300),
    ("GRP-TRK", "Rails de travelling 20 pi", "Grip & Rigging", 1, 4, 140, 4200),
    ("AUD-SND", "Enregistreur Sound Devices 833", "Audio", 1, 4, 160, 5000),
    ("AUD-SEN", "Micro-cravate Sennheiser (paire)", "Audio", 1, 10, 45, 1100),
    ("AUD-BOM", "Perche et bonnette Rycote", "Audio", 0, 10, 30, 600),
    ("AUD-ZXN", "Micro canon Sennheiser MKH 416", "Audio", 1, 6, 55, 1300),
    ("MON-SMM", "Moniteur SmallHD 17 po", "Monitors & Wireless Video", 1, 5, 120, 4500),
    ("MON-TER", "Transmission vidéo Teradek Bolt 4K", "Monitors & Wireless Video", 1, 6, 190, 6500),
    ("MON-ATM", "Enregistreur Atomos Ninja V", "Monitors & Wireless Video", 1, 8, 60, 900),
    ("MON-DIR", "Station de direction vidéo (chariot)", "Monitors & Wireless Video", 1, 2, 320, 12000),
    ("PWR-ABM", "Batteries Anton/Bauer (lot de 4)", "Power & Batteries", 1, 10, 40, 1600),
    ("PWR-GOL", "Batteries Gold Mount 150 Wh", "Power & Batteries", 0, 30, 15, 380),
    ("PWR-GEN", "Génératrice silencieuse 5 kW", "Power & Batteries", 1, 3, 280, 9500),
    ("PWR-DST", "Panneau de distribution 100 A", "Power & Batteries", 1, 4, 65, 2200),
    ("PWR-CBL", "Rallonges électriques 50 pi", "Power & Batteries", 0, 50, 5, 60),
    ("GRP-HMI", "Ballasts HMI 4 kW", "Lighting", 1, 4, 210, 8000),
    ("CAM-MTB", "Matte box et follow focus", "Camera Bodies", 0, 10, 110, 2500),
    ("MON-TRK", "Moniteur de retour 7 po", "Monitors & Wireless Video", 0, 20, 28, 450),
]
PACKAGES = [
    ("camera", ["CAM-ALX", "CAM-MIN", "CAM-RED", "CAM-FX6", "CAM-BMP"], ["LNS-CKE", "LNS-ZSP", "LNS-SIG", "LNS-ANG"]),
    ("lumiere", ["LGT-APU", "LGT-ARR", "LGT-NAN", "LGT-KIT", "LGT-HMI"], ["GRP-CST", "GRP-FLG", "GRP-SND", "PWR-CBL"]),
    ("son", ["AUD-SND"], ["AUD-SEN", "AUD-BOM", "AUD-ZXN"]),
    ("video", ["MON-SMM", "MON-TER", "MON-DIR"], ["MON-ATM", "MON-TRK"]),
]
COMPANIES_PREFIX = [
    "Productions",
    "Studio",
    "Films",
    "Média",
    "Créations",
    "Vidéo",
    "Atelier",
    "Collectif",
    "Agence",
    "Publicité",
]
COMPANIES_NAME = [
    "Mont-Royal",
    "Plateau",
    "Saint-Laurent",
    "Rosemont",
    "Outremont",
    "Villeray",
    "Griffintown",
    "Lachine",
    "Verdun",
    "Hochelaga",
    "Mile-End",
    "Vieux-Port",
    "Laurentides",
    "Charlevoix",
    "Gaspé",
    "Saguenay",
    "Estrie",
    "Beauce",
]

STATE_TIMES = defaultdict(list)
ERRORS = Counter()
EVENTS = Counter()
ERROR_SAMPLES = {}


def log(message):
    line = f"{datetime.now().strftime('%H:%M:%S')} {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def timed(label, fn, *args, **kwargs):
    started = time.perf_counter()
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - the simulation records every failure
        ERRORS[f"{label}: {type(exc).__name__}"] += 1
        ERROR_SAMPLES.setdefault(f"{label}: {type(exc).__name__}", str(exc)[:240])
        raise
    finally:
        STATE_TIMES[label].append((time.perf_counter() - started) * 1000)


def as_user(user):
    frappe.set_user(user)
    frappe.local.form_dict = frappe._dict()


def call(user, fn, **form):
    as_user(user)
    frappe.local.form_dict = frappe._dict(form)
    return fn(**{k: v for k, v in form.items() if k in fn.__code__.co_varnames[: fn.__code__.co_argcount]})


# ------------------------------------------------------------------ provisioning
def provision():
    from cortex_rental.services import tenant_provisioning as tp

    frappe.set_user("Administrator")
    if not frappe.db.exists("Company", COMPANY):
        tp.create_company(COMPANY)
        log(f"Société créée : {COMPANY}")
    tp.ensure_default_pricing_rule(COMPANY)
    from cortex_rental.services import billing

    billing.ensure_settings(COMPANY)
    frappe.db.set_value(
        "Cortex Finance Settings",
        COMPANY,
        {
            "late_fee_enabled": 1,
            "late_fee_grace_minutes": 60,
            "late_fee_percent": 100,
            "late_fee_cap_days": 3,
            "tps_number": "123456789 RT0001",
            "tvq_number": "1234567890 TQ0001",
        },
    )
    people = [
        (OWNER, "Simone Propriétaire", "manager"),
        (PROPRIO, "Paul Propriétaire", "owner"),
        (MANAGER, "Marc Gestionnaire", "manager"),
        (COUNTERS[0], "Camille Comptoir", "counter"),
        (COUNTERS[1], "Louis Comptoir", "counter"),
    ]
    from frappe.utils.password import update_password

    for email, name, preset in people:
        if not frappe.db.exists("User", email):
            roles = OWNER_ROLES if preset == "owner" else tp.ROLE_PRESETS[preset]["roles"]
            tp.create_user(email, name, COMPANY, roles)
        update_password(email, PASSWORD)
    frappe.db.commit()


def build_catalog(rng):
    frappe.set_user("Administrator")
    serials_by_item = {}
    for prefix, name, category, serialized, quantity, rate, replacement in CATALOG:
        code = f"SIM-{prefix}"
        if not frappe.db.exists("Item", code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": code,
                    "item_name": name,
                    "item_group": "All Item Groups",
                    "stock_uom": "Unit",
                    "is_stock_item": 0,
                    "has_serial_no": 0,
                }
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Cortex Rental Item Profile", {"item_code": code, "company": COMPANY}):
            frappe.get_doc(
                {
                    "doctype": "Cortex Rental Item Profile",
                    "company": COMPANY,
                    "item_code": code,
                    "item_name": name,
                    "category": category,
                    "is_rental": 1,
                    "is_serialized": serialized,
                    "total_quantity": quantity,
                    "daily_rate": rate,
                    "replacement_value": replacement,
                }
            ).insert(ignore_permissions=True)
        serials = []
        if serialized:
            for n in range(1, quantity + 1):
                serial = f"SIM-{prefix}-{n:03d}"
                serials.append(serial)
                if not frappe.db.exists("Serial No", serial):
                    frappe.get_doc(
                        {
                            "doctype": "Serial No",
                            "serial_no": serial,
                            "item_code": code,
                            "company": COMPANY,
                            "cortex_status": "Active",
                        }
                    ).insert(ignore_permissions=True)
        serials_by_item[code] = serials
    frappe.db.commit()
    return serials_by_item


def build_customers(rng, count=120):
    frappe.set_user("Administrator")
    if not frappe.db.exists("Customer Group", "Commercial"):
        frappe.get_doc({"doctype": "Customer Group", "customer_group_name": "Commercial", "is_group": 0}).insert(
            ignore_permissions=True
        )
    existing = frappe.get_all("Customer", filters={"cortex_company": COMPANY}, pluck="name")
    if len(existing) >= count:
        return existing
    names = set()
    while len(names) < count - len(existing):
        names.add(
            f"{rng.choice(COMPANIES_PREFIX)} {rng.choice(COMPANIES_NAME)} {rng.choice(['inc.', 's.e.n.c.', 'ltée', ''])}".strip()
        )
    created = list(existing)
    for label in sorted(names):
        label = f"{label} (SIM)"
        if frappe.db.exists("Customer", {"customer_name": label}):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": label,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
                "cortex_company": COMPANY,
            }
        )
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    frappe.db.commit()
    return created


# ------------------------------------------------------------------ one rental's life
def basket(rng, codes_available):
    chosen = []
    kinds = rng.sample(PACKAGES, k=rng.choice([1, 1, 1, 2, 2, 3]))
    for _, mains, accessories in kinds:
        main = rng.choice(mains)
        if main in codes_available:
            chosen.append((main, rng.choice([1, 1, 1, 2])))
        for accessory in rng.sample(accessories, k=min(len(accessories), rng.choice([1, 2, 3]))):
            if accessory in codes_available:
                chosen.append(
                    (
                        accessory,
                        rng.choice([1, 2, 4, 6, 10]) if accessory.startswith(("GRP-CST", "GRP-SND", "PWR-CBL")) else 1,
                    )
                )
    merged = {}
    for code, qty in chosen:
        merged[code] = merged.get(code, 0) + qty
    return [{"item_code": f"SIM-{c}", "quantity": q} for c, q in merged.items()]


def new_quote(rng, customers, sim_day, stats):
    from cortex_rental.api.v1 import rentals

    counter = rng.choice(COUNTERS)
    lead = rng.choice([0, 1, 2, 3, 5, 7, 7, 10, 14, 21])
    start = datetime.combine(sim_day + timedelta(days=lead), datetime.min.time()) + timedelta(hours=9)
    days = rng.choice([1, 1, 2, 2, 3, 3, 4, 5, 7, 7, 10])
    end = start + timedelta(days=days)
    codes = {f"{p[0]}" for p in CATALOG}
    items = basket(rng, codes)
    if not items:
        return None
    customer = rng.choice(customers)
    payload = {
        "customer_id": customer,
        "starts_at": start.strftime("%Y-%m-%d %H:%M:%S"),
        "ends_at": end.strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": f"Tournage {rng.choice(['publicité', 'court métrage', 'série web', 'documentaire', 'clip', 'corporatif'])} {rng.randint(1, 99)}",
        "items": items,
    }
    as_user(counter)
    frappe.local.form_dict = frappe._dict(payload)
    result = timed("devis.creer", rentals.create_quote_draft)
    name = result["entity_id"]
    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        "creation",
        datetime.combine(sim_day, datetime.min.time()) + timedelta(hours=rng.randint(8, 17)),
        update_modified=False,
    )
    EVENTS["devis"] += 1
    return {"name": name, "counter": counter, "start": start.date(), "end": end.date(), "days": days}


def progress_rental(rng, record, sim_day, today, stats, schedule):
    """Quote -> reservation -> contract approval, all on the day the quote is created."""
    from cortex_rental.api.v1 import approval_queue, rentals

    name, counter = record["name"], record["counter"]
    if rng.random() > 0.80:
        as_user(counter)
        doc = frappe.get_doc("Cortex Rental Transaction", name)
        timed("devis.annuler", doc.transition_to, "Cancelled", "Client non retenu")
        EVENTS["devis_perdu"] += 1
        return
    as_user(counter)
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    try:
        timed("reservation", doc.transition_to, "Reservation", "Simulation")
    except Exception:
        EVENTS["reservation_refusee_disponibilite"] += 1
        as_user(counter)
        doc = frappe.get_doc("Cortex Rental Transaction", name)
        timed("devis.annuler", doc.transition_to, "Cancelled", "Matériel indisponible")
        return
    EVENTS["reservation"] += 1
    backdate_invoices(name, sim_day)
    deposit = deposit_invoice_of(name)
    if deposit and rng.random() < 0.92:
        pay_invoice(deposit.name, deposit.total, sim_day, rng)
    frappe.db.set_value(
        "Cortex Rental Transaction",
        name,
        {
            "customer_account_ready": 1 if rng.random() < 0.96 else 0,
            "insurance_ready": 1 if rng.random() < 0.95 else 0,
            "payment_ready": 1 if rng.random() < 0.94 else 0,
        },
        update_modified=False,
    )
    as_user(counter)
    frappe.local.form_dict = frappe._dict({"name": name})
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    request = timed("contrat.demande", rentals.request_contract, name=name, version=doc.version)
    approval = request.get("approval_request_id")
    EVENTS["contrat_demande"] += 1
    as_user(MANAGER)
    if rng.random() < 0.97:
        try:
            timed(
                "contrat.approuver",
                approval_queue.decide_approval,
                name=approval,
                decision="approve",
                reason="Simulation",
            )
            EVENTS["contrat_approuve"] += 1
        except Exception:
            EVENTS["contrat_bloque_preconditions"] += 1
            return
        schedule[record["start"]].append(("sortie", name, record))
    else:
        timed(
            "contrat.refuser",
            approval_queue.decide_approval,
            name=approval,
            decision="reject",
            reason="Dossier incomplet",
        )
        EVENTS["contrat_refuse"] += 1


def backdate_invoices(name, sim_day):
    """Les factures sont émises « aujourd'hui » par le serveur : on les date du jour simulé pour les vues financières."""
    due_days = int(frappe.db.get_value("Cortex Finance Settings", COMPANY, "invoice_due_days") or 0)
    frappe.db.sql(
        "UPDATE `tabCortex Rental Invoice` SET issue_date=%s, due_date=%s, creation=%s WHERE rental_transaction=%s AND issue_date=CURDATE()",
        (
            sim_day,
            sim_day + timedelta(days=due_days),
            datetime.combine(sim_day, datetime.min.time()) + timedelta(hours=10),
            name,
        ),
    )


def pay_invoice(invoice, amount, sim_day, rng, kind="Payment"):
    from cortex_rental.api.v1 import billing

    as_user(rng.choice(COUNTERS))
    frappe.local.form_dict = frappe._dict()
    timed(
        "paiement.enregistrer",
        billing.record_payment,
        invoice=invoice,
        amount=amount,
        method=rng.choice(["Card", "Card", "Card", "Bank Transfer", "Cash", "Cheque"]),
        paid_on=str(sim_day),
        reference=f"SIM-{rng.randint(1000, 9999)}",
        kind=kind,
    )
    EVENTS["paiement" if kind == "Payment" else "remboursement"] += 1


def deposit_invoice_of(name):
    return frappe.db.get_value(
        "Cortex Rental Invoice",
        {"rental_transaction": name, "invoice_type": "Deposit", "status": ["!=", "Cancelled"]},
        ["name", "total"],
        as_dict=True,
    )


def do_checkout(name, record, rng, schedule):
    from cortex_rental.api.v1 import checkout

    as_user(rng.choice(COUNTERS))
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.rental_state != "Contract":
        EVENTS["sortie_ignoree_etat"] += 1
        return
    for row in doc.items:
        for serial in frappe.parse_json(row.assigned_serials or "[]"):
            frappe.local.form_dict = frappe._dict({"rental_id": name, "serial_number": serial})
            timed("sortie.scan", checkout.record_checkout_scan)
    frappe.local.form_dict = frappe._dict({"rental_id": name})
    timed("sortie.terminer", checkout.complete_checkout)
    EVENTS["sortie"] += 1
    late = rng.random() < 0.14
    delay = rng.choice([1, 2, 3]) if late else 0
    schedule[record["end"] + timedelta(days=delay)].append(("retour", name, record))
    if late:
        EVENTS["retour_en_retard"] += 1


def do_checkin(name, rng, schedule, sim_day, consigned):
    from cortex_rental.services.checkin import process_checkin

    as_user(rng.choice(COUNTERS))
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.rental_state != "Checked Out":
        return
    roll = rng.random()
    if roll < 0.012:
        as_user(MANAGER)
        timed("litige", doc.transition_to, "Disputed", "Dommages contestés")
        EVENTS["litige"] += 1
        return
    items = []
    for row in doc.items:
        serials = frappe.parse_json(row.assigned_serials or "[]")
        if serials:
            for serial in serials:
                r = rng.random()
                if r < 0.04:
                    cond, disp, sev, typ = (
                        "Damaged",
                        rng.choice(["Quarantine", "Repair"]),
                        "Functional",
                        "Physical / Impact",
                    )
                elif r < 0.05:
                    cond, disp, sev, typ = "Missing", "Missing", "Blocking", "Missing Parts"
                else:
                    cond, disp, sev, typ = "Good", "Return to Stock", "None", "None"
                items.append(
                    {
                        "transaction_item": row.name,
                        "item_code": row.item_code,
                        "serial_no": serial,
                        "expected_qty": 1,
                        "returned_qty": 1,
                        "condition": cond,
                        "disposition": disp,
                        "damage_severity": sev,
                        "damage_type": typ,
                        "estimated_repair_cost": 250 if cond == "Damaged" else 0,
                    }
                )
        else:
            items.append(
                {
                    "transaction_item": row.name,
                    "item_code": row.item_code,
                    "expected_qty": row.qty,
                    "returned_qty": row.qty,
                    "condition": "Good",
                    "disposition": "Return to Stock",
                }
            )
    result = timed(
        "retour.enregistrer", process_checkin, COMPANY, frappe.session.user, name, items, "auto", "Simulation"
    )
    EVENTS["retour"] += 1
    ends_on = frappe.db.get_value("Cortex Rental Transaction", name, "ends_at").date()
    returned_at = datetime.combine(sim_day, datetime.min.time()) + timedelta(
        hours=8, minutes=30 if sim_day <= ends_on else 120
    )
    frappe.db.set_value("Cortex Check-In", {"transaction": name}, "checked_in_at", returned_at, update_modified=False)
    if (
        result.get("transaction_fully_returned")
        or frappe.db.get_value("Cortex Rental Transaction", name, "rental_state") == "Returned"
    ):
        if rng.random() < 0.70:
            schedule[sim_day + timedelta(days=rng.choice([2, 3, 5, 7]))].append(("cloture", name, None))


def do_close(name, sim_day=None, rng=None, schedule=None):
    as_user(MANAGER)
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.rental_state == "Returned":
        timed("cloture", doc.transition_to, "Closed", "Dossier clôturé")
        EVENTS["cloture"] += 1
        backdate_invoices(name, sim_day)
        final = frappe.db.get_value(
            "Cortex Rental Invoice",
            {"rental_transaction": name, "invoice_type": "Final", "status": ["!=", "Cancelled"]},
            ["name", "total"],
            as_dict=True,
        )
        if final and final.total > 0:
            EVENTS["facture_finale"] += 1
            roll = rng.random()
            if roll < 0.80:
                schedule[sim_day + timedelta(days=rng.choice([0, 1, 3, 7, 14]))].append(
                    ("paiement", final.name, final.total)
                )
            elif roll < 0.90:
                schedule[sim_day + timedelta(days=rng.choice([5, 10]))].append(
                    ("paiement", final.name, round(final.total * 0.5, 2))
                )
            else:
                EVENTS["facture_impayee"] += 1


# ------------------------------------------------------------------ main loop
def simulate(seed, days):
    rng = random.Random(seed)
    today = date.today()
    first = today - timedelta(days=days)
    customers = build_customers(rng)
    build_catalog(rng)
    schedule = defaultdict(list)
    per_day = []
    log(f"Simulation du {first} au {today} ({days} jours), {len(customers)} clients, {len(CATALOG)} équipements")
    for offset in range(days + 1):
        sim_day = first + timedelta(days=offset)
        started = time.perf_counter()
        weekday = sim_day.weekday()
        expected = 8 if weekday < 5 else 3
        created = max(0, int(rng.gauss(expected, 2.5)))
        for _ in range(created):
            try:
                record = new_quote(rng, customers, sim_day, None)
                if record:
                    progress_rental(rng, record, sim_day, today, None, schedule)
            except Exception:
                frappe.db.rollback()
        for kind, name, record in list(schedule.get(sim_day, [])):
            try:
                if kind == "sortie":
                    do_checkout(name, record, rng, schedule)
                elif kind == "retour":
                    do_checkin(name, rng, schedule, sim_day, None)
                elif kind == "cloture":
                    do_close(name, sim_day, rng, schedule)
                elif kind == "paiement":
                    pay_invoice(name, record, sim_day, rng)
            except Exception:
                frappe.db.rollback()
        # un retard de retour reporté au-delà d'aujourd'hui reste « Sorti » : c'est voulu
        frappe.db.commit()
        per_day.append((str(sim_day), created, round(time.perf_counter() - started, 2)))
        if offset % 10 == 0:
            log(f"Jour {offset}/{days} : {dict(EVENTS)}")
    return per_day


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * q))], 1)


def finance_integrity():
    """Contrôles financiers : soldes, taxes, une facture finale par location close, acompte présent, rapprochement."""
    out = {}
    q = lambda sql, *a: frappe.db.sql(sql, a or COMPANY)[0][0]  # noqa: E731
    out["factures"] = dict(
        frappe.db.sql(
            "SELECT invoice_type, COUNT(*) FROM `tabCortex Rental Invoice` WHERE company=%s GROUP BY invoice_type",
            COMPANY,
        )
    )
    out["par_statut"] = dict(
        frappe.db.sql(
            "SELECT status, COUNT(*) FROM `tabCortex Rental Invoice` WHERE company=%s GROUP BY status", COMPANY
        )
    )
    out["total_facture"] = float(
        q("SELECT COALESCE(SUM(total),0) FROM `tabCortex Rental Invoice` WHERE company=%s AND status<>'Cancelled'")
    )
    out["total_encaisse"] = float(
        q("SELECT COALESCE(SUM(signed_amount),0) FROM `tabCortex Rental Payment` WHERE company=%s")
    )
    out["solde_a_recevoir"] = float(
        q("SELECT COALESCE(SUM(balance),0) FROM `tabCortex Rental Invoice` WHERE company=%s AND status<>'Cancelled'")
    )
    out["tps_percue"] = float(
        q("SELECT COALESCE(SUM(tps_amount),0) FROM `tabCortex Rental Invoice` WHERE company=%s AND status<>'Cancelled'")
    )
    out["tvq_percue"] = float(
        q("SELECT COALESCE(SUM(tvq_amount),0) FROM `tabCortex Rental Invoice` WHERE company=%s AND status<>'Cancelled'")
    )
    out["solde_incoherent"] = q(
        "SELECT COUNT(*) FROM `tabCortex Rental Invoice` WHERE company=%s AND status<>'Cancelled' AND ABS(balance - (total - amount_paid)) > 0.01"
    )
    out["paye_incoherent"] = q(
        """SELECT COUNT(*) FROM `tabCortex Rental Invoice` i WHERE i.company=%s AND ABS(i.amount_paid - COALESCE((SELECT SUM(signed_amount) FROM `tabCortex Rental Payment` p WHERE p.invoice=i.name),0)) > 0.01"""
    )
    out["taxes_incoherentes"] = q(
        "SELECT COUNT(*) FROM `tabCortex Rental Invoice` WHERE company=%s AND (ABS(tax_amount - (tps_amount + tvq_amount)) > 0.01 OR ABS(total - (subtotal + tax_amount)) > 0.01 OR ABS(tps_amount - ROUND(subtotal*0.05,2)) > 0.011 OR ABS(tvq_amount - ROUND(subtotal*0.09975,2)) > 0.011)"
    )
    out["locations_totaux_incoherents"] = q(
        "SELECT COUNT(*) FROM `tabCortex Rental Transaction` WHERE company=%s AND ABS(grand_total - (subtotal + tps_amount + tvq_amount)) > 0.01"
    )
    out["closes_sans_facture_finale"] = q(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction` t WHERE t.company=%s AND t.rental_state='Closed' AND t.subtotal > 0
           AND NOT EXISTS (SELECT 1 FROM `tabCortex Rental Invoice` i WHERE i.rental_transaction=t.name AND i.invoice_type='Final' AND i.status<>'Cancelled')"""
    )
    out["reservees_sans_acompte"] = q(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction` t WHERE t.company=%s AND t.rental_state IN ('Reservation','Contract','Checked Out','Returned','Closed') AND t.subtotal > 0
           AND NOT EXISTS (SELECT 1 FROM `tabCortex Rental Invoice` i WHERE i.rental_transaction=t.name AND i.invoice_type='Deposit' AND i.status<>'Cancelled')"""
    )
    out["rapprochement_acompte_final_vs_location"] = q(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction` t WHERE t.company=%s AND t.rental_state='Closed' AND t.subtotal > 0 AND ABS(
             (SELECT COALESCE(SUM(i.total),0) FROM `tabCortex Rental Invoice` i WHERE i.rental_transaction=t.name AND i.status<>'Cancelled')
             - t.grand_total - COALESCE((SELECT SUM(l.amount)*1.14975 FROM `tabCortex Rental Invoice Line` l JOIN `tabCortex Rental Invoice` i ON i.name=l.parent WHERE i.rental_transaction=t.name AND i.invoice_type='Final' AND l.description LIKE 'Frais de retard%%'),0)) > 0.06"""
    )
    out["frais_de_retard_factures"] = float(
        q(
            "SELECT COALESCE(SUM(l.amount),0) FROM `tabCortex Rental Invoice Line` l JOIN `tabCortex Rental Invoice` i ON i.name=l.parent WHERE i.company=%s AND l.description LIKE 'Frais de retard%%'"
        )
    )
    out["factures_en_retard_de_paiement"] = q(
        "SELECT COUNT(*) FROM `tabCortex Rental Invoice` WHERE company=%s AND status IN ('Issued','Partially Paid') AND due_date < CURDATE()"
    )
    return out


def integrity():
    frappe.set_user("Administrator")
    findings = {}
    rows = frappe.get_all(
        "Cortex Rental Transaction",
        filters={"company": COMPANY},
        fields=[
            "name",
            "rental_state",
            "starts_at",
            "ends_at",
            "grand_total",
            "subtotal",
            "billable_days",
            "calendar_days",
            "customer_account_ready",
        ],
        limit_page_length=100000,
    )
    findings["transactions_total"] = len(rows)
    findings["par_etat"] = dict(Counter(r.rental_state for r in rows))
    findings["totaux_a_zero"] = sum(1 for r in rows if not r.grand_total)
    findings["jours_factures_a_zero"] = sum(1 for r in rows if not r.billable_days)
    # 1. surréservation jour par jour
    lines = frappe.db.sql(
        """SELECT t.name, t.rental_state, t.starts_at, t.ends_at, i.item_code, i.qty
           FROM `tabCortex Rental Transaction Item` i JOIN `tabCortex Rental Transaction` t ON t.name=i.parent
           WHERE t.company=%s AND t.rental_state IN ('Reservation','Contract','Checked Out')""",
        COMPANY,
        as_dict=True,
    )
    fleet = {}
    for p in frappe.get_all(
        "Cortex Rental Item Profile",
        filters={"company": COMPANY},
        fields=["item_code", "is_serialized", "total_quantity"],
    ):
        if p.is_serialized:
            fleet[p.item_code] = frappe.db.count("Serial No", {"item_code": p.item_code, "company": COMPANY})
        else:
            fleet[p.item_code] = p.total_quantity
    # Balayage à la minute : à égalité, les fins passent avant les débuts (un retour à 9 h libère l'unité pour un départ à 9 h).
    by_item = defaultdict(list)
    for line in lines:
        by_item[line.item_code].append(line)
    over = []
    for code, rows_for_item in by_item.items():
        events = []
        for line in rows_for_item:
            events.append((line.starts_at, 1, line.qty))
            events.append((line.ends_at, 0, -line.qty))
        events.sort(key=lambda e: (e[0], e[1]))
        current = 0
        for moment, _kind, qty in events:
            current += qty
            if current > (fleet.get(code) or 0):
                over.append(((code, moment.date()), current, fleet.get(code)))
                break
    findings["surreservations_jour_article"] = len(over)
    findings["surreservations_exemples"] = [(k[0], str(k[1]), v, f) for k, v, f in over[:5]]
    # 2. états incohérents
    findings["sortis_sans_scan"] = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction Item` i JOIN `tabCortex Rental Transaction` t ON t.name=i.parent
           WHERE t.company=%s AND t.rental_state IN ('Checked Out','Returned','Closed') AND i.assigned_serials IS NOT NULL
             AND i.assigned_serials NOT IN ('', '[]') AND (i.scanned_checkout_serials IS NULL OR i.scanned_checkout_serials IN ('', '[]'))""",
        COMPANY,
    )[0][0]
    findings["retours_depassant_quantite"] = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction Item` i JOIN `tabCortex Rental Transaction` t ON t.name=i.parent
           WHERE t.company=%s AND i.returned_qty > i.qty""",
        COMPANY,
    )[0][0]
    findings["retours_partiels_ou_nuls_apres_retour"] = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabCortex Rental Transaction Item` i JOIN `tabCortex Rental Transaction` t ON t.name=i.parent
           WHERE t.company=%s AND t.rental_state IN ('Returned','Closed') AND i.returned_qty < i.qty""",
        COMPANY,
    )[0][0]
    # 3. approbations et audit
    findings["approbations"] = dict(
        frappe.db.sql("SELECT status, COUNT(*) FROM `tabApproval Request` WHERE company=%s GROUP BY status", COMPANY)
    )
    findings["evenements_audit"] = frappe.db.count("Audit Event", {"company": COMPANY})
    findings["series_par_statut"] = dict(
        frappe.db.sql(
            "SELECT cortex_status, COUNT(*) FROM `tabSerial No` WHERE company=%s GROUP BY cortex_status", COMPANY
        )
    )
    findings["devis_erpnext"] = frappe.db.count("Quotation", {"company": COMPANY})
    findings["commandes_client"] = frappe.db.count("Sales Order", {"company": COMPANY})
    findings["factures_vente"] = frappe.db.count("Sales Invoice", {"company": COMPANY})
    findings["versements_consignation"] = frappe.db.count("Consignment Payout", {"company": COMPANY})
    findings["finance"] = finance_integrity()
    findings["taxes_calculees"] = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabCortex Rental Transaction` WHERE company=%s AND tax_amount > 0", COMPANY
    )[0][0]
    sizes = frappe.db.sql(
        """SELECT table_name, table_rows, ROUND((data_length+index_length)/1024/1024,2)
           FROM information_schema.tables WHERE table_schema=DATABASE()
           AND table_name IN ('tabCortex Rental Transaction','tabCortex Rental Transaction Item','tabAudit Event','tabApproval Request','tabSales Order','tabQuotation','tabVersion','tabComment','tabActivity Log')"""
    )
    findings["tables"] = {r[0]: {"lignes": r[1], "mo": float(r[2])} for r in sizes}
    return findings


def purge():
    """Remove the simulation's business records (not its company, people, catalogue or customers)."""
    frappe.set_user("Administrator")
    names = frappe.get_all("Cortex Rental Transaction", filters={"company": COMPANY}, pluck="name")
    for table in ("Cortex Rental Transaction Item",):
        frappe.db.sql(
            f"DELETE i FROM `tab{table}` i JOIN `tabCortex Rental Transaction` t ON t.name = i.parent WHERE t.company = %s",
            COMPANY,
        )
    for doctype in ("Cortex Check-In Item",):
        frappe.db.sql(
            f"DELETE i FROM `tab{doctype}` i JOIN `tabCortex Check-In` c ON c.name = i.parent WHERE c.company = %s",
            COMPANY,
        )
    frappe.db.sql(
        "DELETE l FROM `tabCortex Rental Invoice Line` l JOIN `tabCortex Rental Invoice` i ON i.name = l.parent WHERE i.company = %s",
        COMPANY,
    )
    for doctype in (
        "Cortex Rental Payment",
        "Cortex Rental Invoice",
        "Cortex Check-In",
        "Cortex Rental Transaction",
        "Approval Request",
        "Audit Event",
        "Cortex Idempotency Record",
        "Consignment Payout",
    ):
        frappe.db.delete(doctype, {"company": COMPANY})
    frappe.db.sql("UPDATE `tabSerial No` SET cortex_status='Active' WHERE company=%s", COMPANY)
    for doctype, field in (("Quotation", "company"), ("Sales Order", "company")):
        for name in frappe.get_all(doctype, filters={field: COMPANY, "docstatus": ["<", 2]}, pluck="name"):
            try:
                doc = frappe.get_doc(doctype, name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
            except Exception:
                pass
    frappe.db.commit()
    log(f"Données de simulation purgées ({len(names)} locations)")


def run(seed=2026, days=90, reset=0):
    open(LOG_PATH, "w").close()
    if int(reset):
        purge()
    started = time.perf_counter()
    provision()
    per_day = simulate(int(seed), int(days))
    summary = {
        "duree_s": round(time.perf_counter() - started, 1),
        "evenements": dict(EVENTS),
        "erreurs": dict(ERRORS),
        "exemples_erreurs": ERROR_SAMPLES,
        "latences_ms": {
            k: {"n": len(v), "p50": percentile(v, 0.5), "p95": percentile(v, 0.95), "max": round(max(v), 1)}
            for k, v in sorted(STATE_TIMES.items())
        },
        "jours_simules": len(per_day),
        "temps_par_jour_s": {
            "moyen": round(statistics.mean(d[2] for d in per_day), 2),
            "max": max(d[2] for d in per_day),
        },
        "integrite": integrity(),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, default=str)
    log(f"Terminé en {summary['duree_s']} s. Métriques : {METRICS_PATH}")
    return summary
