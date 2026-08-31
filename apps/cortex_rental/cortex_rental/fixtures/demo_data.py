# Copyright (c) 2026, Cortex Rental and contributors
# For license information, please see license.txt

"""
Demo data provisioner for Cortex ERP AI-Native.
Creates a complete, rich rental environment (Company, Customer, serialized fleet,
pricing rules, and transactions in all lifecycle states) for immediate demo capability.
"""

from typing import Any, Dict, List
import datetime

try:
    import frappe
    from frappe.utils import add_days, now_datetime
except ImportError:
    frappe = None  # type: ignore
    add_days = None  # type: ignore
    now_datetime = None  # type: ignore


COMPANY_NAME = "Cortex Cinema Rentals"
CUSTOMER_NAME = "Dune 3 Productions"
CURRENCY = "USD"


def provision_demo_data() -> Dict[str, Any]:
    """
    Idempotently sets up demo fixtures in the active Frappe bench site.
    Can be run via: `bench --site <site> execute cortex_rental.fixtures.demo_data.provision_demo_data`
    """
    if not frappe:
        return {"status": "skipped", "message": "Frappe environment not available"}

    frappe.set_user("Administrator")
    print(f"[*] Provisioning Cortex Demo Data for company: [{COMPANY_NAME}]...")

    # 1. Company
    company = _ensure_company()

    # 2. Customer
    customer = _ensure_customer()

    # 3. Item Profiles & Serial Fleet
    items = _ensure_items_and_serials(company)

    # 4. Pricing Rules
    _ensure_pricing_rules(company)

    # 5. Transactions across states (Checked Out, Reservation, Quote, Returned)
    transactions = _ensure_transactions(company, customer, items)

    frappe.db.commit()
    print("[✓] Demo fixtures provisioned successfully!")

    return {
        "status": "success",
        "company": company,
        "customer": customer,
        "items_count": len(items),
        "transactions_created": len(transactions),
    }


def _ensure_company() -> str:
    if not frappe.db.exists("Company", COMPANY_NAME):
        doc = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": COMPANY_NAME,
                "abbr": "CCR",
                "default_currency": CURRENCY,
                "country": "United States",
            }
        )
        doc.insert(ignore_permissions=True)
        print(f"  + Created Company: {COMPANY_NAME}")
    return COMPANY_NAME


def _ensure_customer() -> str:
    cust_id = None
    existing = frappe.get_all("Customer", filters={"customer_name": CUSTOMER_NAME}, limit=1)
    if existing:
        cust_id = existing[0].name
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": CUSTOMER_NAME,
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
                "cortex_account_status": "Approved",
                "cortex_insurance_status": "Valid",
                "cortex_credit_limit": 50000.0,
                "cortex_deposit_balance": 5000.0,
            }
        )
        doc.insert(ignore_permissions=True)
        cust_id = doc.name
        print(f"  + Created Customer: {CUSTOMER_NAME} ({cust_id})")

    return cust_id


