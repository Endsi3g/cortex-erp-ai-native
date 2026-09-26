"""Catalog: equipment profiles, serial numbers and kits (human staff, tenant-scoped).

ERPNext stays the owner of Item and Serial No; Cortex owns the rental
profile (rates, guarantee, category) and the kits. Optional ERPNext fields
are read through the DocType meta so a field missing in a given ERPNext
version is skipped instead of breaking the query.
"""

import datetime
from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import get_company_context, require_human_staff_role
from cortex_rental.services.audit import AuditService
from cortex_rental.services.pricing import PricingService

CATALOG_MANAGER_ROLES = {"System Manager", "Cortex System Manager", "Rental Manager", "Cortex Inventory Manager"}
SERIAL_STATUSES = ("Active", "Quarantine", "Under Repair", "Missing", "Decommissioned")
EDITABLE_PROFILE_FIELDS = {
    "daily_rate": float,
    "replacement_value": float,
    "deposit_required": float,
    "prep_hours": float,
    "total_quantity": int,
    "category": str,
    "required_accessories": str,
}
PRICING_CURVE_DAYS = (1, 2, 3, 4, 5, 7, 10, 14, 21, 30)
OUT_STATES = ("Checked Out",)


def _require_catalog_manager() -> None:
    if not set(frappe.get_roles(frappe.session.user)) & CATALOG_MANAGER_ROLES:
        frappe.throw("Votre rôle ne permet pas de modifier le catalogue.", frappe.PermissionError)


def _existing(doctype: str, fields: List[str]) -> List[str]:
    meta = frappe.get_meta(doctype)
    return [field for field in fields if field == "name" or meta.has_field(field)]


def _profile(company: str, item_code: str):
    profile = frappe.db.get_value(
        "Cortex Rental Item Profile",
        {"company": company, "item_code": item_code},
        [
            "name",
            "item_code",
            "item_name",
            "category",
            "daily_rate",
            "replacement_value",
            "deposit_required",
            "is_serialized",
            "total_quantity",
            "prep_hours",
            "is_consignment_allowed",
            "required_accessories",
        ],
        as_dict=True,
    )
    if not profile:
        frappe.throw("Équipement introuvable dans le catalogue de la société active.", frappe.DoesNotExistError)
    return profile


def _serials_out(company: str, item_code: str) -> Dict[str, str]:
    """serial -> rental currently holding it (Checked Out)."""
    rows = frappe.db.sql(
        """
        SELECT ti.assigned_serials, t.name AS transaction
        FROM `tabCortex Rental Transaction Item` ti
        JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
        WHERE t.company = %(company)s AND ti.item_code = %(item_code)s AND t.rental_state IN %(states)s
        """,
        {"company": company, "item_code": item_code, "states": OUT_STATES},
        as_dict=True,
    )
    out: Dict[str, str] = {}
    for row in rows:
        try:
            serials = frappe.parse_json(row.assigned_serials or "[]") or []
        except Exception:
            serials = []
        for serial in serials:
            out[serial] = row.transaction
    return out


def fleet_summary(company: str, item_code: str, is_serialized: bool, total_quantity: int) -> Dict[str, int]:
    if not is_serialized:
        return {"total": int(total_quantity or 0), "active": int(total_quantity or 0), "out": 0, "unavailable": 0}
    counts = frappe.db.sql(
        """
        SELECT IFNULL(cortex_status, 'Active') AS status, COUNT(*) AS n
        FROM `tabSerial No` WHERE company = %(company)s AND item_code = %(item_code)s
        GROUP BY IFNULL(cortex_status, 'Active')
        """,
        {"company": company, "item_code": item_code},
        as_dict=True,
    )
    by_status = {row.status: int(row.n) for row in counts}
    out = len(_serials_out(company, item_code))
    return {
        "total": sum(by_status.values()),
        "active": by_status.get("Active", 0),
        "out": out,
        "unavailable": sum(v for k, v in by_status.items() if k != "Active"),
        "by_status": by_status,
    }


def pricing_curve(daily_rate: float, company: str) -> List[Dict[str, float]]:
    start = datetime.datetime(2026, 1, 5, 8, 0, 0)
    curve = []
    for days in PRICING_CURVE_DAYS:
        end = start + datetime.timedelta(days=days) - datetime.timedelta(hours=1)
        calendar_days, billable = PricingService.compute_billable_days(start, end, company)
        curve.append(
            {
                "calendar_days": calendar_days,
                "billable_days": billable,
                "price": round(billable * float(daily_rate or 0), 2),
            }
        )
    return curve


