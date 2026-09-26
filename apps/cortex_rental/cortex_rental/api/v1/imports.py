"""Import & migration: CSV → ERPNext / Cortex documents, in 6 steps.

1. create a batch (type)  2. attach the CSV  3. map columns  4. validate
5. import the valid rows  6. review, and roll back if needed.

Every created document is recorded on the batch, so rollback deletes
exactly those, newest first. A document that something else now links to
is kept and reported instead of being force-deleted. Admins only.
"""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.api.v1.admin import require_admin
from cortex_rental.permissions.agent_scopes import get_company_context
from cortex_rental.services import importer
from cortex_rental.services.audit import AuditService

DOCTYPE = "Cortex Import Batch"
MAX_STORED_ERRORS = 1000


def _batch(name: str, company: str):
    if not frappe.db.exists(DOCTYPE, {"name": name, "company": company}):
        frappe.throw("Lot d’import introuvable pour la société active.", frappe.PermissionError)
    return frappe.get_doc(DOCTYPE, name)


def _source(batch) -> tuple:
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": DOCTYPE, "attached_to_name": batch.name},
        fields=["name", "file_name"],
        order_by="creation desc",
        limit_page_length=1,
    )
    if not files:
        frappe.throw("Joignez d’abord le fichier CSV.", frappe.ValidationError)
    file_doc = frappe.get_doc("File", files[0].name)
    content = file_doc.get_content()
    if isinstance(content, str):
        content = content.encode("utf-8")
    try:
        headers, rows = importer.parse_csv(content)
    except ValueError as exc:
        frappe.throw(str(exc), frappe.ValidationError)
    return files[0].file_name, headers, rows


def _exists(company: str):
    def exists(kind: str, value: str) -> bool:
        if kind == "customer":
            return bool(frappe.db.exists("Customer", {"customer_name": value, "cortex_company": company}))
        if kind == "profile":
            return bool(frappe.db.exists("Cortex Rental Item Profile", {"company": company, "item_code": value}))
        if kind == "item":
            return bool(frappe.db.exists("Item", value))
        if kind == "serial":
            return bool(frappe.db.exists("Serial No", value))
        if kind == "owner":
            return bool(frappe.db.exists("Consignment Owner", {"company": company, "short_code": value}))
        return False

    return exists


def _serialize(batch) -> Dict[str, Any]:
    return {
        "name": batch.name,
        "import_type": batch.import_type,
        "status": batch.status,
        "source_file_name": batch.source_file_name,
        "mapping": frappe.parse_json(batch.mapping) if batch.mapping else None,
        "total_rows": int(batch.total_rows or 0),
        "valid_rows": int(batch.valid_rows or 0),
        "error_rows": int(batch.error_rows or 0),
        "imported_rows": int(batch.imported_rows or 0),
        "row_errors": frappe.parse_json(batch.row_errors) if batch.row_errors else [],
        "records": [
            {
                "line": r.row_number,
                "doctype": r.record_doctype,
                "name": r.record_name,
                "rolled_back": bool(r.rolled_back),
            }
            for r in batch.records or []
        ],
        "created_by": batch.owner,
        "created_at": str(batch.creation),
        "imported_by": batch.imported_by,
        "imported_at": str(batch.imported_at) if batch.imported_at else None,
        "rolled_back_by": batch.rolled_back_by,
        "rolled_back_at": str(batch.rolled_back_at) if batch.rolled_back_at else None,
    }


def _default_item_group() -> str:
    group = frappe.db.get_single_value("Stock Settings", "item_group")
    if group and not frappe.db.get_value("Item Group", group, "is_group"):
        return group
    leaf = frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", limit_page_length=1)
    if not leaf:
        frappe.throw("Aucun groupe d’articles utilisable : créez-en un dans ERPNext.", frappe.ValidationError)
    return leaf[0]


