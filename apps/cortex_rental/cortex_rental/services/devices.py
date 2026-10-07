"""Appareils connectés : qui s'est connecté, depuis quel appareil, quel système, quelle adresse IP, et la
déconnexion à distance.

Frappe ne garde dans sa table de sessions que l'adresse IP et l'heure. À l'ouverture d'une session, on conserve donc
en plus l'agent utilisateur (navigateur, système, type d'appareil) dans « Cortex Device Session ». L'identifiant de
session n'est jamais stocké en clair : seulement son empreinte SHA-256. Une session ouverte avant cette
fonctionnalité apparaît comme « appareil non identifié » (on ne devine rien).

Limites honnêtes : l'agent utilisateur est déclaré par le navigateur (il peut être modifié) ; l'adresse IP est celle
que voit le serveur (derrière un proxy, celle du proxy si l'en-tête de transfert n'est pas configuré) ; aucun lieu
n'est déduit de l'adresse IP.
"""

import hashlib
import re
from typing import Any, Dict, Optional

try:
    import frappe
    from frappe.utils import now_datetime
except ImportError:
    frappe = None

DEVICE_DOCTYPE = "Cortex Device Session"
TYPE_LABELS = {"Computer": "Ordinateur", "Phone": "Téléphone", "Tablet": "Tablette", "Other": "Autre"}

# Ordre important : Edge et Opera contiennent « Chrome », Chrome contient « Safari ».
_BROWSERS = [
    ("Edge", re.compile(r"\bEdg(?:e|A|iOS)?/([\d.]+)")),
    ("Opera", re.compile(r"\bOPR/([\d.]+)")),
    ("Samsung Internet", re.compile(r"\bSamsungBrowser/([\d.]+)")),
    ("Firefox", re.compile(r"\b(?:Firefox|FxiOS)/([\d.]+)")),
    ("Chrome", re.compile(r"\b(?:Chrome|CriOS)/([\d.]+)")),
    ("Safari", re.compile(r"\bVersion/([\d.]+).*Safari/")),
]


def _major(version: str) -> str:
    return (version or "").split(".")[0]


def parse_user_agent(agent: str) -> Dict[str, str]:
    """Décrit un agent utilisateur : navigateur, système, type d'appareil et modèle. Vide si l'agent est absent."""
    agent = (agent or "")[:500]
    result = {"browser": "", "browser_version": "", "os": "", "os_version": "", "device_type": "Other", "model": ""}
    if not agent:
        return result
    for name, pattern in _BROWSERS:
        match = pattern.search(agent)
        if match:
            result["browser"], result["browser_version"] = name, _major(match.group(1))
            break
    if re.search(r"iPhone|iPod", agent):
        result.update(os="iOS", device_type="Phone", model="iPhone")
        version = re.search(r"OS (\d+)[_.](\d+)", agent)
    elif "iPad" in agent:
        result.update(os="iPadOS", device_type="Tablet", model="iPad")
        version = re.search(r"OS (\d+)[_.](\d+)", agent)
    elif "Android" in agent:
        mobile = "Mobile" in agent
        result.update(os="Android", device_type="Phone" if mobile else "Tablet")
        version = re.search(r"Android (\d+(?:\.\d+)?)", agent)
        model = re.search(r"Android [\d.]+; ([^;)]+?)(?: Build|[;)])", agent)
        if model and model.group(1).strip() not in ("K", "Mobile"):
            result["model"] = model.group(1).strip()[:60]
    elif "Windows" in agent:
        result.update(os="Windows", device_type="Computer")
        nt = re.search(r"Windows NT (\d+\.\d+)", agent)
        # Windows 10 et 11 se présentent tous deux comme « NT 10.0 » : on ne peut pas les distinguer.
        version = None
        if nt:
            result["os_version"] = {"10.0": "10 ou 11", "6.3": "8.1", "6.2": "8", "6.1": "7"}.get(
                nt.group(1), nt.group(1)
            )
    elif "Macintosh" in agent or "Mac OS X" in agent:
        # macOS annonce toujours « 10_15_7 » : la version réelle n'est pas connue.
        result.update(os="macOS", device_type="Computer")
        version = None
    elif "CrOS" in agent:
        result.update(os="ChromeOS", device_type="Computer")
        version = None
    elif "Linux" in agent or "X11" in agent:
        result.update(os="Linux", device_type="Computer")
        version = None
    else:
        version = None
    if version and not result["os_version"]:
        result["os_version"] = ".".join(version.groups()) if version.groups() else ""
        if result["os"] in ("iOS", "iPadOS"):
            result["os_version"] = version.group(1)
    return result


def device_label(info: Dict[str, str]) -> str:
    """Phrase lisible : « Chrome 141 sur Windows 10 ou 11 · Ordinateur »."""
    if not (info.get("browser") or info.get("os")):
        return "Appareil non identifié"
    browser = " ".join(p for p in (info.get("browser"), info.get("browser_version")) if p)
    system = " ".join(p for p in (info.get("os"), info.get("os_version")) if p)
    model = info.get("model")
    head = f"{browser} sur {system}" if browser and system else (browser or system)
    extra = [TYPE_LABELS.get(info.get("device_type"), "")]
    if model and model not in head:
        extra.insert(0, model)
    return " · ".join([head] + [e for e in extra if e])


def fingerprint(sid: str) -> str:
    return hashlib.sha256((sid or "").encode()).hexdigest()


