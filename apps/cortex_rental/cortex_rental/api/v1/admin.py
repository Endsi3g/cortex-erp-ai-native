"""Administration: rental policies, team & roles, audit log.

- Policies: the billable-days curve (Rental Pricing Rule overrides on top
  of the standard curve) and the company's billing settings. Edits are
  audited with before/after values.
- Team: System Manager only. Only human Cortex roles can be granted or
  removed here; agent and System Manager roles never are, nobody edits
  their own roles, and service (agent) accounts are read-only.
- Audit: read-only view of the append-only Audit Event log.
"""

from typing import Any, Dict, List

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import HUMAN_STAFF_ROLES, get_company_context
from cortex_rental.services.audit import AuditService

ADMIN_ROLES = {"System Manager", "Cortex System Manager"}
AGENT_ROLES = {
    "Agent Service Account",
    "Cortex Agent Availability",
    "Cortex Agent Intake",
    "Cortex Agent Reporting",
    "Cortex Migration Worker",
}
# Roles this screen may grant or remove. Everything else a user holds is
# shown but left untouched.
MANAGEABLE_ROLES = [*HUMAN_STAFF_ROLES, "Pricing Manager", "Auditor", "Cortex Read Only"]
SETTINGS_FIELDS = ("advance_percentage", "include_equipment_guarantee", "taxes_and_charges", "damage_item", "loss_item")
CURVE_DAYS = 31


def require_admin() -> None:
    if not frappe:
        return
    roles = set(frappe.get_roles(frappe.session.user))
    if roles & AGENT_ROLES:
        frappe.throw("Action réservée aux personnes.", frappe.PermissionError)
    if frappe.session.user != "Administrator" and not roles & ADMIN_ROLES:
        frappe.throw("Action réservée aux administrateurs.", frappe.PermissionError)


def require_system_manager() -> None:
    if not frappe:
        return
    roles = set(frappe.get_roles(frappe.session.user))
    if roles & AGENT_ROLES:
        frappe.throw("Action réservée aux personnes.", frappe.PermissionError)
    if frappe.session.user != "Administrator" and "System Manager" not in roles:
        frappe.throw("Seul un System Manager peut gérer l’équipe.", frappe.PermissionError)


def role_changes(current: List[str], requested: List[str]) -> Dict[str, List[str]]:
    """Grant/remove sets limited to MANAGEABLE_ROLES; other roles are never touched."""
    unknown = sorted(set(requested) - set(MANAGEABLE_ROLES))
    if unknown:
        raise ValueError(f"Rôles non attribuables ici : {', '.join(unknown)}")
    held = set(current) & set(MANAGEABLE_ROLES)
    wanted = set(requested)
    return {"add": sorted(wanted - held), "remove": sorted(held - wanted)}


def check_role_target(actor: str, target: str, target_roles: List[str]) -> None:
    if target == actor:
        raise PermissionError("Vous ne pouvez pas modifier vos propres rôles.")
    if target in ("Administrator", "Guest"):
        raise PermissionError("Ce compte ne se gère pas ici.")
    if set(target_roles) & AGENT_ROLES:
        raise PermissionError("Les comptes d’agent ne se gèrent pas ici.")


def validate_rule(calendar_days: int, billable_days: float) -> None:
    if calendar_days < 1 or calendar_days > 365:
        raise ValueError("Le nombre de jours calendrier doit être entre 1 et 365.")
    if billable_days <= 0 or billable_days > calendar_days:
        raise ValueError("Les jours facturables doivent être supérieurs à 0 et au plus égaux aux jours calendrier.")