def _kit_payload(doc) -> Dict[str, Any]:
    return {
        "name": doc.name,
        "kit_name": doc.kit_name,
        "is_active": bool(doc.is_active),
        "discount_percentage": float(doc.discount_percentage or 0),
        "description": doc.description or "",
        "items": [
            {
                "item_code": row.item_code,
                "item_name": frappe.db.get_value("Item", row.item_code, "item_name") or row.item_code,
                "qty": float(row.qty or 0),
                "is_optional": bool(row.is_optional),
                "daily_rate": float(
                    frappe.db.get_value(
                        "Cortex Rental Item Profile", {"company": doc.company, "item_code": row.item_code}, "daily_rate"
                    )
                    or 0
                ),
            }
            for row in doc.items or []
        ],
    }


def _owned_kit(name: str, company: str):
    doc = frappe.get_doc("Cortex Rental Kit", name)
    if doc.company != company:
        frappe.throw("Kit introuvable pour la société active.", frappe.PermissionError)
    return doc


if frappe:

    @frappe.whitelist(methods=["GET"])
    def list_equipment(search: str = None, category: str = None, page=1, page_size=50):
        require_human_staff_role()
        company = get_company_context()
        page, page_size = max(1, int(page)), min(500, max(1, int(page_size)))
        filters: Dict[str, Any] = {"company": company}
        if category:
            filters["category"] = category
        or_filters = None
        if search:
            token = f"%{search.strip()}%"
            or_filters = [["item_code", "like", token], ["item_name", "like", token]]
        rows = frappe.get_list(
            "Cortex Rental Item Profile",
            filters=filters,
            or_filters=or_filters,
            fields=[
                "item_code",
                "item_name",
                "category",
                "daily_rate",
                "replacement_value",
                "is_serialized",
                "total_quantity",
            ],
            order_by="item_name asc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )
        total = len(frappe.get_list("Cortex Rental Item Profile", filters=filters, or_filters=or_filters, pluck="name"))
        currency = frappe.db.get_value("Company", company, "default_currency")
        items = []
        for row in rows:
            fleet = fleet_summary(company, row.item_code, bool(row.is_serialized), row.total_quantity)
            items.append(
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name or row.item_code,
                    "category": row.category or "",
                    "daily_rate": float(row.daily_rate or 0),
                    "replacement_value": float(row.replacement_value or 0),
                    "is_serialized": bool(row.is_serialized),
                    "currency": currency,
                    "fleet_total": fleet["total"],
                    "fleet_active": fleet["active"],
                    "fleet_out": fleet["out"],
                    "fleet_unavailable": fleet["unavailable"],
                }
            )
        return {"data": {"items": items, "total_count": total, "page": page, "page_size": page_size}}

    @frappe.whitelist(methods=["GET"])
    def get_equipment(item_code: str):
        require_human_staff_role()
        company = get_company_context()
        profile = _profile(company, item_code)
        item = (
            frappe.db.get_value(
                "Item",
                item_code,
                _existing("Item", ["item_name", "description", "image", "item_group", "brand", "stock_uom"]),
                as_dict=True,
            )
            or {}
        )
        holders = _serials_out(company, item_code)
        serials = []
        if profile.is_serialized:
            for row in frappe.get_all(
                "Serial No",
                filters={"company": company, "item_code": item_code},
                fields=_existing("Serial No", ["name", "cortex_status", "warranty_expiry_date", "purchase_rate"]),
                order_by="name asc",
                limit_page_length=500,
            ):
                serials.append(
                    {
                        "serial_no": row.name,
                        "status": row.get("cortex_status") or "Active",
                        "current_rental": holders.get(row.name),
                        "warranty_expiry_date": str(row.get("warranty_expiry_date") or "") or None,
                    }
                )
        raw = profile.required_accessories or ""
        try:
            accessories = (
                frappe.parse_json(raw)
                if raw.lstrip().startswith("[")
                else [a.strip() for a in raw.split(",") if a.strip()]
            )
        except Exception:
            accessories = [a.strip() for a in raw.split(",") if a.strip()]
        return {
            "data": {
                "item_code": item_code,
                "item_name": profile.item_name or item.get("item_name") or item_code,
                "description": item.get("description") or "",
                "image": item.get("image") or None,
                "item_group": item.get("item_group"),
                "brand": item.get("brand"),
                "category": profile.category or "",
                "daily_rate": float(profile.daily_rate or 0),
                "replacement_value": float(profile.replacement_value or 0),
                "deposit_required": float(profile.deposit_required or 0),
                "prep_hours": float(profile.prep_hours or 0),
                "is_serialized": bool(profile.is_serialized),
                "total_quantity": int(profile.total_quantity or 0),
                "is_consignment_allowed": bool(profile.is_consignment_allowed),
                "required_accessories": accessories,
                "currency": frappe.db.get_value("Company", company, "default_currency"),
                "fleet": fleet_summary(company, item_code, bool(profile.is_serialized), profile.total_quantity),
                "serials": serials,
                "pricing_curve": pricing_curve(profile.daily_rate, company),
                "can_edit": bool(set(frappe.get_roles(frappe.session.user)) & CATALOG_MANAGER_ROLES),
            }
        }

    @frappe.whitelist(methods=["POST"])
    def update_equipment_profile(item_code: str, changes: str = None):
        require_human_staff_role()
        _require_catalog_manager()
        company = get_company_context()
        profile = _profile(company, item_code)
        values = frappe.parse_json(changes or "{}") or {}
        unknown = sorted(set(values) - set(EDITABLE_PROFILE_FIELDS))
        if unknown:
            frappe.throw(f"Champs non modifiables : {', '.join(unknown)}", frappe.ValidationError)
        cleaned = {}
        for field, cast in EDITABLE_PROFILE_FIELDS.items():
            if field in values:
                value = cast(values[field]) if values[field] is not None else None
                if cast in (float, int) and value is not None and value < 0:
                    frappe.throw(f"{field} ne peut pas être négatif.", frappe.ValidationError)
                cleaned[field] = value
        if not cleaned:
            frappe.throw("Aucune modification.", frappe.ValidationError)
        doc = frappe.get_doc("Cortex Rental Item Profile", profile.name)
        before = {field: doc.get(field) for field in cleaned}
        doc.update(cleaned)
        doc.save()
        AuditService.record_mutation(
            company=company,
            action="cortex.catalog.profile_updated",
            entity_type="Cortex Rental Item Profile",
            entity_id=doc.name,
            before_state=before,
            after_state=cleaned,
        )
        return get_equipment(item_code)

    @frappe.whitelist(methods=["GET"])
    def get_serial(serial_no: str):
        require_human_staff_role()
        company = get_company_context()
        fields = _existing(
            "Serial No",
            ["name", "item_code", "item_name", "company", "status", "cortex_status", "warranty_expiry_date"],
        )
        serial = frappe.db.get_value("Serial No", serial_no, fields, as_dict=True)
        if not serial or (serial.get("company") and serial.company != company):
            frappe.throw("Numéro de série introuvable pour la société active.", frappe.DoesNotExistError)
        token = f'%"{serial_no}"%'
        rentals = frappe.db.sql(
            """
            SELECT DISTINCT t.name, t.customer, t.rental_state, t.starts_at, t.ends_at
            FROM `tabCortex Rental Transaction Item` ti
            JOIN `tabCortex Rental Transaction` t ON t.name = ti.parent
            WHERE t.company = %(company)s AND (ti.serial_no = %(serial)s OR ti.assigned_serials LIKE %(token)s)
            ORDER BY t.starts_at DESC LIMIT 100
            """,
            {"company": company, "serial": serial_no, "token": token},
            as_dict=True,
        )
        returns = frappe.db.sql(
            """
            SELECT c.name AS checkin, c.transaction, c.checked_in_at, i.condition, i.disposition,
                   i.damage_severity, i.damage_type, i.estimated_repair_cost, i.notes
            FROM `tabCortex Check-In Item` i JOIN `tabCortex Check-In` c ON c.name = i.parent
            WHERE c.company = %(company)s AND i.serial_no = %(serial)s AND c.status = 'Completed'
            ORDER BY c.checked_in_at DESC LIMIT 100
            """,
            {"company": company, "serial": serial_no},
            as_dict=True,
        )
        events = frappe.get_all(
            "Audit Event",
            filters={"company": company, "entity_type": "Serial No", "entity_id": serial_no},
            fields=["name", "creation", "actor_id", "action", "after_state"],
            order_by="creation desc",
            limit_page_length=50,
        )
        return {
            "data": {
                "serial_no": serial.name,
                "item_code": serial.item_code,
                "item_name": serial.get("item_name") or serial.item_code,
                "erpnext_status": serial.get("status"),
                "status": serial.get("cortex_status") or "Active",
                "consignment_owner": serial.get("cortex_consignment_owner") or None,
                "warranty_expiry_date": str(serial.get("warranty_expiry_date") or "") or None,
                "current_rental": _serials_out(company, serial.item_code).get(serial.name),
                "rentals": [
                    {
                        "name": r.name,
                        "customer": r.customer,
                        "rental_state": r.rental_state,
                        "starts_at": str(r.starts_at),
                        "ends_at": str(r.ends_at),
                    }
                    for r in rentals
                ],
                "returns": [
                    {
                        "checkin": r.checkin,
                        "transaction": r.transaction,
                        "checked_in_at": str(r.checked_in_at or ""),
                        "condition": r.condition,
                        "disposition": r.disposition,
                        "damage_severity": r.damage_severity,
                        "damage_type": r.damage_type,
                        "estimated_repair_cost": float(r.estimated_repair_cost or 0),
                        "notes": r.notes or "",
                    }
                    for r in returns
                ],
                "status_history": [
                    {
                        "id": e.name,
                        "timestamp": str(e.creation),
                        "actor": e.actor_id,
                        "action": e.action,
                        "detail": e.after_state or "",
                    }
                    for e in events
                ],
                "can_change_status": bool(set(frappe.get_roles(frappe.session.user)) & CATALOG_MANAGER_ROLES),
            }
        }

    @frappe.whitelist(methods=["POST"])
    def set_serial_status(serial_no: str, status: str, reason: str = None):
        """Quarantine / repair / release: a person with a catalog role, with a reason, audited."""
        require_human_staff_role()
        _require_catalog_manager()
        company = get_company_context()
        if status not in SERIAL_STATUSES:
            frappe.throw("Statut inconnu.", frappe.ValidationError)
        if not reason or len(reason.strip()) < 3:
            frappe.throw("Un motif d’au moins trois caractères est obligatoire.", frappe.ValidationError)
        current = frappe.db.get_value("Serial No", serial_no, ["company", "cortex_status", "item_code"], as_dict=True)
        if not current or (current.company and current.company != company):
            frappe.throw("Numéro de série introuvable pour la société active.", frappe.DoesNotExistError)
        if _serials_out(company, current.item_code).get(serial_no) and status != "Missing":
            frappe.throw(
                "Cette unité est actuellement sortie : son statut se change au retour.", frappe.ValidationError
            )
        frappe.db.set_value("Serial No", serial_no, "cortex_status", status)
        AuditService.record_mutation(
            company=company,
            action="cortex.serial.status_changed",
            entity_type="Serial No",
            entity_id=serial_no,
            before_state={"cortex_status": current.cortex_status or "Active"},
            after_state={"cortex_status": status, "reason": reason.strip()[:500]},
        )
        return get_serial(serial_no)

    @frappe.whitelist(methods=["GET"])
    def list_kits(include_inactive: int = 0):
        require_human_staff_role()
        company = get_company_context()
        filters: Dict[str, Any] = {"company": company}
        if not int(include_inactive or 0):
            filters["is_active"] = 1
        names = frappe.get_list("Cortex Rental Kit", filters=filters, pluck="name", order_by="kit_name asc")
        return {"data": [_kit_payload(frappe.get_doc("Cortex Rental Kit", name)) for name in names]}

    @frappe.whitelist(methods=["POST"])
    def save_kit(kit: str):
        require_human_staff_role()
        _require_catalog_manager()
        company = get_company_context()
        data = frappe.parse_json(kit) if isinstance(kit, str) else kit
        values = {
            "kit_name": (data.get("kit_name") or "").strip(),
            "is_active": 1 if data.get("is_active", True) else 0,
            "discount_percentage": float(data.get("discount_percentage") or 0),
            "description": data.get("description") or "",
            "items": [
                {
                    "item_code": row["item_code"],
                    "qty": float(row.get("qty") or 1),
                    "is_optional": 1 if row.get("is_optional") else 0,
                }
                for row in data.get("items") or []
            ],
        }
        if not values["kit_name"]:
            frappe.throw("Le kit doit avoir un nom.", frappe.ValidationError)
        if not values["items"]:
            frappe.throw("Ajoutez au moins un composant.", frappe.ValidationError)
        if data.get("name"):
            doc = _owned_kit(data["name"], company)
            doc.update({k: v for k, v in values.items() if k != "items"})
            doc.set("items", values["items"])
            doc.save()
            action = "cortex.kit.updated"
        else:
            doc = frappe.get_doc({"doctype": "Cortex Rental Kit", "company": company, **values})
            doc.insert()
            action = "cortex.kit.created"
        AuditService.record_mutation(
            company=company,
            action=action,
            entity_type="Cortex Rental Kit",
            entity_id=doc.name,
            after_state={
                "kit_name": doc.kit_name,
                "items": len(values["items"]),
                "discount": values["discount_percentage"],
            },
        )
        return {"data": _kit_payload(doc)}
