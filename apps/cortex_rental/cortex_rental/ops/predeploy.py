"""Contrôle avant mise en production : configuration du site, secrets, comptes de démonstration, migrations.

    bench --site <site> execute cortex_rental.ops.predeploy.run

Chaque contrôle donne OK, AVERTISSEMENT (à examiner) ou ÉCHEC (bloquant). Le code de retour de `run` est le nombre
d'échecs. Aucune écriture dans la base : le contrôle est sûr à lancer sur un site en service.
"""

from typing import Callable, Dict, List, Tuple

try:
    import frappe
except ImportError:
    frappe = None

OK, WARN, FAIL = "OK", "AVERTISSEMENT", "ÉCHEC"
Result = Tuple[str, str, str]  # niveau, contrôle, détail

DEMO_EMAIL_SUFFIXES = ("@cortex.test", "@example.com", "@example.org")
DEMO_COMPANY_MARKERS = ("(essai)", "(SIM)", "Simulation")
DEFAULT_PASSWORDS = ("admin", "Sim-Pass-2026!", "password", "12345678")


def evaluate_site_config(conf: Dict) -> List[Result]:
    """Pur : jugement sur site_config.json (testable sans bench)."""
    results: List[Result] = []

    def add(level, name, detail):
        results.append((level, name, detail))

    add(FAIL, "developer_mode", "Le mode développeur doit être désactivé.") if conf.get("developer_mode") else add(
        OK, "developer_mode", "désactivé"
    )
    add(FAIL, "allow_tests", "allow_tests doit être désactivé.") if conf.get("allow_tests") else add(
        OK, "allow_tests", "désactivé"
    )
    factor = conf.get("cortex_rate_limit_factor")
    if factor and float(factor) > 1:
        add(FAIL, "limites de débit", f"cortex_rate_limit_factor={factor} : réservé aux essais de charge, à retirer.")
    else:
        add(OK, "limites de débit", "valeurs normales")
    if str(conf.get("cortex_chat_provider", "gateway")).lower() == "mock":
        add(FAIL, "moteur IA", "cortex_chat_provider=mock : aucune vraie réponse de l'assistant.")
    else:
        add(OK, "moteur IA", str(conf.get("cortex_chat_provider", "gateway")))
    host = str(conf.get("host_name") or "")
    if host.startswith("https://"):
        add(OK, "adresse publique", host)
    else:
        add(WARN, "adresse publique", "host_name devrait être une adresse https:// (liens des courriels, paiements).")
    cors = conf.get("allow_cors")
    if cors == "*" or (isinstance(cors, list) and "*" in cors):
        add(FAIL, "CORS", "allow_cors ne doit pas être « * ».")
    else:
        add(OK, "CORS", "restreint")
    if conf.get("encryption_key"):
        add(OK, "clé de chiffrement", "présente (à sauvegarder séparément des sauvegardes de base de données)")
    else:
        add(
            FAIL,
            "clé de chiffrement",
            "encryption_key absente : les secrets chiffrés seraient illisibles après restauration.",
        )
    if conf.get("maintenance_mode"):
        add(WARN, "maintenance", "le site est en mode maintenance.")
    if not conf.get("max_file_size"):
        add(WARN, "taille des fichiers", "max_file_size non défini (25 Mo par défaut) : fixez-le (ex. 10485760).")
    return results


def _check(name: str, function: Callable[[], Result]) -> Result:
    try:
        return function()
    except Exception as error:  # un contrôle en panne est signalé, il ne bloque pas les autres
        return (WARN, name, f"contrôle impossible : {type(error).__name__}")


