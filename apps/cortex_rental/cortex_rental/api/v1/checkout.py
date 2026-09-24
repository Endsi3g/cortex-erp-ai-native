"""Human-operated, tenant-scoped equipment release workflow."""

import json

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role


def _transaction(name, company):
    doc = frappe.get_doc("Cortex Rental Transaction", name)
    if doc.company != company:
        frappe.throw("Rental transaction is unavailable for the active company.", frappe.PermissionError)
    return doc


def _array(value):
    if isinstance(value, list):
        return value
    try:
        return json.loads(value or "[]")
    except (TypeError, ValueError):
        return []


if frappe:
    @frappe.whitelist(methods=["POST"])
    def record_checkout_scan():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        doc = _transaction(payload.get("rental_id"), company)
        if doc.rental_state != "Contract":
            frappe.throw("Only an approved Contract can be checked out.", frappe.ValidationError)
        serial = (payload.get("serial_number") or "").strip()
        serial_doc = frappe.db.get_value("Serial No", serial, ["name", "item_code", "company", "cortex_status"], as_dict=True)
        if not serial_doc or (serial_doc.company and serial_doc.company != company) or (serial_doc.cortex_status or "Active") != "Active":
            frappe.throw("This serial number is missing, belongs to another company, or is not available.", frappe.ValidationError)
        row = next((line for line in doc.items if serial in _array(line.assigned_serials)), None)
        if not row or row.item_code != serial_doc.item_code:
            frappe.throw("This serial number is not allocated to this rental contract.", frappe.ValidationError)
        scanned = _array(row.scanned_checkout_serials)
        if serial in scanned:
            frappe.throw("This serial number has already been scanned for this checkout.", frappe.ValidationError)
        scanned.append(serial)
        row.scanned_checkout_serials = frappe.as_json(scanned)
        doc.save()
        return {"request_id": frappe.generate_hash(length=16), "entity_id": doc.name,
            "status": "completed", "approval_required": False, "mutation_performed": True}

    @frappe.whitelist(methods=["POST"])
    def complete_checkout():
        require_human_staff_role()
        company = get_company_context()
        payload = frappe.local.form_dict
        doc = _transaction(payload.get("rental_id"), company)
        if doc.rental_state != "Contract":
            frappe.throw("Only an approved Contract can be checked out.", frappe.ValidationError)
        missing = []
        for row in doc.items:
            assigned = set(_array(row.assigned_serials))
            scanned = set(_array(row.scanned_checkout_serials))
            profile = frappe.db.get_value("Cortex Rental Item Profile", {"company": company, "item_code": row.item_code}, "is_serialized")
            if profile and assigned and (scanned != assigned or len(assigned) != int(float(row.qty or 0))):
                missing.extend(sorted(assigned - scanned))
            elif profile and not assigned:
                frappe.throw(f"No physical serial allocation exists for {row.item_code}; return the contract to the rental manager.", frappe.ValidationError)
        if missing:
            frappe.throw("Scan every allocated unit before completing checkout: " + ", ".join(missing), frappe.ValidationError)
        doc.transition_to("Checked Out", reason="Warehouse checkout completed by authorized staff")
        return {"request_id": frappe.generate_hash(length=16), "entity_id": doc.name,
            "status": "completed", "approval_required": False, "mutation_performed": True}
