"""
A small in-memory stand-in for `frappe`, so the code paths guarded by
`if frappe:` can run in plain pytest (no bench in CI).

It is deliberately strict where the real framework is strict and where
bugs have slipped through before: `get_doc(...).insert()` validates the
payload against the DocType JSON shipped in this app — unknown fields and
missing mandatory fields raise, exactly like `bench` would.

Usage:
    with fake_frappe(user="ops@x", roles=["Rental Operator"]) as frappe:
        frappe.tables["Company"] = [{"name": "A"}, {"name": "B"}]
        module = load("cortex_rental.permissions.agent_scopes")
        ...
"""

import contextlib
import importlib
import json
import pathlib
import sys
import types
from typing import Any, Dict, Iterator, List, Optional

DOCTYPE_DIR = pathlib.Path(__file__).resolve().parents[1] / "cortex_rental" / "doctype"
_NON_DATA_FIELDTYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading"}
_STANDARD_FIELDS = {"doctype", "name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}


class FakeFrappeException(Exception):
    pass


class ValidationError(FakeFrappeException):
    pass


class PermissionError(FakeFrappeException):  # noqa: A001 - mirrors frappe.PermissionError
    pass


class DoesNotExistError(FakeFrappeException):
    pass


class AuthenticationError(FakeFrappeException):
    pass


class _Dict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value


def _load_doctype_schemas() -> Dict[str, Dict[str, Any]]:
    schemas = {}
    for path in DOCTYPE_DIR.glob("*/*.json"):
        data = json.loads(path.read_text())
        if data.get("doctype") == "DocType":
            schemas[data["name"]] = data
    return schemas


SCHEMAS = _load_doctype_schemas()


def _matches(row: Dict[str, Any], filters: Any) -> bool:
    if not filters:
        return True
    items = (
        filters.items()
        if isinstance(filters, dict)
        else [(f[0], f[1:]) if len(f) == 3 else (f[1], f[2:]) for f in filters]
    )
    for key, condition in items:
        value = row.get(key)
        if isinstance(condition, (list, tuple)) and len(condition) == 2 and isinstance(condition[0], str):
            op, expected = condition
            op = op.lower()
            if op == "in" and value not in expected:
                return False
            if op == "not in" and value in expected:
                return False
            if op == "!=" and value == expected:
                return False
            if op == "like" and str(expected).strip("%").lower() not in str(value or "").lower():
                return False
            if op in (">=", "<=", ">", "<"):
                if value is None or not eval(f"value {op} expected"):  # noqa: S307 - test helper
                    return False
        elif value != condition:
            return False
    return True


class FakeDB:
    def __init__(self, frappe_module: "FakeFrappe"):
        self._frappe = frappe_module

    def table_exists(self, doctype: str) -> bool:
        return doctype in self._frappe.tables

    def exists(self, doctype: str, filters: Any = None) -> bool:
        rows = self._frappe.tables.get(doctype, [])
        if isinstance(filters, str):
            return any(r.get("name") == filters for r in rows)
        return any(_matches(r, filters) for r in rows)

    def get_value(self, doctype: str, filters: Any, fieldname: Any = "name", as_dict: bool = False):
        rows = self._frappe.tables.get(doctype, [])
        match = next(
            (r for r in rows if (r.get("name") == filters if isinstance(filters, str) else _matches(r, filters))), None
        )
        if match is None:
            return None
        if isinstance(fieldname, (list, tuple)):
            data = _Dict({f: match.get(f) for f in fieldname})
            return data if as_dict else tuple(data.values())
        return match.get(fieldname)

    def count(self, doctype: str, filters: Any = None) -> int:
        return len([r for r in self._frappe.tables.get(doctype, []) if _matches(r, filters)])

    def escape(self, value: str) -> str:
        return "'" + str(value).replace("'", "\\'") + "'"

    def commit(self) -> None:
        pass

    def get_single_value(self, doctype: str, fieldname: str):
        return self._frappe.singles.get(doctype, {}).get(fieldname)

    def has_column(self, doctype: str, column: str) -> bool:
        return True

    def savepoint(self, name: str) -> None:
        self._frappe.savepoints[name] = {k: [dict(r) for r in v] for k, v in self._frappe.tables.items()}

    def rollback(self, save_point: Optional[str] = None) -> None:
        snapshot = self._frappe.savepoints.get(save_point)
        if snapshot is not None:
            self._frappe.tables = {k: [dict(r) for r in v] for k, v in snapshot.items()}


class FakeDoc(_Dict):
    def __init__(self, frappe_module: "FakeFrappe", data: Dict[str, Any]):
        super().__init__(data)
        object.__setattr__(self, "_frappe", frappe_module)
        object.__setattr__(self, "flags", _Dict())

    def insert(self, ignore_permissions: bool = False):
        self._frappe.validate_against_schema(self)
        self.setdefault("name", f"{self['doctype']}-{len(self._frappe.tables.get(self['doctype'], [])) + 1}")
        self._frappe.tables.setdefault(self["doctype"], []).append(dict(self))
        self._frappe.inserted.append(dict(self))
        return self

    def db_set(self, fieldname: Any, value: Any = None):
        updates = fieldname if isinstance(fieldname, dict) else {fieldname: value}
        self.update(updates)
        for row in self._frappe.tables.get(self.get("doctype"), []):
            if row.get("name") == self.get("name"):
                row.update(updates)

    def save(self, ignore_permissions: bool = False):
        self._frappe.validate_against_schema(self)
        return self


class FakeFrappe(types.ModuleType):
    ValidationError = ValidationError
    PermissionError = PermissionError
    DoesNotExistError = DoesNotExistError
    AuthenticationError = AuthenticationError

    def __init__(self, user: str, roles: List[str]):
        super().__init__("frappe")
        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        self.singles: Dict[str, Dict[str, Any]] = {}
        self.savepoints: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self.link_guard: Dict[str, str] = {}  # "doctype:name" -> reason delete_doc must refuse
        self.inserted: List[Dict[str, Any]] = []
        self.roles_by_user: Dict[str, List[str]] = {user: list(roles)}
        self.session = _Dict(user=user)
        self.local = _Dict(form_dict=_Dict(), request=None, flags=_Dict())
        self.flags = _Dict()
        self.conf = _Dict()
        self.db = FakeDB(self)
        self.utils = types.SimpleNamespace()
        self._dict = _Dict

    # --- framework surface used by Cortex -------------------------------
    def get_roles(self, user: Optional[str] = None) -> List[str]:
        return list(self.roles_by_user.get(user or self.session.user, []))

    def throw(self, message: str, exc: type = ValidationError):
        raise exc(message)

    def get_all(
        self,
        doctype: str,
        filters: Any = None,
        fields: Any = None,
        pluck: Optional[str] = None,
        order_by: Optional[str] = None,
        limit_page_length: Optional[int] = None,
        **_: Any,
    ):
        rows = [r for r in self.tables.get(doctype, []) if _matches(r, filters)]
        if limit_page_length:
            rows = rows[:limit_page_length]
        if pluck:
            return [r.get(pluck) for r in rows]
        if _.get("as_list") and fields:
            return [tuple(r.get(f) for f in fields) for r in rows]
        return [_Dict(r) for r in rows]

    get_list = get_all

    def get_doc(self, data: Any, name: Optional[str] = None) -> FakeDoc:
        if isinstance(data, dict):
            return FakeDoc(self, data)
        row = next((r for r in self.tables.get(data, []) if r.get("name") == name), None)
        if row is None:
            raise DoesNotExistError(f"{data} {name} not found")
        return FakeDoc(self, dict(row, doctype=data))

    def delete_doc(self, doctype: str, name: str, **_: Any) -> None:
        reason = self.link_guard.get(f"{doctype}:{name}")
        if reason:
            raise ValidationError(reason)
        self.tables[doctype] = [r for r in self.tables.get(doctype, []) if r.get("name") != name]

    def as_json(self, value: Any) -> str:
        return json.dumps(value, default=str)

    def parse_json(self, value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value

    def generate_hash(self, length: int = 10) -> str:
        return "h" * length

    def whitelist(self, *args: Any, **kwargs: Any):
        if args and callable(args[0]):
            return args[0]
        return lambda fn: fn

    # --- strictness ------------------------------------------------------
    def validate_against_schema(self, doc: Dict[str, Any]) -> None:
        schema = SCHEMAS.get(doc.get("doctype"))
        if not schema:
            return  # ERPNext core doctypes are not modelled here
        fields = {f["fieldname"]: f for f in schema["fields"] if f["fieldtype"] not in _NON_DATA_FIELDTYPES}
        unknown = sorted(k for k in doc if k not in fields and k not in _STANDARD_FIELDS)
        if unknown:
            raise ValidationError(f"{doc['doctype']}: unknown field(s) {unknown}")
        missing = sorted(
            name
            for name, f in fields.items()
            if f.get("reqd") and doc.get(name) in (None, "", []) and not f.get("default")
        )
        if missing:
            raise ValidationError(f"{doc['doctype']}: missing mandatory field(s) {missing}")
        for name, f in fields.items():
            if f["fieldtype"] == "Select" and doc.get(name) not in (None, ""):
                options = [o for o in (f.get("options") or "").split("\n") if o]
                if options and doc[name] not in options:
                    raise ValidationError(f"{doc['doctype']}.{name}: {doc[name]!r} not in {options}")


@contextlib.contextmanager
def fake_frappe(user: str = "staff@cortex.test", roles: Optional[List[str]] = None) -> Iterator[FakeFrappe]:
    """Install a FakeFrappe as `frappe` for the duration of the block."""
    previous = sys.modules.get("frappe")
    fake = FakeFrappe(user, roles or [])
    sys.modules["frappe"] = fake
    reloaded = []
    try:
        yield fake
    finally:
        if previous is None:
            sys.modules.pop("frappe", None)
        else:
            sys.modules["frappe"] = previous
        # Modules loaded with the fake must not leak it into other tests.
        for name in [m for m in sys.modules if m.startswith("cortex_rental.")]:
            module = sys.modules[name]
            if getattr(module, "frappe", None) is fake:
                reloaded.append(name)
        for name in reloaded:
            importlib.reload(sys.modules[name])


def load(module_name: str):
    """(Re)import a Cortex module so it binds the currently installed `frappe`."""
    module = importlib.import_module(module_name)
    return importlib.reload(module)