def on_login(login_manager=None, **_kwargs) -> None:
    """Crochet « on_session_creation » : garde l'appareil de la nouvelle session. Ne bloque jamais la connexion."""
    try:
        user = frappe.session.user
        if user in ("Guest", "Administrator"):
            return
        agent = ""
        if getattr(frappe.local, "request", None) is not None:
            agent = frappe.request.headers.get("User-Agent", "")
        record_device(user, frappe.session.sid, agent, getattr(frappe.local, "request_ip", "") or "")
    except Exception:  # noqa: BLE001 - un échec de suivi ne doit jamais empêcher la connexion
        frappe.log_error(title="Cortex device tracking failed")


def record_device(user: str, sid: str, agent: str, ip: str) -> None:
    info = parse_user_agent(agent)
    frappe.get_doc(
        {
            "doctype": DEVICE_DOCTYPE,
            "user": user,
            "session_key": fingerprint(sid),
            "device_label": device_label(info),
            "device_type": info["device_type"],
            "browser": info["browser"],
            "browser_version": info["browser_version"],
            "os": info["os"],
            "os_version": info["os_version"],
            "model": info["model"],
            "ip_address": (ip or "")[:100],
            "signed_in_at": now_datetime(),
            "user_agent": agent[:500],
        }
    ).insert(ignore_permissions=True)


def _sessions_of(user: str):
    return frappe.db.sql(
        "SELECT sid, ipaddress, lastupdate FROM `tabSessions` WHERE user=%s ORDER BY lastupdate DESC",
        (user,),
        as_dict=True,
    )


def list_for(user: str, current_sid: Optional[str] = None) -> Dict[str, Any]:
    """Sessions actives de la personne avec ce qu'on sait de chaque appareil."""
    known = {
        row.session_key: row
        for row in frappe.get_all(
            DEVICE_DOCTYPE,
            filters={"user": user},
            fields=[
                "name",
                "session_key",
                "device_label",
                "device_type",
                "browser",
                "browser_version",
                "os",
                "os_version",
                "model",
                "ip_address",
                "signed_in_at",
            ],
            limit_page_length=500,
        )
    }
    items = []
    for row in _sessions_of(user):
        key = fingerprint(row.sid)
        device = known.get(key)
        items.append(
            {
                "id": key[:16],
                "current": row.sid == current_sid,
                "label": device.device_label if device else "Appareil non identifié",
                "identified": bool(device),
                "browser": f"{device.browser} {device.browser_version}".strip() if device else "",
                "os": f"{device.os} {device.os_version}".strip() if device else "",
                "model": device.model if device else "",
                "type": TYPE_LABELS.get(device.device_type, "") if device else "",
                "ip": row.ipaddress or (device.ip_address if device else "") or "",
                "signed_in_at": str(device.signed_in_at)[:16] if device and device.signed_in_at else "",
                "last_active": str(row.lastupdate)[:16],
            }
        )
    return {
        "sessions": items,
        "tracking_note": "L'appareil est déclaré par le navigateur ; aucun lieu n'est déduit de l'adresse IP.",
    }


def revoke(
    user: str, device_id: str, current_sid: str, by: str, reason: str = "Déconnecté à distance"
) -> Dict[str, Any]:
    """Ferme une session précise de `user` (jamais la session courante : pour celle-là, on se déconnecte)."""
    from frappe.sessions import delete_session

    for row in _sessions_of(user):
        key = fingerprint(row.sid)
        if key.startswith(device_id or "\0"):
            if row.sid == current_sid:
                frappe.throw(
                    "C'est l'appareil que vous utilisez : déconnectez-vous depuis le menu du profil.",
                    frappe.ValidationError,
                )
            delete_session(row.sid, user=user, reason="Session Expired")
            name = frappe.db.get_value(DEVICE_DOCTYPE, {"session_key": key}, "name")
            if name:
                frappe.db.set_value(
                    DEVICE_DOCTYPE,
                    name,
                    {"revoked": 1, "revoked_at": now_datetime(), "revoked_by": by},
                    update_modified=False,
                )
            return {
                "closed": 1,
                "label": frappe.db.get_value(DEVICE_DOCTYPE, name, "device_label")
                if name
                else "Appareil non identifié",
            }
    frappe.throw("Cette session n'existe plus.", frappe.ValidationError)


def revoke_all(user: str, keep_sid: Optional[str], by: str) -> int:
    """Ferme toutes les sessions de `user`, sauf `keep_sid`. Renvoie le nombre de sessions fermées."""
    from frappe.sessions import delete_session

    closed = 0
    for row in _sessions_of(user):
        if keep_sid and row.sid == keep_sid:
            continue
        delete_session(row.sid, user=user, reason="Session Expired")
        name = frappe.db.get_value(DEVICE_DOCTYPE, {"session_key": fingerprint(row.sid)}, "name")
        if name:
            frappe.db.set_value(
                DEVICE_DOCTYPE,
                name,
                {"revoked": 1, "revoked_at": now_datetime(), "revoked_by": by},
                update_modified=False,
            )
        closed += 1
    return closed


def prune(days: int = 90) -> int:
    """Oublie les appareils dont la session est fermée depuis plus de `days` jours (tâche planifiée quotidienne)."""
    from frappe.utils import add_days

    cutoff = add_days(now_datetime(), -days)
    names = frappe.get_all(DEVICE_DOCTYPE, filters={"creation": ["<", cutoff]}, pluck="name", limit_page_length=1000)
    live = {fingerprint(sid) for (sid,) in frappe.db.sql("SELECT sid FROM `tabSessions`")}
    removed = 0
    for name in names:
        if frappe.db.get_value(DEVICE_DOCTYPE, name, "session_key") not in live:
            frappe.delete_doc(DEVICE_DOCTYPE, name, ignore_permissions=True, force=True)
            removed += 1
    return removed
