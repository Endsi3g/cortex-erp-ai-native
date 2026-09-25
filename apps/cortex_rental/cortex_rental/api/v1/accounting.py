"""
Cortex Accounting — Profit and Loss Statement.

Human-only financial reporting endpoints. `get_profit_and_loss` reshapes
ERPNext's stock `Profit and Loss Statement` query report
(`erpnext.accounts.report.profit_and_loss_statement`) into the KPI /
period / account-tree shape the Cortex P&L screen renders. ERPNext stays
the accounting engine; nothing here recomputes a ledger.

ERPNext v14/v15 report shape relied on (financial_statements.py):
- `execute()` returns `columns, data, message, chart, report_summary, ...`.
- Period columns are the columns whose `fieldname` is a period key.
- Section totals are rows named `'Total Income (Credit)'` and
  `'Total Expense (Debit)'` — ERPNext wraps these labels in single quotes
  so the report grid does not treat them as account links — and the
  result row is `'Profit for the year'`. Empty `{}` rows separate sections.

NOT VERIFIED AGAINST A LIVE BENCH in this repository's CI (no bench).
If the report raises, the endpoint answers `available: false` with the
reason instead of a zeroed statement, so the screen never shows invented
figures.
"""

from typing import Any, Dict, List, Optional, Tuple

try:
    import frappe
except ImportError:
    frappe = None

from cortex_rental.permissions.agent_scopes import require_finance_role, get_company_context
from cortex_rental.services.audit import AuditService

# Row fields ERPNext's P&L report emits that are never a period column,
# whatever the fiscal year / periodicity filters produce.
_NON_PERIOD_FIELDS = {
    "account",
    "account_name",
    "parent_account",
    "indent",
    "has_value",
    "currency",
    "account_currency",
    "type",
    "is_group",
    "bold",
    "total",
}

# ERPNext emits these as plain rows (matched by label, see module docstring).
_TOTAL_INCOME_PREFIX = "total income"
_TOTAL_EXPENSE_PREFIX = "total expense"
_NET_PROFIT_NAMES = {
    "profit for the year",
    "net profit",
    "net loss",
    "net profit / loss",
    "net profit/loss",
}

PERIODICITIES = ("Monthly", "Quarterly", "Half-Yearly", "Yearly")
REPORT_VIEWS = ("Report", "Growth", "Margin")
_TRUTHY = ("1", "true", "True", 1, True)


def _build_pnl_filters(payload: Dict[str, Any], company: str, dimension_fields: Tuple[str, ...] = ()) -> Dict[str, Any]:
    """
    Maps the P&L filter bar to ERPNext's `profit_and_loss_statement`
    filter keys. `company` is always the server-resolved tenant — never
    taken from `payload`. Accounting dimension filters (e.g. `branch`) are
    only forwarded when `dimension_fields` says the site defines them.
    """
    periodicity = payload.get("periodicity") or "Monthly"
    if periodicity not in PERIODICITIES:
        raise ValueError(f"Unsupported periodicity: {periodicity}")

    filters: Dict[str, Any] = {
        "company": company,
        "periodicity": periodicity,
        "accumulated_values": 1 if payload.get("accumulated_values") in _TRUTHY else 0,
    }

    from_date = payload.get("from_date")
    to_date = payload.get("to_date")
    from_fiscal_year = payload.get("from_fiscal_year") or payload.get("fiscal_year")
    to_fiscal_year = payload.get("to_fiscal_year") or from_fiscal_year

    if from_date and to_date:
        filters["filter_based_on"] = "Date Range"
        filters["period_start_date"] = from_date
        filters["period_end_date"] = to_date
    elif from_fiscal_year:
        filters["filter_based_on"] = "Fiscal Year"
        filters["from_fiscal_year"] = from_fiscal_year
        filters["to_fiscal_year"] = to_fiscal_year
    else:
        raise ValueError("Either a fiscal year or from_date + to_date is required.")

    for key in ("cost_center", "project", "finance_book", "presentation_currency"):
        if payload.get(key):
            filters[key] = payload[key]

    selected_view = payload.get("selected_view")
    if selected_view:
        if selected_view not in REPORT_VIEWS:
            raise ValueError(f"Unsupported report view: {selected_view}")
        filters["selected_view"] = selected_view

    for fieldname in dimension_fields:
        if payload.get(fieldname):
            filters[fieldname] = payload[fieldname]

    if payload.get("include_default_book_entries") in _TRUTHY:
        filters["include_default_book_entries"] = 1

    return filters