def _ensure_items_and_serials(company: str) -> List[Dict[str, Any]]:
    catalog = [
        {
            "item_code": "ARRI-ALX35",
            "item_name": "ARRI Alexa 35 Camera Body",
            "category": "Camera",
            "is_serialized": 1,
            "daily_rate": 1500.0,
            "weekly_rate": 4500.0,
            "monthly_rate": 13500.0,
            "insurance_value": 75000.0,
            "serials": ["SN-ALX-001", "SN-ALX-002", "SN-ALX-003"],
        },
        {
            "item_code": "COOKE-S4I-SET",
            "item_name": "Cooke S4/i Prime Lens Set (5-Lens)",
            "category": "Optics",
            "is_serialized": 1,
            "daily_rate": 800.0,
            "weekly_rate": 2400.0,
            "monthly_rate": 7200.0,
            "insurance_value": 45000.0,
            "serials": ["SN-CKE-001", "SN-CKE-002"],
        },
        {
            "item_code": "APUTURE-1200D",
            "item_name": "Aputure Electro Storm 1200d Pro Light",
            "category": "Lighting",
            "is_serialized": 1,
            "daily_rate": 250.0,
            "weekly_rate": 750.0,
            "monthly_rate": 2250.0,
            "insurance_value": 6000.0,
            "serials": ["SN-APT-001", "SN-APT-002", "SN-APT-003", "SN-APT-004"],
        },
        {
            "item_code": "BNC-50FT",
            "item_name": "BNC 12G-SDI Video Cable 50ft",
            "category": "Grip & Cables",
            "is_serialized": 0,
            "total_quantity": 20,
            "daily_rate": 15.0,
            "weekly_rate": 45.0,
            "monthly_rate": 135.0,
            "insurance_value": 80.0,
            "serials": [],
        },
        {
            "item_code": "C-STAND-40",
            "item_name": 'Avenger C-Stand 40" with Grip Arm',
            "category": "Grip & Cables",
            "is_serialized": 0,
            "total_quantity": 15,
            "daily_rate": 20.0,
            "weekly_rate": 60.0,
            "monthly_rate": 180.0,
            "insurance_value": 220.0,
            "serials": [],
        },
    ]

    for item in catalog:
        # 1. Base Item
        if not frappe.db.exists("Item", item["item_code"]):
            doc = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item["item_code"],
                    "item_name": item["item_name"],
                    "item_group": "All Item Groups",
                    "stock_uom": "Unit" if item["is_serialized"] else "Nos",
                    "is_stock_item": 0,
                }
            )
            doc.insert(ignore_permissions=True)

        # 2. Cortex Rental Item Profile
        profile_name = frappe.db.get_value("Cortex Rental Item Profile", {"item_code": item["item_code"]}, "name")
        if not profile_name:
            doc_profile = frappe.get_doc(
                {
                    "doctype": "Cortex Rental Item Profile",
                    "item_code": item["item_code"],
                    "item_name": item["item_name"],
                    "is_rental": 1,
                    "is_serialized": item["is_serialized"],
                    "total_quantity": item.get("total_quantity") or len(item["serials"]),
                    "daily_rate": item["daily_rate"],
                    "weekly_rate": item["weekly_rate"],
                    "monthly_rate": item["monthly_rate"],
                    "insurance_value": item["insurance_value"],
                }
            )
            doc_profile.insert(ignore_permissions=True)
            print(f"  + Created Rental Profile: {item['item_code']}")

        # 3. Serial Numbers
        for sn in item["serials"]:
            if not frappe.db.exists("Serial No", sn):
                doc_sn = frappe.get_doc(
                    {
                        "doctype": "Serial No",
                        "serial_no": sn,
                        "item_code": item["item_code"],
                        "company": company,
                        "cortex_status": "Active",
                        "cortex_ownership": "Owned",
                    }
                )
                doc_sn.insert(ignore_permissions=True)
                print(f"    - Created Serial: {sn}")

    return catalog


def _ensure_pricing_rules(company: str) -> None:
    rule_name = "RULE-7DAY-3DAY"
    existing = frappe.db.get_value("Rental Pricing Rule", {"company": company, "rule_name": "7 Days for 3"}, "name")
    if not existing:
        doc = frappe.get_doc(
            {
                "doctype": "Rental Pricing Rule",
                "company": company,
                "rule_name": "7 Days for 3",
                "min_days": 7,
                "billable_multiplier": 3.0 / 7.0,
                "is_active": 1,
            }
        )
        doc.insert(ignore_permissions=True)
        print("  + Created Pricing Rule: 7 Days for 3")


