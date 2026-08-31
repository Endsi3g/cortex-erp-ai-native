"""
Cortex Accounting — Profit & Loss Statement.

Human-only financial reporting endpoint. Reshapes ERPNext's stock
`Profit and Loss Statement` query report
(`erpnext.accounts.report.profit_and_loss_statement`) into the
KPI/period/account-tree shape the Cortex Accounting P&L screen renders
(see `docs/design-system-accounting-pnl.md` §20 "Modèle de données").

Deliberately built on ERPNext's own GL/accounting engine rather than a
second one — this app depends on `erpnext` (see `HANDOFF.md`'s
`bench get-app erpnext` step) specifically so DocTypes like GL Entry,
Fiscal Year, and this report already exist and are already correct
double-entry accounting. Reimplementing that here would duplicate a
system ERPNext already owns.

NOT VERIFIED AGAINST A LIVE BENCH — same caveat as every other Frappe
integration point in this app (see `HANDOFF.md` §2/§3: no bench
accessible in this sandbox). `transform_pnl_report` below is written
against ERPNext v14/v15's documented `execute()` return shape
(`columns, data, message, chart, report_summary[, primitive_summary]`)
and the row/column field names that report uses (`account`,
`account_name`, `indent`, period key = column `fieldname`, a
"Total Income"/"Total Expense"/"Net Profit" row per section rather than
an explicit flag). If a real bench's ERPNext version returns a
different shape, this will raise or return an empty/garbled table
rather than silently show wrong numbers — report that back so these
field-name assumptions can be corrected against the real thing, per the
practice already established in `HANDOFF.md`.
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

# ERPNext's report emits these as plain rows (account_name), not via a
# dedicated "is this a total" flag — matched by name here.
_TOTAL_INCOME_PREFIX = "total income"
_TOTAL_EXPENSE_PREFIX = "total expense"
_NET_PROFIT_NAMES = {"net profit", "net loss", "net profit / loss", "net profit/loss"}


def _build_pnl_filters(payload: Dict[str, Any], company: str) -> Dict[str, Any]:
    """
    Maps the P&L toolbar's fields (`design-system-accounting-pnl.md`
    §10) to ERPNext's `profit_and_loss_statement` filter keys. `company`
    is always the server-resolved tenant — never taken from `payload`
    (same multi-tenant invariant as every other endpoint in this app).

    Only forwards filters that are real, documented ERPNext filters for
    this report. `Branch` and `Report View` from the design's toolbar
    mockup have no equivalent here — left disabled/UI-only on the
    frontend rather than sent to a filter that doesn't exist (the same
    "don't build a dead link" rule `design-system.md` already applies
    to unwired state tokens).
    """
    truthy = ("1", "true", "True")
    filters: Dict[str, Any] = {
        "company": company,
        "periodicity": payload.get("periodicity") or "Monthly",
        "accumulated_values": 1 if str(payload.get("accumulated_values") or "0") in truthy else 0,
    }

    from_date = payload.get("from_date")
    to_date = payload.get("to_date")
    fiscal_year = payload.get("fiscal_year")

    if from_date and to_date:
        filters["filter_based_on"] = "Date Range"
        filters["period_start_date"] = from_date
        filters["period_end_date"] = to_date
    elif fiscal_year:
        filters["filter_based_on"] = "Fiscal Year"
        filters["from_fiscal_year"] = fiscal_year
        filters["to_fiscal_year"] = fiscal_year
    else:
        raise ValueError("Either fiscal_year or from_date+to_date is required.")

    for key in ("cost_center", "project", "finance_book", "presentation_currency"):
        if payload.get(key):
            filters[key] = payload[key]

    if str(payload.get("include_default_book_entries") or "0") in truthy:
        filters["include_default_book_entries"] = 1

    return filters


def _period_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in columns if c.get("fieldname") not in _NON_PERIOD_FIELDS]


def _row_label(row: Dict[str, Any]) -> str:
    return row.get("account_name") or row.get("account") or ""


def _is_total_income_row(label: str) -> bool:
    return label.strip().lower().startswith(_TOTAL_INCOME_PREFIX)


def _is_total_expense_row(label: str) -> bool:
    return label.strip().lower().startswith(_TOTAL_EXPENSE_PREFIX)


def _is_net_profit_row(label: str) -> bool:
    return label.strip().lower() in _NET_PROFIT_NAMES


def _build_account_tree(rows: List[Dict[str, Any]], period_cols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ERPNext returns a flat, indent-ordered list (how the generic Query
    Report table renders it) — rebuilds the nested `children` shape
    `design-system-accounting-pnl.md` §20's `AccountRow` type expects,
    via a depth stack. `type` ("group" vs "account") is derived from
    whether a node ends up with children, not from an ERPNext field —
    `has_value`'s exact leaf/group semantics aren't reliable enough
    across versions to trust blind.
    """
    roots: List[Dict[str, Any]] = []
    stack: List[Tuple[int, Dict[str, Any]]] = []

    for row in rows:
        depth = int(row.get("indent") or 0)
        node = {
            "id": row.get("account") or _row_label(row),
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
    synthetic ERPNext-shaped `columns`/`data` in
    `tests/test_accounting_pnl.py` (no bench required for that part).
    """
    period_cols = _period_columns(columns)

    tree_rows: List[Dict[str, Any]] = []
    total_income_row: Optional[Dict[str, Any]] = None
    total_expense_row: Optional[Dict[str, Any]] = None
    net_profit_row: Optional[Dict[str, Any]] = None

    for row in data:
        label = _row_label(row)
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
    total_expense = float((total_expense_row or {}).get("total") or 0.0) or (
        periods[-1]["expense"] if periods else 0.0
    )
    net_profit = float((net_profit_row or {}).get("total") or 0.0) or (total_income - total_expense)

    return {
        "totalIncome": total_income,
        "totalExpense": total_expense,
        "netProfit": net_profit,
        "periods": periods,
        "accounts": accounts,
    }


if frappe:

    @frappe.whitelist(methods=["GET"])
    def get_profit_and_loss():
        require_finance_role()
        company = get_company_context()
        payload = frappe.local.form_dict

        filters = _build_pnl_filters(payload, company)

        execute = frappe.get_attr(
            "erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement.execute"
        )
        result = execute(frappe._dict(filters))
        columns, data = result[0], result[1] or []

        report = transform_pnl_report(columns, data)
        report["company"] = company
        report["fiscalYear"] = filters.get("from_fiscal_year") or filters.get("period_start_date")
        report["financeBook"] = filters.get("finance_book") or ""

        AuditService.record_read(
            action="cortex.accounting.profit_and_loss_viewed",
            metadata={"filters": {k: v for k, v in filters.items() if k != "company"}},
            company=company,
        )

        return {"data": report, "meta": {"company": company}}