def _create(import_type: str, values: Dict[str, Any], company: str) -> List[tuple]:
    """Create one row's documents; returns [(doctype, name)] in creation order."""
    created = []
    if import_type == "Customers":
        doc = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": values["customer_name"],
                "customer_type": values.get("customer_type") or "Company",
                "cortex_company": company,
                "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
                or "All Customer Groups",
                "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
            }
        )
        if values.get("email"):
            doc.email_id = values["email"]
        if values.get("phone"):
            doc.mobile_no = values["phone"]
        if values.get("insurance_valid_until") and frappe.db.has_column("Customer", "cortex_insurance_valid_until"):
            doc.cortex_insurance_valid_until = values["insurance_valid_until"]
        doc.insert()
        created.append(("Customer", doc.name))
    elif import_type == "Equipment":
        code = values["item_code"]
        if not frappe.db.exists("Item", code):
            item = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": code,
                    "item_name": values["item_name"],
                    "item_group": _default_item_group(),
                    "stock_uom": frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos",
                    "is_stock_item": 1,
                    "has_serial_no": 1 if values.get("is_serialized") else 0,
                }
            )
            item.insert()
            created.append(("Item", item.name))
        profile = frappe.get_doc(
            {
                "doctype": "Cortex Rental Item Profile",
                "company": company,
                "item_code": code,
                "item_name": values["item_name"],
                "category": values.get("category"),
                "daily_rate": values["daily_rate"],
                "replacement_value": values.get("replacement_value") or 0,
                "deposit_required": values.get("deposit_required") or 0,
                "is_serialized": 1 if values.get("is_serialized") else 0,
            }
        )
        profile.insert()
        created.append(("Cortex Rental Item Profile", profile.name))
    elif import_type == "Serial Numbers":
        owner = None
        if values.get("consignment_owner"):
            owner = frappe.db.get_value(
                "Consignment Owner", {"company": company, "short_code": values["consignment_owner"]}, "name"
            )
        doc = frappe.get_doc(
            {
                "doctype": "Serial No",
                "serial_no": values["serial_no"],
                "item_code": values["item_code"],
                "company": company,
                "warranty_expiry_date": values.get("warranty_expiry_date"),
                "cortex_consignment_owner": owner,
            }
        )
        doc.insert()
        created.append(("Serial No", doc.name))
    return created


def import_rows(import_type: str, results: List[Dict[str, Any]], company: str):
    """Create every valid row in its own savepoint; a failing row is reported, never half-created."""
    records, imported = [], 0
    errors = [{"line": r["line"], "errors": r["errors"]} for r in results if r["errors"]]
    for result in results:
        if result["errors"]:
            continue
        frappe.db.savepoint("cortex_import_row")
        try:
            created = _create(import_type, result["values"], company)
        except Exception as exc:  # one bad row must not abort the batch
            frappe.db.rollback(save_point="cortex_import_row")
            errors.append({"line": result["line"], "errors": [str(exc)[:300]]})
            continue
        records.extend((result["line"], doctype, name) for doctype, name in created)
        imported += 1
    return records, errors, imported