def _ensure_transactions(company: str, customer: str, items: List[Dict[str, Any]]) -> List[str]:
    now = now_datetime() if now_datetime else datetime.datetime.now()
    created_txns = []

    # 1. Transaction CHECKED OUT (for Check-in Scanner Demo)
    t1_id = "CRX-TXN-DEMO-001"
    if not frappe.db.exists("Cortex Rental Transaction", t1_id):
        t1 = frappe.get_doc(
            {
                "doctype": "Cortex Rental Transaction",
                "name": t1_id,
                "company": company,
                "customer": customer,
                "customer_name": CUSTOMER_NAME,
                "rental_state": "Checked Out",
                "starts_at": add_days(now, -3) if add_days else now,
                "ends_at": now,
                "currency": CURRENCY,
                "notes": "Sortie plateau tournage Studio A — En attente de retour et contrôle technique.",
                "items": [
                    {
                        "item_code": "ARRI-ALX35",
                        "item_name": "ARRI Alexa 35 Camera Body",
                        "serial_no": "SN-ALX-001",
                        "qty": 1.0,
                        "returned_qty": 0.0,
                        "rate": 1500.0,
                        "amount": 4500.0,
                    },
                    {
                        "item_code": "COOKE-S4I-SET",
                        "item_name": "Cooke S4/i Prime Lens Set (5-Lens)",
                        "serial_no": "SN-CKE-001",
                        "qty": 1.0,
                        "returned_qty": 0.0,
                        "rate": 800.0,
                        "amount": 2400.0,
                    },
                    {
                        "item_code": "BNC-50FT",
                        "item_name": "BNC 12G-SDI Video Cable 50ft",
                        "qty": 4.0,
                        "returned_qty": 0.0,
                        "rate": 15.0,
                        "amount": 180.0,
                    },
                ],
            }
        )
        t1.flags.ignore_validate = True
        t1.insert(ignore_permissions=True)
        created_txns.append(t1.name)
        print(f"  + Created Checked Out Transaction: {t1.name}")

    # 2. Transaction RESERVATION (for Availability Grid Demo)
    t2_id = "CRX-TXN-DEMO-002"
    if not frappe.db.exists("Cortex Rental Transaction", t2_id):
        t2 = frappe.get_doc(
            {
                "doctype": "Cortex Rental Transaction",
                "name": t2_id,
                "company": company,
                "customer": customer,
                "customer_name": CUSTOMER_NAME,
                "rental_state": "Reservation",
                "starts_at": add_days(now, 2) if add_days else now,
                "ends_at": add_days(now, 6) if add_days else now,
                "currency": CURRENCY,
                "notes": "Réservation confirmée pour tournage extérieur désert.",
                "items": [
                    {
                        "item_code": "ARRI-ALX35",
                        "item_name": "ARRI Alexa 35 Camera Body",
                        "serial_no": "SN-ALX-002",
                        "qty": 1.0,
                        "returned_qty": 0.0,
                        "rate": 1500.0,
                        "amount": 6000.0,
                    },
                    {
                        "item_code": "APUTURE-1200D",
                        "item_name": "Aputure Electro Storm 1200d Pro Light",
                        "serial_no": "SN-APT-001",
                        "qty": 1.0,
                        "returned_qty": 0.0,
                        "rate": 250.0,
                        "amount": 1000.0,
                    },
                ],
            }
        )
        t2.flags.ignore_validate = True
        t2.insert(ignore_permissions=True)
        created_txns.append(t2.name)
        print(f"  + Created Reservation Transaction: {t2.name}")

    # 3. Transaction QUOTE (for Composer Demo)
    t3_id = "CRX-TXN-DEMO-003"
    if not frappe.db.exists("Cortex Rental Transaction", t3_id):
        t3 = frappe.get_doc(
            {
                "doctype": "Cortex Rental Transaction",
                "name": t3_id,
                "company": company,
                "customer": customer,
                "customer_name": CUSTOMER_NAME,
                "rental_state": "Quote",
                "starts_at": add_days(now, 10) if add_days else now,
                "ends_at": add_days(now, 17) if add_days else now,
                "currency": CURRENCY,
                "notes": "Devis estimatif pour seconde équipe.",
                "items": [
                    {
                        "item_code": "APUTURE-1200D",
                        "item_name": "Aputure Electro Storm 1200d Pro Light",
                        "qty": 2.0,
                        "returned_qty": 0.0,
                        "rate": 250.0,
                        "amount": 1500.0,
                    },
                ],
            }
        )
        t3.flags.ignore_validate = True
        t3.insert(ignore_permissions=True)
        created_txns.append(t3.name)
        print(f"  + Created Quote Transaction: {t3.name}")

    return created_txns
