try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexRentalKit(Document):
    """
    A reusable set of rental equipment. Kits are expanded into ordinary
    rental lines when added to a rental, so every component is priced,
    reserved and availability-checked on its own (no kit-level stock).
    """

    def validate(self):
        pct = float(self.discount_percentage or 0)
        if pct < 0 or pct > 100:
            frappe.throw("Le rabais du kit doit être entre 0 et 100 %.", frappe.ValidationError)
        seen = set()
        for row in self.items or []:
            if float(row.qty or 0) <= 0:
                frappe.throw(f"Quantité invalide pour {row.item_code}.", frappe.ValidationError)
            if row.item_code in seen:
                frappe.throw(f"{row.item_code} apparaît deux fois dans le kit.", frappe.ValidationError)
            seen.add(row.item_code)
            if not frappe.db.exists(
                "Cortex Rental Item Profile", {"company": self.company, "item_code": row.item_code}
            ):
                frappe.throw(
                    f"{row.item_code} n’est pas dans le catalogue locatif de {self.company}.", frappe.ValidationError
                )
