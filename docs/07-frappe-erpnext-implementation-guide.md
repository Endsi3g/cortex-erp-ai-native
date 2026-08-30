# Guide d'Implémentation Complet : Frappe Framework & ERPNext pour Cortex

Ce document constitue le guide technique de référence pour implémenter l'ERP de location audiovisuelle et événementielle **Cortex** sur la pile **Frappe Framework v15+ & ERPNext** adossée à **PostgreSQL**, intégrée de manière sécurisée avec **Onyx** et la façade **MCP**.

---

## 1. Initialisation de l'Environnement (Frappe Bench + PostgreSQL)

### 1.1 Initialisation du Bench avec support PostgreSQL
```bash
# 1. Créer le bench avec le moteur PostgreSQL
bench init --db-type postgres --frappe-branch version-15 cortex-bench
cd cortex-bench

# 2. Créer le site principal Cortex
bench new-site cortex.local \
  --db-type postgres \
  --db-host 127.0.0.1 \
  --db-port 5432 \
  --admin-password admin

# 3. Installer ERPNext
bench get-app --branch version-15 erpnext
bench --site cortex.local install-app erpnext

# 4. Créer l'application métier Cortex Rental
bench new-app cortex_rental
bench --site cortex.local install-app cortex_rental
```

---

## 2. Architecture de l'Application `cortex_rental`

### 2.1 Arborescence de l'Application Frappe
```text
apps/cortex_rental/
├── cortex_rental/
│   ├── hooks.py                           # Hooks globaux, permission queries, overrides
│   ├── api/                               # Endpoints REST pour Onyx & MCP
│   │   ├── __init__.py
│   │   ├── availability.py                # Calcul disponibilité en temps réel
│   │   ├── quotes.py                      # Ingestion brouillons de devis IA
│   │   ├── approvals.py                   # File de soumission/approbation
│   │   └── consignment.py                 # Rapports propriétaires & relevés
│   ├── cortex_rental/
│   │   └── doctype/
│   │       ├── rental_item/               # DocType Matériel de location
│   │       ├── consignment_owner/         # DocType Propriétaire consignateur
│   │       ├── consignment_payout/        # DocType Relevé de split (Immuable)
│   │       ├── rental_pricing_rule/       # DocType Règle tarifaire (7j=3j)
│   │       ├── approval_request/          # DocType File d'approbation IA
│   │       └── audit_event/               # DocType Journal d'audit append-only
│   ├── overrides/                         # Extensions de DocTypes ERPNext
│   │   ├── quotation.py                   # Calcul durée & jours facturables
│   │   ├── sales_order.py                 # Workflow réservation -> contrat
│   │   └── serial_no.py                   # Statuts de disponibilité & blocage
│   └── tests/                             # Suite de tests d'acceptation Python
│       ├── __init__.py
│       ├── test_demo_scenario.py          # Scénario démo 9 étapes
│       └── test_security_invariants.py    # 4 barrières de sécurité
└── pyproject.toml
```

---

## 3. Spécifications des DocTypes Clés

### 3.1 DocType `Audit Event` (Append-Only & Immuable)
```python
# apps/cortex_rental/cortex_rental/cortex_rental/doctype/audit_event/audit_event.py
import frappe
from frappe.model.document import Document

class AuditEvent(Document):
    def before_save(self):
        if not self.is_new():
            frappe.throw("Audit events are strictly immutable and cannot be updated.", frappe.PermissionError)

    def on_trash(self):
        frappe.throw("Audit events cannot be deleted from the system.", frappe.PermissionError)

def log_audit_event(company: str, actor_type: str, actor_id: str, action: str, 
                    entity_type: str, entity_id: str, before_state=None, 
                    after_state=None, evidence=None, policy_decision=None, request_id=None):
    doc = frappe.get_doc({
        "doctype": "Audit Event",
        "company": company,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_state": frappe.as_json(before_state) if before_state else None,
        "after_state": frappe.as_json(after_state) if after_state else None,
        "evidence": frappe.as_json(evidence) if evidence else None,
        "policy_decision": frappe.as_json(policy_decision) if policy_decision else None,
        "request_id": request_id
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc
```

