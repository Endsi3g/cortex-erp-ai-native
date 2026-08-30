try:
    import frappe
    from frappe.model.document import Document
except ImportError:

    class Document:
        pass

    frappe = None

from cortex_rental.services.audit import AuditService


class CortexInboundRequest(Document):
    """
    Structured ingestion container for incoming rental inquiries (emails, PDFs, webhooks).
    Enforces Rule #1: Structured extraction before business mutation.
    """

    def before_insert(self):
        if not self.status:
            self.status = "Received"

    def mark_processed(self, transaction_id: str, agent_id: str):
        self.status = "Processed"
        self.extracted_transaction = transaction_id
        self.processed_by = agent_id
        self.save()

        AuditService.record_mutation(
            company=self.company,
            action="cortex.inbound_request.processed",
            entity_type="Cortex Inbound Request",
            entity_id=self.name if hasattr(self, "name") else "new",
            after_state={"status": "Processed", "transaction_id": transaction_id},
        )
