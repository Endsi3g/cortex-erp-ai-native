"""
Server-side validation of the chat context a client submits. The
client's ChatContext (schemas/chat_schemas.py) is a *request*, never a
source of truth — this resolver is what the spec means by "le serveur
doit vérifier que l'utilisateur peut voir la ressource" and "refuser
tout contexte cross-tenant".
"""

import hashlib
import json
from typing import Any, Dict

try:
    import frappe
except ImportError:
    frappe = None


class ChatContextPermissionError(Exception):
    """Raised when the requesting user cannot see the referenced
    document — kept distinct from frappe.PermissionError so this module
    stays importable/testable without a live Frappe site."""


class ChatContextResolver:
    @staticmethod
    def resolve(context: Dict[str, Any], user: str, company: str) -> Dict[str, Any]:
        """
        `context` is `ChatContext.model_dump()` — already structurally
        valid (right types, right lengths) by the time it gets here.
        This adds the checks a Pydantic schema can't: does this
        specific document actually exist and is this specific user
        actually allowed to read it.

        Returns a new dict — the "resolved" context — never the same
        object passed in, so a caller can't confuse "what the client
        asked for" with "what was actually authorized".
        """
        resolved = dict(context)
        resolved["company_resolved_server_side"] = True

        doctype = context.get("active_doctype")
        document_name = context.get("active_document_name")

        if doctype and document_name:
            if not frappe:
                # No live site to check against — leave the reference in
                # place but don't claim it was verified.
                resolved["reference_verified"] = False
            else:
                if not frappe.db.exists(doctype, document_name):
                    raise ChatContextPermissionError(f"{doctype} {document_name} does not exist.")
                if not frappe.has_permission(doctype, doc=document_name, user=user, ptype="read"):
                    raise ChatContextPermissionError(
                        f"User {user} does not have read access to {doctype} {document_name}."
                    )
                # Company-scoped doctypes must also match the caller's
                # resolved Company — belt-and-suspenders on top of
                # frappe.has_permission (which already runs
                # permission_query_conditions-equivalent checks for a
                # single doc via get_doc, but this makes the tenant
                # check explicit and independently testable).
                doc_company = frappe.db.get_value(doctype, document_name, "company")
                if doc_company and doc_company != company:
                    raise ChatContextPermissionError(
                        f"{doctype} {document_name} belongs to a different Company than the caller's session."
                    )
                resolved["reference_verified"] = True
        else:
            resolved["reference_verified"] = None

        return resolved

    @staticmethod
    def hash_context(resolved_context: Dict[str, Any]) -> str:
        raw = json.dumps(resolved_context, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