def _company_users(company: str) -> List[str]:
    """Users with access to the company (User Permission), or every system user on a one-company site."""
    users = set(frappe.get_all("User Permission", filters={"allow": "Company", "for_value": company}, pluck="user"))
    if len(frappe.get_all("Company", pluck="name")) == 1:
        users |= set(
            frappe.get_all(
                "User",
                filters={"user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
                pluck="name",
            )
        )
    return sorted(users - {"Administrator", "Guest"})


def _curve(company: str) -> List[Dict[str, Any]]:
    from cortex_rental.services.pricing import PricingService

    rules = {
        int(r.calendar_days): r
        for r in frappe.get_all(
            "Rental Pricing Rule",
            filters={"company": company, "is_active": 1},
            fields=["name", "calendar_days", "billable_days"],
        )
    }
    curve = []
    for days in range(1, CURVE_DAYS + 1):
        start = "2026-01-01T08:00:00"
        end = frappe.utils.add_to_date(start, days=days, as_string=True).replace(" ", "T")
        _cal, billable = PricingService.compute_billable_days(start, end, company)
        curve.append(
            {"calendar_days": days, "billable_days": billable, "source": "rule" if days in rules else "standard"}
        )
    return curve


if frappe:
    # ---- Policies --------------------------------------------------------------

    @frappe.whitelist(methods=["GET"])
    def get_policies():
        from cortex_rental.services.billing import get_settings

        if not frappe.has_permission("Rental Pricing Rule", "read"):
            frappe.throw("Votre rôle ne permet pas de consulter les politiques.", frappe.PermissionError)
        company = get_company_context()
        rules = frappe.get_all(
            "Rental Pricing Rule",
            filters={"company": company},
            fields=["name", "calendar_days", "billable_days", "is_active", "description", "modified", "modified_by"],
            order_by="calendar_days asc",
        )
        return {
            "data": {
                "rules": [
                    {
                        "name": r.name,
                        "calendar_days": int(r.calendar_days),
                        "billable_days": float(r.billable_days or 0),
                        "is_active": bool(r.is_active),
                        "description": r.description or "",
                        "modified": str(r.modified),
                        "modified_by": r.modified_by,
                    }
                    for r in rules
                ],
                "curve": _curve(company),
                "settings": get_settings(company),
                "tax_templates": frappe.get_all(
                    "Sales Taxes and Charges Template", filters={"company": company, "disabled": 0}, pluck="name"
                ),
                "currency": frappe.db.get_value("Company", company, "default_currency"),
                "can_edit_pricing": bool(frappe.has_permission("Rental Pricing Rule", "write")),
                "can_edit_settings": bool(frappe.has_permission("Cortex Company Settings", "write")),
            }
        }

    @frappe.whitelist(methods=["POST"])
    def save_pricing_rule(calendar_days, billable_days, description: str = None, is_active=1):
        if not frappe.has_permission("Rental Pricing Rule", "write"):
            frappe.throw("Votre rôle ne permet pas de modifier la grille.", frappe.PermissionError)
        company = get_company_context()
        calendar_days, billable_days = int(calendar_days), float(billable_days)
        try:
            validate_rule(calendar_days, billable_days)
        except ValueError as exc:
            frappe.throw(str(exc), frappe.ValidationError)
        name = frappe.db.get_value("Rental Pricing Rule", {"company": company, "calendar_days": calendar_days}, "name")
        values = {
            "billable_days": billable_days,
            "description": (description or "").strip()[:500],
            "is_active": 1 if int(is_active) else 0,
        }
        if name:
            doc = frappe.get_doc("Rental Pricing Rule", name)
            before = {k: doc.get(k) for k in values}
            doc.update(values)
            doc.save()
        else:
            abbr = frappe.db.get_value("Company", company, "abbr") or company
            doc = frappe.get_doc(
                {
                    "doctype": "Rental Pricing Rule",
                    "company": company,
                    "rule_name": f"{abbr}-{calendar_days}J",
                    "calendar_days": calendar_days,
                    **values,
                }
            )
            doc.insert()
            before = None
        AuditService.record_mutation(
            company=company,
            action="cortex.policy.pricing_rule_saved",
            entity_type="Rental Pricing Rule",
            entity_id=doc.name,
            before_state=before,
            after_state={"calendar_days": calendar_days, **values},
        )
        return get_policies()

    @frappe.whitelist(methods=["POST"])
    def save_company_settings(values: str):
        if not frappe.has_permission("Cortex Company Settings", "write"):
            frappe.throw("Votre rôle ne permet pas de modifier ces paramètres.", frappe.PermissionError)
        company = get_company_context()
        values = frappe.parse_json(values) or {}
        unknown = sorted(set(values) - set(SETTINGS_FIELDS))
        if unknown:
            frappe.throw(f"Champs non modifiables : {', '.join(unknown)}", frappe.ValidationError)
        if "advance_percentage" in values:
            pct = float(values["advance_percentage"] or 0)
            if pct < 0 or pct > 100:
                frappe.throw("Le pourcentage d’acompte doit être entre 0 et 100.", frappe.ValidationError)
            values["advance_percentage"] = pct
        if "include_equipment_guarantee" in values:
            values["include_equipment_guarantee"] = 1 if values["include_equipment_guarantee"] else 0
        if values.get("taxes_and_charges") and not frappe.db.exists(
            "Sales Taxes and Charges Template", {"name": values["taxes_and_charges"], "company": company}
        ):
            frappe.throw("Modèle de taxes introuvable pour la société.", frappe.ValidationError)
        for field in ("damage_item", "loss_item"):
            if values.get(field) and not frappe.db.exists("Item", values[field]):
                frappe.throw(f"Article {values[field]} introuvable.", frappe.ValidationError)
        if frappe.db.exists("Cortex Company Settings", company):
            doc = frappe.get_doc("Cortex Company Settings", company)
            before = {k: doc.get(k) for k in values}
            doc.update(values)
            doc.save()
        else:
            doc = frappe.get_doc({"doctype": "Cortex Company Settings", "company": company, **values})
            doc.insert()
            before = None
        AuditService.record_mutation(
            company=company,
            action="cortex.policy.company_settings_saved",
            entity_type="Cortex Company Settings",
            entity_id=company,
            before_state=before,
            after_state=values,
        )
        return get_policies()

    # ---- Team & roles ------------------------------------------------------------

    @frappe.whitelist(methods=["GET"])
    def list_team():
        require_system_manager()
        company = get_company_context()
        names = _company_users(company)
        users = frappe.get_all(
            "User",
            filters={"name": ["in", names or [""]]},
            fields=["name", "full_name", "enabled", "last_login", "user_type"],
            order_by="full_name asc",
        )
        role_rows = frappe.get_all(
            "Has Role", filters={"parent": ["in", names or [""]], "parenttype": "User"}, fields=["parent", "role"]
        )
        roles_by_user: Dict[str, List[str]] = {}
        for row in role_rows:
            roles_by_user.setdefault(row.parent, []).append(row.role)
        people, services = [], []
        for user in users:
            roles = sorted(roles_by_user.get(user.name, []))
            entry = {
                "user": user.name,
                "full_name": user.full_name or user.name,
                "enabled": bool(user.enabled),
                "last_login": str(user.last_login) if user.last_login else None,
                "roles": roles,
                "is_self": user.name == frappe.session.user,
            }
            (services if set(roles) & AGENT_ROLES else people).append(entry)
        return {"data": {"users": people, "service_accounts": services, "manageable_roles": MANAGEABLE_ROLES}}

    @frappe.whitelist(methods=["POST"])
    def set_user_roles(user: str, roles: str):
        require_system_manager()
        company = get_company_context()
        if user not in _company_users(company):
            frappe.throw("Utilisateur introuvable pour la société active.", frappe.PermissionError)
        doc = frappe.get_doc("User", user)
        current = [r.role for r in doc.roles]
        try:
            check_role_target(frappe.session.user, user, current)
            changes = role_changes(current, frappe.parse_json(roles) or [])
        except PermissionError as exc:
            frappe.throw(str(exc), frappe.PermissionError)
        except ValueError as exc:
            frappe.throw(str(exc), frappe.ValidationError)
        if not changes["add"] and not changes["remove"]:
            return list_team()
        if changes["add"]:
            doc.add_roles(*changes["add"])
        if changes["remove"]:
            doc.remove_roles(*changes["remove"])
        AuditService.record_mutation(
            company=company,
            action="cortex.team.roles_changed",
            entity_type="User",
            entity_id=user,
            before_state={"roles": sorted(set(current) & set(MANAGEABLE_ROLES))},
            after_state=changes,
        )
        return list_team()

    # ---- Audit log -------------------------------------------------------------------

    def _audit_filters(company, action, entity_type, entity_id, actor, actor_type, from_date, to_date):
        filters: List[Any] = [["company", "=", company]]
        if action:
            filters.append(["action", "like", f"%{action}%"])
        if entity_type:
            filters.append(["entity_type", "=", entity_type])
        if entity_id:
            filters.append(["entity_id", "like", f"%{entity_id}%"])
        if actor:
            filters.append(["actor_id", "like", f"%{actor}%"])
        if actor_type:
            filters.append(["actor_type", "=", actor_type])
        if from_date:
            filters.append(["creation", ">=", f"{from_date} 00:00:00"])
        if to_date:
            filters.append(["creation", "<=", f"{to_date} 23:59:59"])
        return filters

    @frappe.whitelist(methods=["GET"])
    def list_audit_events(
        action: str = None,
        entity_type: str = None,
        entity_id: str = None,
        actor: str = None,
        actor_type: str = None,
        from_date: str = None,
        to_date: str = None,
        page=1,
        page_size=100,
    ):
        if not frappe.has_permission("Audit Event", "read"):
            frappe.throw("Votre rôle ne permet pas de consulter le journal d’audit.", frappe.PermissionError)
        company = get_company_context()
        page, page_size = max(1, int(page)), min(5000, max(1, int(page_size)))
        filters = _audit_filters(company, action, entity_type, entity_id, actor, actor_type, from_date, to_date)
        rows = frappe.get_all(
            "Audit Event",
            filters=filters,
            fields=["name", "creation", "actor_type", "actor_id", "action", "entity_type", "entity_id", "request_id"],
            order_by="creation desc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )
        total = frappe.db.count("Audit Event", filters=filters)
        entity_types = sorted(
            {
                r.entity_type
                for r in frappe.get_all(
                    "Audit Event", filters={"company": company}, fields=["entity_type"], group_by="entity_type"
                )
                if r.entity_type
            }
        )
        return {
            "data": {
                "items": [
                    {
                        "name": r.name,
                        "timestamp": str(r.creation),
                        "actor_type": r.actor_type,
                        "actor_id": r.actor_id,
                        "action": r.action,
                        "entity_type": r.entity_type,
                        "entity_id": r.entity_id,
                        "request_id": r.request_id,
                    }
                    for r in rows
                ],
                "total_count": total,
                "page": page,
                "page_size": page_size,
                "entity_types": entity_types,
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_audit_event(name: str):
        if not frappe.has_permission("Audit Event", "read"):
            frappe.throw("Votre rôle ne permet pas de consulter le journal d’audit.", frappe.PermissionError)
        company = get_company_context()
        if not frappe.db.exists("Audit Event", {"name": name, "company": company}):
            frappe.throw("Événement introuvable pour la société active.", frappe.PermissionError)
        doc = frappe.get_doc("Audit Event", name)

        def parsed(value):
            try:
                return frappe.parse_json(value) if value else None
            except Exception:
                return value

        return {
            "data": {
                "name": doc.name,
                "timestamp": str(doc.creation),
                "actor_type": doc.actor_type,
                "actor_id": doc.actor_id,
                "action": doc.action,
                "entity_type": doc.entity_type,
                "entity_id": doc.entity_id,
                "request_id": doc.request_id,
                "before_state": parsed(doc.before_state),
                "after_state": parsed(doc.after_state),
                "evidence": parsed(doc.evidence),
                "policy_decision": parsed(doc.policy_decision),
            }
        }