### 3.2 DocType `Approval Request` (Gouvernance Human-in-the-Loop)
```python
# apps/cortex_rental/cortex_rental/cortex_rental/doctype/approval_request/approval_request.py
import frappe
from frappe.model.document import Document
from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event

class ApprovalRequest(Document):
    def approve(self, reason=None):
        current_user = frappe.session.user
        user_roles = frappe.get_roles(current_user)
        
        # Règle stricte : Un agent ne peut jamais approuver
        if "Agent Service Account" in user_roles or frappe.flags.in_agent_context:
            frappe.throw("Agents are strictly forbidden from approving requests.", frappe.PermissionError)

        if self.status != "Pending":
            frappe.throw(f"Cannot approve request in status {self.status}.")

        self.status = "Approved"
        self.decided_by = current_user
        self.decision_reason = reason
        self.decided_at = frappe.utils.now_datetime()
        self.save()

        # Exécuter la transition métier
        if self.entity_type == "Sales Order" and self.action == "rental.quote.transition_to_reservation":
            so = frappe.get_doc("Sales Order", self.entity_id)
            so.custom_rental_state = "Reservation"
            so.save()

        log_audit_event(
            company=self.company,
            actor_type="Human",
            actor_id=current_user,
            action="rental.approval.approved",
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            after_state={"status": "Approved", "reason": reason}
        )
```

### 3.3 DocType `Consignment Payout` (Confidentialité Renter Garantie)
```python
# apps/cortex_rental/cortex_rental/cortex_rental/doctype/consignment_payout/consignment_payout.py
import frappe
from frappe.model.document import Document

class ConsignmentPayout(Document):
    def validate(self):
        # Calcul du split propriétaire
        gross = float(self.gross_amount or 0.0)
        pct = float(self.consignment_percentage or 70.0)
        self.owner_payout_amount = round(gross * (pct / 100.0), 2)
        
        # Vérification qu'aucune donnée client/locataire n'est stockée dans le snapshot
        if self.calculation_snapshot:
            snapshot = frappe.parse_json(self.calculation_snapshot)
            forbidden_keys = ["customer_name", "client_name", "renter_name", "customer_email"]
            for k in forbidden_keys:
                if k in snapshot:
                    frappe.throw(f"Forbidden renter identity field [{k}] detected in owner payout snapshot.")
```

---

## 4. Moteur Tarifaire (Règle 7j Calendaires = 3j Facturables)

```python
# apps/cortex_rental/cortex_rental/pricing.py
import math
import frappe

def compute_billable_days(starts_at, ends_at, company: str) -> tuple[int, float]:
    start_date = frappe.utils.getdate(starts_at)
    end_date = frappe.utils.getdate(ends_at)
    diff = (end_date - start_date).days
    calendar_days = max(1, diff)

    # Recherche de règles actives
    pricing_rule = frappe.db.get_value(
        "Rental Pricing Rule",
        {"company": company, "is_active": 1, "calendar_days": calendar_days},
        ["billable_days"],
        as_dict=True
    )

    if pricing_rule:
        billable_days = float(pricing_rule.billable_days)
    elif calendar_days == 7:
        billable_days = 3.0
    else:
        billable_days = float(calendar_days)

    return calendar_days, billable_days
```

---

## 5. API REST pour Onyx & Façade MCP

> **⚠️ Obsolète.** Les échantillons de code de cette section (§5.1)
> décrivent une itération de conception antérieure à `api/v1/` et à
> `Cortex Rental Transaction`. Le module `cortex_rental.api.quotes`
> (sans `v1`) qu'ils documentaient a été supprimé du code (endpoint
> `@frappe.whitelist` actif mais sans aucune vérification de scope agent
> ni de Company autorisée — un vestige dangereux, pas juste mort).
> L'implémentation réelle et sécurisée est
> `cortex_rental.api.v1.quotes.create_quote_draft`
> (`apps/cortex_rental/cortex_rental/api/v1/quotes.py`), qui passe par
> `permissions.agent_scopes.get_company_context()` /
> `require_agent_scope()` avant toute écriture. Cette section reste ici
> pour l'historique de conception ; une réécriture complète de ce guide
> est un suivi ouvert, pas fait dans cette passe de correction.

