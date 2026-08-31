"""
Check-in / partial-return / quarantine service (PRD §4: "Retours
partiels, équipements manquants, quarantaine et réparation").

A Cortex Check-In records what physically came back for one or more
lines of a Cortex Rental Transaction. Completing one:
  1. Updates each returned Serial No's cortex_status per its disposition
     (Return to Stock/Quarantine/Repair/Missing/Write-off), so
     AvailabilityService immediately reflects it.
  2. Increments returned_qty on the matching Cortex Rental Transaction
     Item line(s).
  3. Transitions the transaction to Returned once every line is fully returned,
     or when settled with loss/damage declaration. A partial return leaves
     it Checked Out, which is the correct state for "some units are still out".

This is deliberately human-only: no MCP tool calls into this module.
Physical receiving requires a person scanning real serial numbers.
"""

from typing import Any, Dict, List, Optional

try:
    import frappe
except ImportError:
    frappe = None

DISPOSITION_TO_SERIAL_STATUS = {
    "Return to Stock": "Active",
    "Quarantine": "Quarantine",
    "Repair": "Under Repair",
    "Missing": "Missing",
    "Write-off": "Decommissioned",
}


def search_active_transactions(company: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns active Checked Out transactions for a company, with their items and return progress.
    """
    if not frappe:
        return []

    filters: Dict[str, Any] = {
        "company": company,
        "rental_state": "Checked Out",
    }

    or_filters = None
    if query:
        q = f"%{query.strip()}%"
        or_filters = [
            ["name", "like", q],
            ["customer", "like", q],
            ["customer_name", "like", q],
        ]

    txns = frappe.get_all(
        "Cortex Rental Transaction",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "customer",
            "customer_name",
            "rental_state",
            "starts_at",
            "ends_at",
            "currency",
            "total_amount",
            "creation",
        ],
        order_by="ends_at asc, creation desc",
        limit=50,
    )

    if not txns:
        return []

    txn_names = [t["name"] for t in txns]

    # 1. Batch query all items for all transactions in one query
    all_items = frappe.get_all(
        "Cortex Rental Transaction Item",
        filters={"parent": ("in", txn_names)},
        fields=[
            "name",
            "parent",
            "item_code",
            "item_name",
            "serial_no",
            "qty",
            "returned_qty",
            "rate",
            "amount",
        ],
        order_by="idx asc",
    )

    # 2. Batch query all serial numbers statuses for this company
    all_serial_nos = list({i["serial_no"] for i in all_items if i.get("serial_no")})
    serial_status_map: Dict[str, str] = {}
    if all_serial_nos:
        serials = frappe.get_all(
            "Serial No",
            filters={"name": ("in", all_serial_nos), "company": company},
            fields=["name", "cortex_status"],
        )
        serial_status_map = {s["name"]: s.get("cortex_status") or "Active" for s in serials}

    # Group items by parent transaction
    items_by_parent: Dict[str, List[Dict[str, Any]]] = {name: [] for name in txn_names}
    for i in all_items:
        items_by_parent.setdefault(i["parent"], []).append(i)

    results: List[Dict[str, Any]] = []
    for t in txns:
        items = items_by_parent.get(t["name"], [])
        total_qty = sum(float(i.get("qty") or 0.0) for i in items)
        total_returned = sum(float(i.get("returned_qty") or 0.0) for i in items)
        pending_qty = max(0.0, total_qty - total_returned)

        enhanced_items = []
        for i in items:
            sn = i.get("serial_no")
            sn_status = serial_status_map.get(sn) if sn else None

            enhanced_items.append(
                {
                    "name": i["name"],
                    "item_code": i["item_code"],
                    "item_name": i.get("item_name") or i["item_code"],
                    "serial_no": sn,
                    "serial_status": sn_status,
                    "qty": float(i.get("qty") or 0.0),
                    "returned_qty": float(i.get("returned_qty") or 0.0),
                    "rate": float(i.get("rate") or 0.0),
                    "amount": float(i.get("amount") or 0.0),
                    "is_fully_returned": float(i.get("returned_qty") or 0.0) >= float(i.get("qty") or 0.0),
                }
            )

        results.append(
            {
                "name": t["name"],
                "customer": t["customer"],
                "customer_name": t.get("customer_name") or t["customer"],
                "rental_state": t["rental_state"],
                "starts_at": str(t["starts_at"]) if t.get("starts_at") else "",
                "ends_at": str(t["ends_at"]) if t.get("ends_at") else "",
                "currency": t.get("currency") or "USD",
                "total_amount": float(t.get("total_amount") or 0.0),
                "total_lines": len(items),
                "total_qty": total_qty,
                "returned_qty": total_returned,
                "pending_qty": pending_qty,
                "is_complete": pending_qty <= 0,
                "items": enhanced_items,
            }
        )

    return results


def lookup_scan_target(company: str, scan_code: str) -> Dict[str, Any]:
    """
    Resolves a scanned barcode / serial / transaction ID to active rental items in Checked Out state.
    """
    code = (scan_code or "").strip()
    if not code:
        return {"type": "empty", "scan_code": ""}

    if not frappe:
        return {"type": "unknown", "scan_code": code}

    # 1. Direct match on Transaction Name
    txn_match = frappe.db.get_value(
        "Cortex Rental Transaction",
        {"name": code, "company": company, "rental_state": "Checked Out"},
        ["name", "customer", "customer_name", "rental_state", "starts_at", "ends_at"],
        as_dict=True,
    )
    if txn_match:
        items = frappe.get_all(
            "Cortex Rental Transaction Item",
            filters={"parent": txn_match["name"]},
            fields=["name", "item_code", "item_name", "serial_no", "qty", "returned_qty"],
        )
        return {
            "type": "transaction",
            "scan_code": code,
            "transaction": txn_match,
            "items": items,
        }

    # 2. Match on Serial No
    if frappe.db.exists("Serial No", code):
        # Find if this serial number is currently checked out on a transaction
        txn_items = frappe.get_all(
            "Cortex Rental Transaction Item",
            filters={"serial_no": code},
            fields=["name", "parent", "item_code", "item_name", "qty", "returned_qty"],
        )
        for ti in txn_items:
            parent_txn = frappe.db.get_value(
                "Cortex Rental Transaction",
                {"name": ti["parent"], "company": company, "rental_state": "Checked Out"},
                ["name", "customer", "customer_name", "starts_at", "ends_at"],
                as_dict=True,
            )
            if parent_txn:
                return {
                    "type": "serial",
                    "scan_code": code,
                    "serial_no": code,
                    "item_code": ti["item_code"],
                    "item_name": ti.get("item_name") or ti["item_code"],
                    "transaction_item": ti["name"],
                    "transaction": parent_txn,
                }

    # 3. Match on Item Code (e.g. bulk accessory or non-serialized item)
    if frappe.db.exists("Item", code):
        # Look for open Checked Out transactions containing this item
        matching_items = frappe.get_all(
            "Cortex Rental Transaction Item",
            filters={"item_code": code},
            fields=["name", "parent", "item_code", "item_name", "serial_no", "qty", "returned_qty"],
        )
        active_txns = []
        for mi in matching_items:
            if float(mi.get("returned_qty") or 0) < float(mi.get("qty") or 0):
                ptxn = frappe.db.get_value(
                    "Cortex Rental Transaction",
                    {"name": mi["parent"], "company": company, "rental_state": "Checked Out"},
                    ["name", "customer", "customer_name", "starts_at", "ends_at"],
                    as_dict=True,
                )
                if ptxn and ptxn not in active_txns:
                    active_txns.append(ptxn)

        return {
            "type": "item",
            "scan_code": code,
            "item_code": code,
            "active_transactions": active_txns,
        }

    return {"type": "not_found", "scan_code": code}


def complete_checkin(checkin_name: str, actor_id: str, finalize_mode: str = "auto") -> Dict[str, Any]:
    """
    Completes an existing Cortex Check-In document.
    """
    if not frappe:
        return {"id": checkin_name, "status": "Completed", "transaction_fully_returned": True}

    from cortex_rental.services.audit import AuditService

    checkin = frappe.get_doc("Cortex Check-In", checkin_name)
    if checkin.status == "Completed":
        frappe.throw("This Cortex Check-In has already been completed.", frappe.ValidationError)

    transaction = frappe.get_doc("Cortex Rental Transaction", checkin.transaction)
    if transaction.rental_state != "Checked Out":
        frappe.throw(
            f"Cannot check in against a transaction in state [{transaction.rental_state}]; it must be Checked Out.",
            frappe.ValidationError,
        )

    for row in checkin.items or []:
        _apply_disposition(row)
        _increment_returned_qty(transaction, row)

    checkin.status = "Completed"
    checkin.checked_in_by = actor_id
    checkin.checked_in_at = frappe.utils.now_datetime()
    if finalize_mode and finalize_mode != "auto":
        checkin.finalize_mode = finalize_mode
    checkin.save()

    AuditService.record_mutation(
        company=checkin.company,
        action="cortex.check_in.completed",
        entity_type="Cortex Check-In",
        entity_id=checkin.name,
        after_state={
            "transaction": checkin.transaction,
            "line_count": len(checkin.items or []),
            "finalize_mode": checkin.finalize_mode or "auto",
        },
    )

    fully_returned = _is_fully_returned(transaction.name)
    should_transition = fully_returned or (finalize_mode in ("settle_with_loss", "Full Return", "Settle With Loss"))

    if should_transition:
        transaction.reload()
        reason = (
            f"Settled with loss/damage via {checkin.name}"
            if finalize_mode in ("settle_with_loss", "Settle With Loss")
            else f"Fully returned via {checkin.name}"
        )
        transaction.transition_to("Returned", reason=reason)

    return {
        "id": checkin.name,
        "status": "Completed",
        "transaction": checkin.transaction,
        "transaction_fully_returned": should_transition,
        "finalize_mode": checkin.finalize_mode or "auto",
    }


def process_checkin(
    company: str,
    actor_id: str,
    transaction_id: str,
    items: List[Dict[str, Any]],
    finalize_mode: str = "auto",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Creates and completes a Cortex Check-In in a single atomic, audited flow.
    """
    if not frappe:
        return {
            "id": "CHK-MOCK-00001",
            "status": "Completed",
            "transaction": transaction_id,
            "transaction_fully_returned": True,
            "finalize_mode": finalize_mode,
        }

    if not transaction_id:
        frappe.throw("transaction_id is required for Check-In.", frappe.ValidationError)

    if not items:
        frappe.throw("At least one item must be submitted for Check-In.", frappe.ValidationError)

    txn = frappe.get_doc("Cortex Rental Transaction", transaction_id)
    if txn.company != company:
        frappe.throw("Tenant company mismatch on transaction.", frappe.PermissionError)

    if txn.rental_state != "Checked Out":
        frappe.throw(
            f"Cannot check in against transaction [{transaction_id}] in state [{txn.rental_state}]. It must be Checked Out.",
            frappe.ValidationError,
        )

    # Create the Cortex Check-In document
    checkin = frappe.get_doc(
        {
            "doctype": "Cortex Check-In",
            "company": company,
            "transaction": transaction_id,
            "status": "Draft",
            "checked_in_by": actor_id,
            "finalize_mode": (
                "Settle With Loss"
                if finalize_mode == "settle_with_loss"
                else "Partial Return"
                if finalize_mode == "partial"
                else "Full Return"
                if finalize_mode == "full"
                else "Auto"
            ),
            "notes": notes or "",
            "items": [],
        }
    )

    for item in items:
        sn = item.get("serial_no") or None
        if sn:
            sn_company = frappe.db.get_value("Serial No", sn, "company")
            if sn_company and sn_company != company:
                frappe.throw(
                    f"Serial Number [{sn}] belongs to company [{sn_company}] and cannot be checked in under company [{company}].",
                    frappe.PermissionError,
                )

        checkin.append(
            "items",
            {
                "transaction_item": item.get("transaction_item") or "",
                "item_code": item.get("item_code"),
                "serial_no": sn,
                "expected_qty": float(item.get("expected_qty") or 1.0),
                "returned_qty": float(item.get("returned_qty") or 1.0),
                "condition": item.get("condition") or "Good",
                "disposition": item.get("disposition") or "Return to Stock",
                "damage_severity": item.get("damage_severity") or "None",
                "damage_type": item.get("damage_type") or "None",
                "estimated_repair_cost": float(item.get("estimated_repair_cost") or 0.0),
                "notes": item.get("notes") or "",
            },
        )

    checkin.insert()

    # Complete checkin
    return complete_checkin(checkin.name, actor_id=actor_id, finalize_mode=finalize_mode)


def _apply_disposition(row) -> None:
    if not row.serial_no:
        return
    new_status = DISPOSITION_TO_SERIAL_STATUS.get(row.disposition)
    if not new_status:
        return
    frappe.db.set_value("Serial No", row.serial_no, "cortex_status", new_status)


def _increment_returned_qty(transaction, checkin_row) -> None:
    for item in transaction.items or []:
        matches_row = item.name == checkin_row.transaction_item
        matches_lookup = (
            not checkin_row.transaction_item
            and item.item_code == checkin_row.item_code
            and (not checkin_row.serial_no or item.serial_no == checkin_row.serial_no)
        )
        if matches_row or matches_lookup:
            current_qty = float(item.returned_qty or 0.0)
            added_qty = float(checkin_row.returned_qty or 0.0)
            frappe.db.set_value(
                "Cortex Rental Transaction Item",
                item.name,
                "returned_qty",
                current_qty + added_qty,
            )
            return


def _is_fully_returned(transaction_name: str) -> bool:
    lines: List[Dict[str, Any]] = frappe.get_all(
        "Cortex Rental Transaction Item",
        filters={"parent": transaction_name},
        fields=["qty", "returned_qty"],
    )
    if not lines:
        return False
    return all((float(line.get("returned_qty") or 0.0)) >= float(line.get("qty") or 0.0) for line in lines)
