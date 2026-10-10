#!/usr/bin/env python3
"""Faux serveur « generateContent » de Gemini, POUR LES ESSAIS DE BOUT EN BOUT SEULEMENT (jamais en production).

Pourquoi : tester toute la chaîne (message → passerelle → fournisseur → outils → cartes → approbation) sans clé réelle.
Ce que ça prouve : le protocole (forme de la requête, boucle d'outils, signatures, erreurs) et le comportement de Cortex.
Ce que ça ne prouve PAS : ce qu'un vrai modèle déciderait. Le « modèle » ici suit des scénarios codés qui utilisent les
résultats réels des outils (identifiants de clients, d'articles, de factures) : rien n'est inventé côté données.

La requête est validée comme le ferait l'API réelle (types en majuscules, aucun `parameters` vide, rôles qui alternent,
fonctions appelées dans la liste déclarée, clé d'API) : un défaut de protocole de Cortex devient une erreur 400 lisible ici.

Lancer :  python3 fake_gemini.py [port] [clé attendue]     (défaut 9911, « fake-gemini-key »)
Site : bench --site <site> set-config cortex_ai_gemini_base_url http://127.0.0.1:9911/v1beta
"""

import json
import re
import sys
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 9911
KEY = "fake-gemini-key"  # remplacés par les arguments de la ligne de commande au lancement (voir __main__)
LOG = "/tmp/fake_gemini.log"
TYPES = {"STRING", "NUMBER", "INTEGER", "BOOLEAN", "ARRAY", "OBJECT"}
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
STATE = {"count_429": 0}


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


# --- validation du protocole -------------------------------------------------------------------------------------------


def check_schema(node, path, problems):
    if not isinstance(node, dict):
        problems.append(f"{path}: schéma attendu")
        return
    kind = node.get("type")
    if kind not in TYPES:
        problems.append(f"{path}.type: « {kind} » n'est pas un type valide ({', '.join(sorted(TYPES))})")
    if str(kind).upper() == "OBJECT":
        props = node.get("properties")
        if not props:
            problems.append(f"{path}.properties: ne doit pas être vide pour un OBJECT")
        else:
            for name, spec in props.items():
                check_schema(spec, f"{path}.properties.{name}", problems)
        required = node.get("required")
        if required is not None:
            if not required:
                problems.append(f"{path}.required: ne doit pas être une liste vide")
            for name in required or []:
                if name not in (props or {}):
                    problems.append(f"{path}.required: « {name} » n'est pas une propriété")
    if str(kind).upper() == "ARRAY":
        if "items" not in node:
            problems.append(f"{path}.items: obligatoire pour un ARRAY")
        else:
            check_schema(node["items"], f"{path}.items", problems)


def validate(body):
    problems = []
    contents = body.get("contents") or []
    if not contents:
        problems.append("contents: vide")
    if contents and contents[0].get("role") != "user":
        problems.append("contents[0].role doit être « user »")
    last_calls = None
    for i, content in enumerate(contents):
        role, parts = content.get("role"), content.get("parts") or []
        if role not in ("user", "model"):
            problems.append(f"contents[{i}].role: « {role} » invalide")
        if not parts:
            problems.append(f"contents[{i}].parts: vide")
        calls = [p["functionCall"]["name"] for p in parts if "functionCall" in p]
        resps = [p["functionResponse"]["name"] for p in parts if "functionResponse" in p]
        if resps:
            if role != "user" or last_calls is None:
                problems.append(f"contents[{i}]: functionResponse sans functionCall juste avant")
            elif sorted(resps) != sorted(last_calls):
                problems.append(f"contents[{i}]: les réponses {resps} ne correspondent pas aux appels {last_calls}")
        last_calls = calls or None
    declared = set()
    for t in body.get("tools") or []:
        for d in t.get("functionDeclarations") or []:
            name = d.get("name", "")
            if not NAME_RE.match(name):
                problems.append(f"functionDeclarations: nom « {name} » invalide")
            if not d.get("description"):
                problems.append(f"{name}: description obligatoire")
            if "parameters" in d:
                check_schema(d["parameters"], f"{name}.parameters", problems)
            declared.add(name)
    return problems, declared


# --- scénarios -----------------------------------------------------------------------------------------------------------

NUMBERS = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5}
MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}
ITEM_WORDS = {"led": "LED", "panneau": "LED", "trepied": "Trépied", "camera": "Alexa", "objectif": "Cooke"}


