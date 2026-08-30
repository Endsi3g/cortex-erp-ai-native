try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None


class CortexCheckIn(Document):
    """
    A physical return event (full or partial) against a Cortex Rental
    Transaction. Deliberately not exposed to any agent/MCP tool — per
    PRD, physical equipment receiving is a human/logistics action
    (serial number scanning), never an autonomous agent one. The actual
    state mutation (Serial No status, transaction item returned_qty,
    transaction transition to Returned once fully back) happens in
    services/checkin.complete_checkin(), not here — this class only
    guards the precondition that the transaction is actually checked out.
    """

    def validate(self):
        if not frappe:
            return
        if self.transaction:
            rental_state = frappe.db.get_value("Cortex Rental Transaction", self.transaction, "rental_state")
            if rental_state not in ("Checked Out",):
                frappe.throw(
                    f"Cannot check in against a transaction in state [{rental_state}]; it must be Checked Out.",
                    frappe.ValidationError,
                )
