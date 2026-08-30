"""
Check-in / partial-return / quarantine service (PRD §4: "Retours
partiels, équipements manquants, quarantaine et réparation").

A Cortex Check-In records what physically came back for one or more
lines of a Cortex Rental Transaction. Completing one:
  1. Updates each returned Serial No's cortex_status per its disposition
     (Return to Stock/Quarantine/Repair/Missing/Write-off), so
     AvailabilityService (Phase 5) immediately reflects it.
  2. Increments returned_qty on the matching Cortex Rental Transaction
     Item line(s).
  3. Transitions the transaction to Returned only once every line is
     fully returned — a partial return leaves it Checked Out, which is
     the correct state for "some units are still out".

This is deliberately human-only: no MCP tool calls into this module.
Physical receiving requires a person scanning real serial numbers.
"""

from typing import Any, Dict, List

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


def complete_checkin(checkin_name: str, actor_id: str) -> Dict[str, Any]:
    if not frappe:
        return {"id": checkin_name, "status": "Completed", "transaction_fully_returned": True}

    from cortex_rental.services.audit import AuditService

    checkin = frappe.get_doc("Cortex Check-In", checkin_name)
    if checkin.status == "Completed":
        frappe.throw("This Cortex Check-In has already been completed.", frappe.ValidationError)

    transaction = frappe.get_doc("Cortex Rental Transaction", checkin.transaction)

    for row in checkin.items or []:
        _apply_disposition(row)
        _increment_returned_qty(transaction, row)

    checkin.status = "Completed"
    checkin.checked_in_by = actor_id
    checkin.checked_in_at = frappe.utils.now_datetime()
    checkin.save()

    AuditService.record_mutation(
        company=checkin.company,
        action="cortex.check_in.completed",
        entity_type="Cortex Check-In",
        entity_id=checkin.name,
        after_state={"transaction": checkin.transaction, "line_count": len(checkin.items or [])},
    )

    fully_returned = _is_fully_returned(transaction.name)
    if fully_returned:
        transaction.reload()
        transaction.transition_to("Returned", reason=f"Fully returned via {checkin.name}")

    return {
        "id": checkin.name,
        "status": "Completed",
        "transaction": checkin.transaction,
        "transaction_fully_returned": fully_returned,
    }


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
            frappe.db.set_value(
                "Cortex Rental Transaction Item",
                item.name,
                "returned_qty",
                (item.returned_qty or 0) + checkin_row.returned_qty,
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
    return all((line.returned_qty or 0) >= line.qty for line in lines)
