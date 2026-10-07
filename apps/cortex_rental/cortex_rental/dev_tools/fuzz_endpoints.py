"""Fuzz HTTP de tous les endpoints exposés : aucune entrée absurde ne doit produire une erreur serveur (5xx).

    1. bench --site cortex.local execute cortex_rental.dev_tools.fuzz_endpoints.prepare      (société et comptes d'essai)
    2. python3 apps/cortex_rental/cortex_rental/dev_tools/fuzz_endpoints.py http://localhost:8000

Pour chaque endpoint (liste lue dans le code source) on envoie des valeurs hostiles : texte immense, injection SQL,
XSS, traversée de chemin, octet nul, Unicode bidirectionnel, nombres extrêmes, JSON cassé ou imbriqué. Deux profils :
un propriétaire et un lecteur (Auditor), plus l'invité pour les appels publics. Les appels coûteux ou qui déconnecteraient
la session d'essai sont exclus. Résultat : /tmp/cortex_fuzz.json (et code de sortie 1 s'il reste des erreurs 5xx).
"""

import ast
import json
import os
import sys
import time

COMPANY = "Société Fuzz (essai)"
OWNER = "fuzz.proprio@example.com"
READER = "fuzz.lecteur@example.com"
PASSWORD = "Sim-Pass-2026!"
OUT = "/tmp/cortex_fuzz.json"

# Effets de bord hors du périmètre d'essai (modèle IA payant, déconnexion de la session de test, mot de passe).
EXCLUDED = {
    "send_message",
    "chat_stream",
    "change_password",
    "sign_out_other_sessions",
    "request_access",
    "resend_verification",
}

HOSTILE_STRINGS = [
    "",
    "x" * 100_000,
    "' OR 1=1 -- ",
    '"; DROP TABLE tabUser; --',
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "../../../../etc/passwd",
    "\x00null\x00",
    "émoji 😀 ‮ rtl",
    '{"a": {"b": {"c": [1,2,3]}}}',
    "[1,2",
    "null",
    "-1",
    "NaN",
    "9" * 40,
    "${jndi:ldap://x/a}",
    "{{7*7}}",
]
HOSTILE_NUMBERS = ["-1", "0", "1000000000000", "abc", "1.7976931348623157e308", "NaN", "-0", "1e-400"]


def _literal(node):
    try:
        return ast.literal_eval(node) if node is not None else None
    except (ValueError, SyntaxError):
        return None


def endpoints(app_dir):
    """(module dotted path, function name, [params]) pour chaque `@frappe.whitelist`; aussi la méthode HTTP déclarée."""
    found = []
    root = os.path.join(app_dir, "api", "v1")
    for name in sorted(os.listdir(root)):
        if not name.endswith(".py") or name.startswith("_"):
            continue
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            decorators = [ast.unparse(d) for d in node.decorator_list]
            marker = next((d for d in decorators if "frappe.whitelist" in d), None)
            if not marker:
                continue
            defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + list(node.args.defaults)
            params = [(a.arg, _literal(d)) for a, d in zip(node.args.args, defaults)]
            found.append(
                {
                    "path": f"cortex_rental.api.v1.{name[:-3]}.{node.name}",
                    "name": node.name,
                    "params": params,
                    "guest": "allow_guest=True" in marker,
                    "get": "'GET'" in marker or '"GET"' in marker,
                }
            )
    return found