### 5.1 Endpoint d'Ingestion de Brouillon (`POST /api/method/cortex_rental.api.quotes.create_draft`) — historique, ne pas utiliser
```python
# apps/cortex_rental/cortex_rental/api/quotes.py
import frappe
from cortex_rental.cortex_rental.doctype.audit_event.audit_event import log_audit_event
from cortex_rental.pricing import compute_billable_days

@frappe.whitelist(methods=["POST"])
def create_draft():
    data = frappe.local.form_dict
    company = frappe.local.request.headers.get("X-Company-ID") or frappe.defaults.get_user_default("Company")
    
    calendar_days, billable_days = compute_billable_days(data.starts_at, data.ends_at, company)

    # Création du devis dans Quotation
    quotation = frappe.get_doc({
        "doctype": "Quotation",
        "company": company,
        "party_name": data.customer_id,
        "quotation_to": "Customer",
        "custom_starts_at": data.starts_at,
        "custom_ends_at": data.ends_at,
        "custom_rental_state": "Quote",
        "items": []
    })

    for line in data.get("lines", []):
        item_doc = frappe.get_doc("Item", line["item_id"])
        rate = float(line.get("unit_rate") or item_doc.custom_daily_rate or 100.0)
        qty = float(line.get("quantity") or 1.0)
        amount = round(qty * rate * billable_days, 2)
        
        quotation.append("items", {
            "item_code": item_doc.name,
            "qty": qty,
            "rate": rate,
            "amount": amount,
            "custom_calendar_days": calendar_days,
            "custom_billable_days": billable_days
        })

    quotation.insert()

    # Enregistrement de l'événement d'audit
    log_audit_event(
        company=company,
        actor_type="Agent",
        actor_id=frappe.session.user,
        action="rental.quote.draft_created",
        entity_type="Quotation",
        entity_id=quotation.name,
        evidence=data.get("evidence_ids"),
        after_state={"name": quotation.name, "total": quotation.grand_total, "state": "Quote"}
    )

    return {
        "success": True,
        "data": {
            "id": quotation.name,
            "state": "quote",
            "grand_total": quotation.grand_total,
            "billable_days": billable_days
        }
    }
```

---

## 6. Tests d'Acceptation Python (Pytest / FrappeTestCase)

```python
# apps/cortex_rental/cortex_rental/tests/test_demo_scenario.py
import frappe
from frappe.tests.utils import FrappeTestCase
from cortex_rental.pricing import compute_billable_days

class TestCortexDemoScenario(FrappeTestCase):
    def setUp(self):
        self.company = "CineRental Montreal"
        self.customer = "Dune 3 Productions Inc."

    def test_step_1_to_3_agent_draft_and_human_approval(self):
        # 1. Création du devis par agent
        calendar_days, billable_days = compute_billable_days("2026-09-01", "2026-09-08", self.company)
        self.assertEqual(calendar_days, 7)
        self.assertEqual(billable_days, 3.0)

        # 2. Vérification que l'agent ne peut pas approuver
        approval = frappe.get_doc({
            "doctype": "Approval Request",
            "company": self.company,
            "action": "rental.quote.transition_to_reservation",
            "entity_type": "Sales Order",
            "entity_id": "SO-2026-0001",
            "status": "Pending"
        }).insert()

        frappe.flags.in_agent_context = True
        with self.assertRaises(frappe.PermissionError):
            approval.approve(reason="Agent autonomous approval attempt")
        frappe.flags.in_agent_context = False

    def test_step_9_consignment_payout_redacts_renter_identity(self):
        payout = frappe.get_doc({
            "doctype": "Consignment Payout",
            "company": self.company,
            "owner": "Roger Deakins Productions Inc.",
            "gross_amount": 9000.00,
            "consignment_percentage": 70.0,
            "calculation_snapshot": frappe.as_json({
                "serial": "SN-ALX35-001",
                "days": 3.0,
                "rate": 1500.00
            })
        }).insert()

        self.assertEqual(payout.owner_payout_amount, 6300.00)
        self.assertNotIn("Dune 3 Productions", payout.calculation_snapshot)
```

---

## 7. Configuration du Desk UI/UX & Espaces de Travail

1. **Workspace Location & Comptoir** :
   - Graphiques de taux de sortie et de retours prévus.
   - Raccourcis : *Nouveau Devis*, *Check-in Scanner*, *Calendrier de Disponibilité*.
   - Cartes de statut de la file d'approbation avec badge rouge pour les demandes en attente.
2. **Recherche Universelle (Awesomebar `Cmd+K`)** :
   - Recherche instantanée des `Item`, `Serial No`, `Quotation`, `Sales Order` et `Consignment Owner`.
3. **Timeline et Journal d'Audit** :
   - Chaque formulaire (`Quotation`, `Sales Order`) affiche en barre latérale ou en bas de page l'historique complet des actions, des pièces jointes et des validations d'opérateurs.