def _site_checks() -> List[Result]:
    from frappe.utils.password import check_password

    results: List[Result] = list(evaluate_site_config(dict(frappe.conf)))

    def migrations():
        from cortex_rental.services import health

        return (
            (OK, "migrations", "à jour")
            if health._migrations()
            else (FAIL, "migrations", "des correctifs restent à appliquer : bench migrate")
        )

    def scheduler():
        from frappe.utils.scheduler import is_scheduler_disabled

        from cortex_rental.services import health

        if is_scheduler_disabled():
            return (FAIL, "planificateur", "désactivé : rappels et expirations ne tourneront pas.")
        if not health._scheduler():
            return (
                WARN,
                "planificateur",
                "activé, mais aucune tâche exécutée récemment : `bench schedule` tourne-t-il ?",
            )
        return (OK, "planificateur", "actif et récemment exécuté")

    def admin_password():
        for candidate in DEFAULT_PASSWORDS:
            try:
                check_password("Administrator", candidate)
                return (
                    FAIL,
                    "mot de passe Administrator",
                    "un mot de passe par défaut est encore valide : changez-le.",
                )
            except Exception:
                continue
        return (OK, "mot de passe Administrator", "pas un mot de passe par défaut connu")

    def demo_users():
        users = frappe.get_all("User", filters={"enabled": 1}, pluck="name", limit_page_length=0)
        demo = [u for u in users if u.lower().endswith(DEMO_EMAIL_SUFFIXES)]
        if demo:
            return (
                FAIL,
                "comptes de démonstration",
                f"{len(demo)} compte(s) actif(s) (ex. {', '.join(demo[:3])}) : à désactiver.",
            )
        return (OK, "comptes de démonstration", "aucun compte actif")

    def demo_companies():
        names = frappe.get_all("Company", pluck="name", limit_page_length=0)
        demo = [n for n in names if any(marker in n for marker in DEMO_COMPANY_MARKERS)]
        return (
            (WARN, "sociétés de démonstration", f"{len(demo)} société(s) d'essai : {', '.join(demo[:3])}")
            if demo
            else (OK, "sociétés de démonstration", "aucune")
        )

    def password_policy():
        settings = frappe.get_cached_doc("System Settings")
        if not settings.enable_password_policy:
            return (WARN, "politique de mot de passe", "désactivée dans les paramètres système.")
        return (OK, "politique de mot de passe", f"activée (score minimal {settings.minimum_password_score})")

    def lockout():
        settings = frappe.get_cached_doc("System Settings")
        if not int(settings.allow_consecutive_login_attempts or 0):
            return (WARN, "tentatives de connexion", "aucune limite d'échecs consécutifs : définissez-la (ex. 5).")
        return (OK, "tentatives de connexion", f"verrouillage après {settings.allow_consecutive_login_attempts} échecs")

    def two_factor():
        enabled = frappe.get_cached_doc("System Settings").enable_two_factor_auth
        return (
            (OK, "authentification à deux facteurs", "activée")
            if enabled
            else (WARN, "authentification à deux facteurs", "désactivée : recommandée au moins pour les propriétaires.")
        )

    def outgoing_email():
        has = frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}) or frappe.conf.get(
            "mail_server"
        )
        return (
            (OK, "courriel sortant", "configuré")
            if has
            else (
                WARN,
                "courriel sortant",
                "aucun compte de courriel sortant par défaut (invitations, vérifications, rappels).",
            )
        )

    def ai_key():
        from frappe.utils.password import get_decrypted_password

        key = None
        try:
            key = get_decrypted_password("Cortex AI Settings", "Cortex AI Settings", "api_key", raise_exception=False)
        except Exception:
            key = None
        return (
            (OK, "clé de l'IA", "définie")
            if key
            else (WARN, "clé de l'IA", "aucune clé : l'assistant ne répondra pas.")
        )

    def assets():
        import os

        built_dir = os.path.join(frappe.utils.get_bench_path(), "sites", "assets")
        built = os.path.isdir(os.path.join(built_dir, "cortex_rental")) and os.path.isdir(
            os.path.join(built_dir, "frappe", "dist")
        )
        if built:
            return (OK, "ressources construites", "présentes")
        return (FAIL, "ressources construites", "dossier assets absent : bench build --app cortex_rental")

    for function in (
        migrations,
        scheduler,
        admin_password,
        demo_users,
        demo_companies,
        password_policy,
        lockout,
        two_factor,
        outgoing_email,
        ai_key,
        assets,
    ):
        results.append(_check(function.__name__, function))
    return results


def run() -> int:
    results = _site_checks()
    width = max(len(name) for _l, name, _d in results)
    marks = {OK: "✔", WARN: "!", FAIL: "✘"}
    for level, name, detail in results:
        print(f" {marks[level]} {level:<13} {name:<{width}}  {detail}")
    failures = sum(1 for level, _n, _d in results if level == FAIL)
    warnings = sum(1 for level, _n, _d in results if level == WARN)
    print(
        f"\n{failures} échec(s), {warnings} avertissement(s), {len(results) - failures - warnings} contrôle(s) réussi(s)."
    )
    return failures