def prepare():
    """Société, propriétaire et lecteur d'essai (bench execute)."""
    import frappe

    from cortex_rental.services import access_requests, tenant_provisioning

    frappe.set_user("Administrator")
    for user in (OWNER, READER):
        if frappe.db.exists("User", user):
            frappe.delete_doc("User", user, force=True, ignore_permissions=True)
    if frappe.db.exists("Cortex Onboarding", COMPANY):
        frappe.delete_doc("Cortex Onboarding", COMPANY, force=True, ignore_permissions=True)
    if frappe.db.exists("Company", COMPANY):
        company = COMPANY
    else:
        company = tenant_provisioning.create_company(COMPANY)
    roles = access_requests.split_owner_roles(access_requests.get_settings().owner_roles)
    owner = tenant_provisioning.create_user(OWNER, "Fuzz Propriétaire", company, roles)
    reader = tenant_provisioning.create_user(READER, "Fuzz Lecteur", company, ["Auditor"])
    tenant_provisioning.ensure_onboarding(company, owner)
    for user in (owner, reader):
        frappe.utils.password.update_password(user, PASSWORD)
    frappe.db.commit()
    print({"company": company, "owner": owner, "reader": reader})


def variants(params):
    """Jeux d'arguments : une valeur hostile à la fois pour tous les paramètres, selon leur type par défaut."""
    sets = []
    for value in HOSTILE_STRINGS:
        sets.append({name: value for name, _d in params})
    for value in HOSTILE_NUMBERS:
        sets.append({name: value for name, _d in params})
    # confusion de types : liste / objet JSON à la place d'un texte ou d'un nombre
    sets.append({name: json.dumps(["a", {"b": 1}]) for name, _d in params})
    sets.append({name: json.dumps({"$gt": ""}) for name, _d in params})
    return sets


def run(base="http://localhost:8000"):
    import requests

    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    eps = [e for e in endpoints(app_dir) if e["name"] not in EXCLUDED]
    report = {"endpoints": len(eps), "requests": 0, "five_xx": [], "by_status": {}, "slow": []}

    def login(user):
        s = requests.Session()
        r = s.post(f"{base}/api/method/login", data={"usr": user, "pwd": PASSWORD}, timeout=30)
        r.raise_for_status()
        return s

    profiles = {"propriétaire": login(OWNER), "lecteur": login(READER), "invité": requests.Session()}
    for profile, session in profiles.items():
        for ep in eps:
            if profile == "invité" and not ep["guest"]:
                continue
            for args in variants(ep["params"]) or [{}]:
                url = f"{base}/api/method/{ep['path']}"
                started = time.perf_counter()
                try:
                    if ep["get"]:
                        r = session.get(url, params=args, timeout=60)
                    else:
                        r = session.post(url, data=args, timeout=60)
                except requests.RequestException as error:
                    report["five_xx"].append({"profile": profile, "endpoint": ep["name"], "error": str(error)[:120]})
                    continue
                elapsed = (time.perf_counter() - started) * 1000
                report["requests"] += 1
                key = f"{profile}:{r.status_code}"
                report["by_status"][key] = report["by_status"].get(key, 0) + 1
                if r.status_code >= 500:
                    try:
                        exc = r.json().get("exc_type") or r.json().get("exception", "")[:80]
                    except ValueError:
                        exc = r.text[:80]
                    report["five_xx"].append(
                        {
                            "profile": profile,
                            "endpoint": ep["name"],
                            "status": r.status_code,
                            "exc": exc,
                            "sample": {k: (str(v)[:40]) for k, v in list(args.items())[:2]},
                        }
                    )
                if elapsed > 3000:
                    report["slow"].append({"endpoint": ep["name"], "ms": round(elapsed), "profile": profile})
                if r.status_code == 429:
                    time.sleep(0.05)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    return report


if __name__ == "__main__":
    result = run(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
    print(json.dumps({k: v for k, v in result.items() if k != "five_xx"}, ensure_ascii=False))
    seen = {}
    for item in result["five_xx"]:
        seen.setdefault((item["endpoint"], item.get("exc", item.get("error"))), item)
    print(f"{len(result['five_xx'])} erreurs 5xx, {len(seen)} distinctes")
    for (endpoint, exc), item in sorted(seen.items(), key=lambda kv: str(kv[0])):
        print(" -", endpoint, "|", exc, "|", item.get("sample"))
    sys.exit(1 if result["five_xx"] else 0)