def current_turn(contents):
    """Question courante = dernier message texte de la personne; puis les échanges d'outils de ce tour."""
    index = max(
        (i for i, c in enumerate(contents) if c.get("role") == "user" and any("text" in p for p in c.get("parts", []))),
        default=0,
    )
    question = " ".join(p.get("text", "") for p in contents[index].get("parts", []))
    exchanges = []  # [(appels, réponses)]
    pending = None
    for c in contents[index + 1 :]:
        parts = c.get("parts", [])
        if c.get("role") == "model":
            pending = [p["functionCall"] for p in parts if "functionCall" in p]
        elif pending is not None:
            exchanges.append((pending, [p["functionResponse"] for p in parts if "functionResponse" in p]))
            pending = None
    return question, exchanges


def responses(exchanges, tool):
    out = []
    for calls, resps in exchanges:
        for r in resps:
            if r["name"] == tool:
                out.append(r["response"].get("result", {}))
    return out


def parse_quote(question):
    q = plain(question)
    customer = re.search(r"pour (.+?)(?: du | le |, | avec )", q)
    name = None
    if customer:
        start = plain(question).index(customer.group(1))
        name = question[start : start + len(customer.group(1))].strip()
    dates = re.search(r"du (\d{1,2}) au (\d{1,2}) (\w+)", q)
    items = []
    for m in re.finditer(r"(un|une|deux|trois|quatre|cinq|\d+)\s+(?:de\s+|des\s+)?(\w+)", q):
        word = m.group(2).rstrip("sx") if m.group(2) not in ITEM_WORDS else m.group(2)
        if word in ITEM_WORDS and not any(i["keyword"] == ITEM_WORDS[word] for i in items):
            qty = NUMBERS.get(m.group(1)) or int(m.group(1))
            items.append({"keyword": ITEM_WORDS[word], "quantity": qty})
    if not (name and dates and items):
        return None
    month = MONTHS.get(dates.group(3), 11)
    return {
        "name": name,
        "starts_at": f"2026-{month:02d}-{int(dates.group(1)):02d} 09:00:00",
        "ends_at": f"2026-{month:02d}-{int(dates.group(2)):02d} 18:00:00",
        "items": items,
    }


def say(text):
    return {"text": text}


def call(name, args):
    return {"functionCall": {"name": name, "args": args}}


def scenario(question, exchanges, declared):
    q = plain(question)
    n = len(exchanges)

    def need(*names):
        missing = [x for x in names if x not in declared]
        return say("Je n'ai pas accès à l'outil nécessaire (" + ", ".join(missing) + ").") if missing else None

    if re.search(r"retenue", q):
        miss = need("list_rentals", "propose_release_hold")
        if miss:
            return [miss]
        if n == 0:
            return [call("list_rentals", {"state": "Quote", "limit": 5})]
        rentals = (responses(exchanges, "list_rentals") or [{}])[0].get("rentals") or []
        if not rentals:
            return [say("Aucun devis ne retient de matériel.")]
        if n == 1:
            return [
                call(
                    "propose_release_hold",
                    {
                        "rental": rentals[0]["name"],
                        "reason": f"Vous demandez de libérer la retenue; {rentals[0]['name']} est le devis le plus récent.",
                    },
                )
            ]
        return [say("Voici la libération à approuver.")]
    if "devis" in q:
        plan = parse_quote(question)
        if not plan:
            return [
                say(
                    "Pour préparer un devis, j'ai besoin du client, des dates et de l'équipement. Par exemple : « devis pour Studio Boréal du 24 au 27 novembre avec deux panneaux LED »."
                )
            ]
        miss = need("search_customers", "search_rental_items", "check_inventory_availability", "propose_create_quote")
        if miss:
            return [miss]
        if n == 0:
            return [call("search_customers", {"query": plan["name"]})]
        if n == 1:
            return [call("search_rental_items", {"query": i["keyword"]}) for i in plan["items"]]
        customers = (responses(exchanges, "search_customers") or [{}])[0].get("customers") or []
        if not customers:
            return [say(f"Je ne trouve pas le client « {plan['name']} ». Voulez-vous que je propose de le créer ?")]
        found = [(r.get("items") or [None])[0] for r in responses(exchanges, "search_rental_items")]
        if not all(found):
            return [say("Je ne retrouve pas tout l'équipement demandé dans le catalogue.")]
        if n == 2:
            return [
                call(
                    "check_inventory_availability",
                    {
                        "item_code": f["item_code"],
                        "starts_at": plan["starts_at"],
                        "ends_at": plan["ends_at"],
                        "quantity": i["quantity"],
                    },
                )
                for f, i in zip(found, plan["items"])
            ]
        checks = [c for r in responses(exchanges, "check_inventory_availability") for c in r.get("results", [])]
        if any(not c.get("is_available") for c in checks):
            return [
                say(
                    "Une partie du matériel n'est pas disponible sur cette période : je ne propose pas de devis. Voulez-vous d'autres dates ?"
                )
            ]
        if n == 3:
            return [
                call(
                    "propose_create_quote",
                    {
                        "customer": customers[0]["name"],
                        "starts_at": plan["starts_at"],
                        "ends_at": plan["ends_at"],
                        "items": [
                            {"item_code": f["item_code"], "quantity": i["quantity"]}
                            for f, i in zip(found, plan["items"])
                        ],
                        "reason": f"Vous avez demandé un devis pour {customers[0]['customer_name']}; le client et le matériel existent et sont libres sur la période.",
                    },
                )
            ]
        return [
            say("J'ai préparé le devis ci-dessous. Vérifiez l'aperçu : rien n'est créé tant que vous n'approuvez pas.")
        ]
    if re.search(r"paie|paye|cheque", q) and "factur" in q:
        miss = need("list_invoices", "propose_record_payment")
        if miss:
            return [miss]
        if n == 0:
            return [call("list_invoices", {"limit": 10})]
        invoices = [
            i
            for i in ((responses(exchanges, "list_invoices") or [{}])[0].get("invoices") or [])
            if i.get("status") in ("Issued", "Partially Paid") and float(i.get("balance") or 0) > 0
        ]
        if not invoices:
            return [say("Je ne trouve aucune facture ouverte.")]
        if n == 1:
            inv = invoices[0]
            return [
                call(
                    "propose_record_payment",
                    {
                        "invoice": inv["name"],
                        "amount": inv["balance"],
                        "method": "Cheque" if "cheque" in q else "Card",
                        "reference": "CH-1001",
                        "reason": f"Vous indiquez qu'un paiement a été reçu; la facture {inv['name']} est la plus récente avec un solde de {inv['balance']} $.",
                    },
                )
            ]
        return [say("Voici le paiement à enregistrer ci-dessous. Vérifiez le montant avant d'approuver.")]
    if re.search(r"factur|situation|statistique", q) and "paiement" not in q and "payee" not in q:
        miss = need("finance_summary", "finance_trend", "rentals_by_state")
        if miss:
            return [miss]
        if n == 0:
            return [call("finance_summary", {}), call("finance_trend", {"months": 6}), call("rentals_by_state", {})]
        return [say("Voici la situation de votre société, tirée de vos données.")]
    return [
        say(
            "Je peux consulter vos locations, votre facturation et vos disponibilités, et préparer un devis, un paiement ou une libération de retenue pour approbation. Que voulez-vous faire ?"
        )
    ]


