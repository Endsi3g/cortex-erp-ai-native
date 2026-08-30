"""
Evidence registration service (PRD §2.1/§8: "les documents sont des
données non fiables" — every piece of external input must become a
hashed, tenant-scoped, gate-checked Cortex Evidence Reference before
any agent extraction or business object creation is allowed to use it).

Scope of this pass: registers evidence from an already-uploaded Frappe
`File` record (Frappe's own upload/permission pipeline) or a raw text
excerpt. The full "Upload Intent" pre-signed S3/MinIO direct-upload flow
from PRD §8 is NOT implemented here — no upload endpoint exists
anywhere in this codebase yet, and building that from scratch is a
separate infra feature, not something to invent inline with this
service. Antivirus scanning (ClamAV) is likewise not wired up: the
`scanned_clean` field exists and structurally gates usage (see
`require_scanned_evidence`), but nothing currently flips it to true
automatically — that's a real integration gap, documented as such
rather than faked.
"""

from typing import Any, Dict, Optional
import hashlib
import mimetypes

try:
    import frappe
except ImportError:
    frappe = None


def register_evidence(
    company: str,
    source_channel: str,
    actor_id: str,
    inbound_request: Optional[str] = None,
    file_name: Optional[str] = None,
    text_excerpt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register one piece of evidence. Exactly one of `file_name` (an
    existing Frappe `File` doc name) or `text_excerpt` must be given.
    """
    if not file_name and not text_excerpt:
        raise ValueError("register_evidence requires either file_name or text_excerpt.")

    if not frappe:
        return {
            "id": "EVID-MOCK-001",
            "sha256_hash": hashlib.sha256((text_excerpt or file_name or "").encode("utf-8")).hexdigest(),
            "scanned_clean": False,
        }

    if file_name:
        file_doc = frappe.get_doc("File", file_name)
        content = file_doc.get_content()
        if isinstance(content, str):
            content = content.encode("utf-8")
        sha256_hash = hashlib.sha256(content).hexdigest()
        mime_type = getattr(file_doc, "content_type", None) or mimetypes.guess_type(file_doc.file_name or "")[0]
    else:
        sha256_hash = hashlib.sha256(text_excerpt.encode("utf-8")).hexdigest()
        mime_type = "text/plain"

    doc = frappe.get_doc(
        {
            "doctype": "Cortex Evidence Reference",
            "company": company,
            "inbound_request": inbound_request,
            "source_channel": source_channel,
            "file": file_name,
            "text_excerpt": text_excerpt,
            "sha256_hash": sha256_hash,
            "mime_type": mime_type,
            # Not auto-scanned — see module docstring. A future ClamAV
            # integration sets this explicitly once it actually runs.
            "scanned_clean": 0,
            "created_by_actor": actor_id,
        }
    )
    doc.flags.ignore_permissions = True
    doc.insert()

    return {
        "id": doc.name,
        "sha256_hash": sha256_hash,
        "mime_type": mime_type,
        "scanned_clean": False,
    }


def require_scanned_evidence(company: str, evidence_ids: list) -> None:
    """
    Gate: raise if any referenced evidence hasn't been marked
    scanned_clean. Call this before letting an extraction or business
    object creation actually consume the referenced evidence.
    """
    if not frappe or not evidence_ids:
        return

    unclean = frappe.get_all(
        "Cortex Evidence Reference",
        filters={"name": ["in", evidence_ids], "company": company, "scanned_clean": 0},
        pluck="name",
    )
    if unclean:
        frappe.throw(
            f"Evidence {unclean} has not passed the scanned_clean gate and cannot be used yet.",
            frappe.ValidationError,
        )