def _period_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in columns if c.get("fieldname") and c.get("fieldname") not in _NON_PERIOD_FIELDS]


def _clean_label(value: Any) -> str:
    return str(value or "").strip().strip("'").strip()


def _row_label(row: Dict[str, Any]) -> str:
    return _clean_label(row.get("account_name") or row.get("account"))


def _is_total_income_row(label: str) -> bool:
    return label.lower().startswith(_TOTAL_INCOME_PREFIX)


def _is_total_expense_row(label: str) -> bool:
    return label.lower().startswith(_TOTAL_EXPENSE_PREFIX)


def _is_net_profit_row(label: str) -> bool:
    return label.lower() in _NET_PROFIT_NAMES


def _build_account_tree(rows: List[Dict[str, Any]], period_cols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ERPNext returns a flat, indent-ordered list; rebuild the nested
    `children` shape via a depth stack. `type` ("group" vs "account") is
    derived from whether a node ends up with children.
    """
    roots: List[Dict[str, Any]] = []
    stack: List[Tuple[int, Dict[str, Any]]] = []

    for row in rows:
        depth = int(row.get("indent") or 0)
        node = {
            "id": _clean_label(row.get("account")) or _row_label(row),
            "name": _row_label(row),
            "depth": depth,
            "children": [],
            "values": {c["fieldname"]: row.get(c["fieldname"]) for c in period_cols},
            "total": row.get("total"),
        }

        while stack and stack[-1][0] >= depth:
            stack.pop()

        if stack:
            stack[-1][1]["children"].append(node)
        else:
            roots.append(node)

        stack.append((depth, node))

    def _mark_types(nodes: List[Dict[str, Any]]) -> None:
        for node in nodes:
            node["type"] = "group" if node["children"] else "account"
            _mark_types(node["children"])

    _mark_types(roots)
    return roots


def transform_pnl_report(columns: List[Dict[str, Any]], data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pure transform — no frappe dependency, unit-tested directly against
    ERPNext-shaped `columns`/`data` in `tests/test_accounting_pnl.py`.
    """
    period_cols = _period_columns(columns)

    tree_rows: List[Dict[str, Any]] = []
    total_income_row: Optional[Dict[str, Any]] = None
    total_expense_row: Optional[Dict[str, Any]] = None
    net_profit_row: Optional[Dict[str, Any]] = None

    for row in data:
        label = _row_label(row)
        if not label:
            continue  # section spacer rows
        if _is_total_income_row(label):
            total_income_row = row
        elif _is_total_expense_row(label):
            total_expense_row = row
        elif _is_net_profit_row(label):
            net_profit_row = row
        else:
            tree_rows.append(row)

    accounts = _build_account_tree(tree_rows, period_cols)

    def _val(row: Optional[Dict[str, Any]], fieldname: str) -> float:
        if not row:
            return 0.0
        return float(row.get(fieldname) or 0.0)

    periods = [
        {
            "key": col["fieldname"],
            "label": col.get("label") or col["fieldname"],
            "income": _val(total_income_row, col["fieldname"]),
            "expense": _val(total_expense_row, col["fieldname"]),
            "profitLoss": _val(net_profit_row, col["fieldname"]),
        }
        for col in period_cols
    ]

    total_income = float((total_income_row or {}).get("total") or 0.0) or (periods[-1]["income"] if periods else 0.0)
    total_expense = float((total_expense_row or {}).get("total") or 0.0) or (periods[-1]["expense"] if periods else 0.0)
    net_profit = float((net_profit_row or {}).get("total") or 0.0) or (total_income - total_expense)

    return {
        "totalIncome": total_income,
        "totalExpense": total_expense,
        "netProfit": net_profit,
        "periods": periods,
        "accounts": accounts,
    }


def _accounting_dimensions(company: str) -> List[Dict[str, Any]]:
    """Enabled accounting dimensions (e.g. Branch) with the values usable by this company."""
    if not frappe.db.table_exists("Accounting Dimension"):
        return []
    dimensions = []
    for dim in frappe.get_all(
        "Accounting Dimension",
        filters={"disabled": 0},
        fields=["document_type", "fieldname", "label"],
        order_by="label asc",
    ):
        meta = frappe.get_meta(dim.document_type)
        filters = {"company": company} if meta.has_field("company") else {}
        values = frappe.get_list(dim.document_type, filters=filters, pluck="name", limit_page_length=500)
        dimensions.append({"fieldname": dim.fieldname, "label": dim.label or dim.document_type, "options": values})
    return dimensions


def _fiscal_year_dates(names: List[str]) -> Tuple[Optional[str], Optional[str]]:
    rows = frappe.get_all(
        "Fiscal Year",
        filters={"name": ["in", names]},
        fields=["year_start_date", "year_end_date"],
    )
    if not rows:
        return None, None
    return str(min(r.year_start_date for r in rows)), str(max(r.year_end_date for r in rows))


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_pnl_filter_options():
        require_finance_role()
        company = get_company_context()

        fiscal_years = frappe.get_all(
            "Fiscal Year",
            filters={"disabled": 0},
            fields=["name", "year_start_date", "year_end_date"],
            order_by="year_start_date desc",
        )
        # A fiscal year with company rows only applies to those companies.
        scoped = []
        for fy in fiscal_years:
            companies = frappe.get_all("Fiscal Year Company", filters={"parent": fy.name}, pluck="company")
            if not companies or company in companies:
                scoped.append({"name": fy.name, "start": str(fy.year_start_date), "end": str(fy.year_end_date)})

        today = frappe.utils.getdate()
        current = next(
            (
                fy["name"]
                for fy in scoped
                if frappe.utils.getdate(fy["start"]) <= today <= frappe.utils.getdate(fy["end"])
            ),
            scoped[0]["name"] if scoped else None,
        )

        return {
            "data": {
                "company": company,
                "company_currency": frappe.db.get_value("Company", company, "default_currency"),
                "fiscal_years": scoped,
                "current_fiscal_year": current,
                "finance_books": frappe.get_list(
                    "Finance Book", pluck="name", order_by="name asc", limit_page_length=200
                ),
                "cost_centers": frappe.get_list(
                    "Cost Center",
                    filters={"company": company},
                    pluck="name",
                    order_by="name asc",
                    limit_page_length=500,
                ),
                "projects": frappe.get_list(
                    "Project", filters={"company": company}, pluck="name", order_by="name asc", limit_page_length=500
                ),
                "currencies": frappe.get_all("Currency", filters={"enabled": 1}, pluck="name", order_by="name asc"),
                "dimensions": _accounting_dimensions(company),
                "periodicities": list(PERIODICITIES),
                "report_views": list(REPORT_VIEWS),
            }
        }

    @frappe.whitelist(methods=["GET"])
    def get_profit_and_loss():
        require_finance_role()
        company = get_company_context()
        payload = frappe.local.form_dict

        dimension_fields = tuple(d["fieldname"] for d in _accounting_dimensions(company))
        try:
            filters = _build_pnl_filters(payload, company, dimension_fields)
        except ValueError as exc:
            frappe.throw(str(exc), frappe.ValidationError)

        if filters["filter_based_on"] == "Fiscal Year":
            period_start, period_end = _fiscal_year_dates([filters["from_fiscal_year"], filters["to_fiscal_year"]])
        else:
            period_start, period_end = filters["period_start_date"], filters["period_end_date"]

        try:
            execute = frappe.get_attr(
                "erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement.execute"
            )
            result = execute(frappe._dict(filters))
            columns, data = result[0], result[1] or []
            report = transform_pnl_report(columns, data)
            report["available"] = True
        except Exception:
            frappe.log_error(title="Cortex P&L: ERPNext report failed")
            report = {
                "available": False,
                "reason": "Le rapport ERPNext « Profit and Loss Statement » n’a pas pu être exécuté "
                "pour ces filtres. Le détail est dans le journal d’erreurs du site.",
                "totalIncome": None,
                "totalExpense": None,
                "netProfit": None,
                "periods": [],
                "accounts": [],
            }

        report.update(
            {
                "company": company,
                "currency": filters.get("presentation_currency")
                or frappe.db.get_value("Company", company, "default_currency"),
                "periodStart": period_start,
                "periodEnd": period_end,
                "filters": {k: v for k, v in filters.items() if k != "company"},
            }
        )

        AuditService.record_read(
            action="cortex.accounting.profit_and_loss_viewed",
            metadata={"filters": report["filters"], "available": report["available"]},
            company=company,
        )

        return {"data": report, "meta": {"company": company}}
