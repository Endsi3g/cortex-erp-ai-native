"""Réglages de la passerelle IA : modèle, clé, limites, prix et plafond mensuel par société."""

try:
    import frappe
    from frappe.model.document import Document
except ImportError:
    frappe = None

    class Document:
        pass


class CortexAISettings(Document):
    def validate(self):
        if self.model and not str(self.model).strip().lower().startswith("gemini-"):
            frappe.throw("Le modèle doit être un identifiant Gemini (il commence par « gemini- »).")
        for field in (
            "price_input_per_mtok",
            "price_output_per_mtok",
            "default_monthly_budget",
            "default_monthly_token_cap",
        ):
            if (self.get(field) or 0) < 0:
                frappe.throw("Les prix et les plafonds ne peuvent pas être négatifs.")
        if not 1 <= int(self.max_tool_steps or 5) <= 8:
            frappe.throw("Le nombre d'étapes d'outils doit être entre 1 et 8.")
        seen = set()
        for row in self.company_budgets or []:
            if row.company in seen:
                frappe.throw(f"La société {row.company} est en double dans les plafonds par société.")
            seen.add(row.company)