# --- serveur -------------------------------------------------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencieux
        pass

    def reply(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        match = re.match(r"^/v1beta/models/([^:]+):generateContent$", self.path)
        if not match:
            return self.reply(404, {"error": {"code": 404, "message": "Not found", "status": "NOT_FOUND"}})
        if self.headers.get("x-goog-api-key") != KEY:
            return self.reply(
                403, {"error": {"code": 403, "message": "API key not valid.", "status": "PERMISSION_DENIED"}}
            )
        model = match.group(1)
        if model.startswith("gemini-inexistant"):
            return self.reply(
                404, {"error": {"code": 404, "message": f"models/{model} is not found", "status": "NOT_FOUND"}}
            )
        problems, declared = validate(body)
        if problems:
            self.log("400", model, problems)
            return self.reply(
                400,
                {
                    "error": {
                        "code": 400,
                        "message": "Invalid JSON payload: " + "; ".join(problems[:6]),
                        "status": "INVALID_ARGUMENT",
                    }
                },
            )
        question, exchanges = current_turn(body.get("contents", []))
        if "[panne]" in question:
            return self.reply(
                503, {"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}}
            )
        if "[limite]" in question and STATE["count_429"] == 0:
            STATE["count_429"] += 1
            return self.reply(
                429, {"error": {"code": 429, "message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}}
            )
        parts = scenario(question, exchanges, declared)
        used = len(json.dumps(body)) // 4
        self.log(
            "200",
            model,
            [list(p)[0] if "functionCall" not in p else "call:" + p["functionCall"]["name"] for p in parts],
            question[:60],
        )
        self.reply(
            200,
            {
                "candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}],
                "usageMetadata": {
                    "promptTokenCount": used,
                    "candidatesTokenCount": 40 * len(parts),
                    "totalTokenCount": used + 40 * len(parts),
                },
            },
        )

    def log(self, status, model, detail, question=""):
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"status": status, "model": model, "detail": detail, "question": question}, ensure_ascii=False
                )
                + "\n"
            )


if __name__ == "__main__":
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    KEY = sys.argv[2] if len(sys.argv) > 2 else KEY
    print(f"Faux Gemini sur http://127.0.0.1:{PORT}/v1beta (clé « {KEY} »)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