def rollback_records(records) -> tuple:
    """Delete created documents newest first; keep (and explain) any another document now links to."""
    kept, deleted = [], 0
    for record in reversed(records):
        if record.rolled_back:
            continue
        if not frappe.db.exists(record.record_doctype, record.record_name):
            record.rolled_back = 1
            continue
        frappe.db.savepoint("cortex_import_rollback")
        try:
            frappe.delete_doc(record.record_doctype, record.record_name)
        except Exception as exc:  # LinkExistsError and friends
            frappe.db.rollback(save_point="cortex_import_rollback")
            kept.append({"doctype": record.record_doctype, "name": record.record_name, "reason": str(exc)[:300]})
            continue
        record.rolled_back = 1
        deleted += 1
    return deleted, kept


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_import_batches():
        require_admin()
        company = get_company_context()
        rows = frappe.get_all(
            DOCTYPE,
            filters={"company": company},
            fields=[
                "name",
                "import_type",
                "status",
                "source_file_name",
                "total_rows",
                "valid_rows",
                "error_rows",
                "imported_rows",
                "owner",
                "creation",
                "imported_at",
            ],
            order_by="creation desc",
            limit_page_length=100,
        )
        return {
            "data": {
                "items": [
                    {
                        "name": r.name,
                        "import_type": r.import_type,
                        "status": r.status,
                        "source_file_name": r.source_file_name,
                        "total_rows": int(r.total_rows or 0),
                        "valid_rows": int(r.valid_rows or 0),
                        "error_rows": int(r.error_rows or 0),
                        "imported_rows": int(r.imported_rows or 0),
                        "created_by": r.owner,
                        "created_at": str(r.creation),
                        "imported_at": str(r.imported_at) if r.imported_at else None,
                    }
                    for r in rows
                ],
                "specs": {
                    kind: [
                        {"field": field, "label": label, "required": required}
                        for field, (label, required, _k, _a) in spec.items()
                    ]
                    for kind, spec in importer.SPECS.items()
                },
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_import_batch(batch: str):
        require_admin()
        return {"data": _serialize(_batch(batch, get_company_context()))}

    @frappe.whitelist(methods=["POST"])
    def create_import_batch(import_type: str):
        require_admin()
        if import_type not in importer.SPECS:
            frappe.throw("Type d’import inconnu.", frappe.ValidationError)
        company = get_company_context()
        doc = frappe.get_doc({"doctype": DOCTYPE, "company": company, "import_type": import_type, "status": "Draft"})
        doc.insert()
        return {"data": _serialize(doc)}

    @frappe.whitelist(methods=["POST"])
    def analyze_import(batch: str):
        """Step 3: headers, a preview and the suggested column mapping."""
        require_admin()
        doc = _batch(batch, get_company_context())
        if doc.status not in ("Draft", "Validated"):
            frappe.throw("Ce lot est déjà importé.", frappe.ValidationError)
        file_name, headers, rows = _source(doc)
        doc.db_set({"source_file_name": file_name, "total_rows": len(rows)})
        saved = frappe.parse_json(doc.mapping) if doc.mapping else None
        return {
            "data": {
                "file_name": file_name,
                "headers": headers,
                "preview": rows[:10],
                "total_rows": len(rows),
                "mapping": saved or importer.suggest_mapping(doc.import_type, headers),
            }
        }

    @frappe.whitelist(methods=["POST"])
    def validate_import(batch: str, mapping: str):
        """Step 4: every row checked against the file and the site. Nothing is created."""
        require_admin()
        company = get_company_context()
        doc = _batch(batch, company)
        if doc.status not in ("Draft", "Validated"):
            frappe.throw("Ce lot est déjà importé.", frappe.ValidationError)
        mapping = frappe.parse_json(mapping) or {}
        _file, headers, rows = _source(doc)
        problems = importer.check_mapping(doc.import_type, headers, mapping)
        if problems:
            frappe.throw(" ".join(problems), frappe.ValidationError)
        results = importer.validate_rows(doc.import_type, headers, rows, mapping, _exists(company))
        counts = importer.summarize(results)
        errors = [{"line": r["line"], "errors": r["errors"]} for r in results if r["errors"]][:MAX_STORED_ERRORS]
        doc.db_set(
            {
                "mapping": frappe.as_json(mapping),
                "row_errors": frappe.as_json(errors),
                "status": "Validated",
                **counts,
            }
        )
        return {
            "data": {
                **counts,
                "errors": errors,
                "sample": [{"line": r["line"], "values": r["values"]} for r in results if not r["errors"]][:10],
            }
        }

    @frappe.whitelist(methods=["POST"])
    def run_import(batch: str):
        """Step 5: re-validates (the site may have changed) and creates the valid rows."""
        require_admin()
        company = get_company_context()
        doc = _batch(batch, company)
        if doc.status != "Validated" or not doc.mapping:
            frappe.throw("Validez le lot avant de l’importer.", frappe.ValidationError)
        _file, headers, rows = _source(doc)
        mapping = frappe.parse_json(doc.mapping)
        results = importer.validate_rows(doc.import_type, headers, rows, mapping, _exists(company))
        records, errors, imported = import_rows(doc.import_type, results, company)
        for line, doctype, name in records:
            doc.append("records", {"row_number": line, "record_doctype": doctype, "record_name": name})
        errors.sort(key=lambda e: e["line"])
        doc.status = "Imported" if imported and not errors else "Partially Imported" if imported else "Failed"
        doc.imported_rows = imported
        doc.error_rows = len(errors)
        doc.row_errors = frappe.as_json(errors[:MAX_STORED_ERRORS])
        doc.imported_by = frappe.session.user
        doc.imported_at = frappe.utils.now_datetime()
        doc.save()
        AuditService.record_mutation(
            company=company,
            action="cortex.import.completed",
            entity_type=DOCTYPE,
            entity_id=doc.name,
            after_state={"type": doc.import_type, "imported_rows": imported, "error_rows": len(errors)},
        )
        return {"data": _serialize(doc)}

    @frappe.whitelist(methods=["POST"])
    def rollback_import(batch: str, reason: str):
        """Step 6: delete what this batch created, newest first; linked documents are kept and listed."""
        require_admin()
        if not reason or len(reason.strip()) < 3:
            frappe.throw("Un motif d’au moins trois caractères est obligatoire.", frappe.ValidationError)
        company = get_company_context()
        doc = _batch(batch, company)
        if doc.status not in ("Imported", "Partially Imported"):
            frappe.throw("Seul un lot importé peut être annulé.", frappe.ValidationError)
        deleted, kept = rollback_records(doc.records or [])
        if not kept:
            doc.status = "Rolled Back"
            doc.rolled_back_by = frappe.session.user
            doc.rolled_back_at = frappe.utils.now_datetime()
        doc.save()
        AuditService.record_mutation(
            company=company,
            action="cortex.import.rolled_back",
            entity_type=DOCTYPE,
            entity_id=doc.name,
            after_state={"deleted": deleted, "kept": len(kept), "reason": reason.strip()[:500]},
        )
        return {"data": {**_serialize(doc), "kept": kept, "deleted": deleted}}
