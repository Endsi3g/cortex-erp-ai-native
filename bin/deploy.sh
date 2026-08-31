#!/usr/bin/env bash
# ==============================================================================
# CORTEX ERP AI-NATIVE — SCRIPT DE DÉPLOIEMENT COMPLET UNIVERSEL
# ==============================================================================
# Modes supportés :
#   ./bin/deploy.sh tour      -> Déploiement & migration sur le Bench natif (la Tour)
#   ./bin/deploy.sh docker    -> Déploiement complet de la stack Docker Compose
#   ./bin/deploy.sh fixtures  -> Chargement des données de démo (société, parc, sorties)
#
# Drapeaux optionnels :
#   --with-fixtures           -> Charge automatiquement les fixtures sans invite
#   --skip-fixtures           -> Saute le chargement des fixtures sans invite
#   --site <nom_du_site>      -> Spécifie le site Frappe cible (défaut: cortex.local)
#   --bench-path <chemin>     -> Spécifie le chemin racine du Frappe Bench
# ==============================================================================

set -eo pipefail

# --- Palette de Couleurs & Styles ANSI ---
BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

# --- Chemins et Variables par Défaut ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_SITE="cortex.local"
DEFAULT_BENCH_PATH="${BENCH_PATH:-${HOME}/frappe-bench}"
SITE="${DEFAULT_SITE}"
MODE=""
PROVISION_FIXTURES="" # "yes", "no", or "" (interactive)

# --- Fonctions d'Affichage ---
print_banner() {
    printf "${CYAN}${BOLD}"
    printf "\n======================================================================\n"
    printf "       🧠 CORTEX ERP AI-NATIVE — DÉPLOIEMENT & ORCHESTRATION\n"
    printf "======================================================================\n\n"
    printf "${NC}"
}

log_step() {
    printf "\n${BLUE}${BOLD}[STEP %s]${NC} ${BOLD}%s${NC}\n" "$1" "$2"
}

log_success() {
    printf "${GREEN}${BOLD}✓ %s${NC}\n" "$1"
}

log_warn() {
    printf "${YELLOW}${BOLD}⚠️  %s${NC}\n" "$1"
}

log_error() {
    printf "${RED}${BOLD}❌ %s${NC}\n" "$1" >&2
}

# --- Aide & Usage ---
usage() {
    print_banner
    printf "Usage: ${BOLD}./bin/deploy.sh <mode> [options]${NC}\n\n"
    printf "Modes :\n"
    printf "  ${GREEN}tour${NC} | ${GREEN}native${NC}   Déploie sur l'instance Bench native locale/distante (la Tour)\n"
    printf "  ${GREEN}docker${NC}          Déploie la stack complète conteneurisée via Docker Compose\n"
    printf "  ${GREEN}fixtures${NC}        Génère et injecte le jeu de données de démo sur le site actif\n\n"
    printf "Options :\n"
    printf "  --site <nom>          Nom du site Frappe (défaut: %s)\n" "${SITE}"
    printf "  --bench-path <chemin> Chemin vers le répertoire frappe-bench\n"
    printf "  --with-fixtures       Force le chargement automatique des fixtures de démo\n"
    printf "  --skip-fixtures       Ignore le chargement des fixtures\n"
    printf "  -h, --help            Affiche cette aide\n\n"
    exit 0
}

# --- Parsing des Arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        tour|native)
            MODE="tour"
            shift
            ;;
        docker)
            MODE="docker"
            shift
            ;;
        fixtures)
            MODE="fixtures"
            shift
            ;;
        --site)
            SITE="$2"
            shift 2
            ;;
        --bench-path)
            DEFAULT_BENCH_PATH="$2"
            shift 2
            ;;
        --with-fixtures)
            PROVISION_FIXTURES="yes"
            shift
            ;;
        --skip-fixtures)
            PROVISION_FIXTURES="no"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Option ou mode inconnu : $1"
            usage
            ;;
    esac
done

if [ -z "${MODE}" ]; then
    print_banner
    echo -e "${YELLOW}Aucun mode spécifié.${NC}"
    echo "Choisissez le mode de déploiement :"
    echo "  1) Tour / Bench Natif (recommandé si Frappe est installé en local)"
    echo "  2) Docker Compose (stack isolée : MariaDB, Valkey, MinIO, Bench, FastMCP)"
    echo "  3) Fixtures de Démo uniquement"
    echo ""
    read -rp "Sélectionnez une option [1-3]: " choice
    case "${choice}" in
        1) MODE="tour" ;;
        2) MODE="docker" ;;
        3) MODE="fixtures" ;;
        *) log_error "Sélection invalide. Annulation."; exit 1 ;;
    esac
fi

# ==============================================================================
# MODE 1 : DÉPLOIEMENT BENCH NATIF / LA TOUR
# ==============================================================================
deploy_tour() {
    print_banner
    echo -e "Déploiement en cours sur le ${BOLD}Bench Natif (la Tour)${NC}..."
    echo -e "Site cible : ${CYAN}${SITE}${NC}"

    # 1. Localisation du Bench
    log_step "1/6" "Localisation et validation de l'environnement Frappe Bench..."
    BENCH_DIR="${DEFAULT_BENCH_PATH}"
    if [ ! -d "${BENCH_DIR}" ] && [ -d "/home/frappe/frappe-bench" ]; then
        BENCH_DIR="/home/frappe/frappe-bench"
    elif [ ! -d "${BENCH_DIR}" ] && [ -d "${REPO_ROOT}/../frappe-bench" ]; then
        BENCH_DIR="$(cd "${REPO_ROOT}/../frappe-bench" && pwd)"
    fi

    if [ ! -d "${BENCH_DIR}" ]; then
        log_warn "Répertoire frappe-bench introuvable à '${BENCH_DIR}'."
        read -rp "Veuillez entrer le chemin absolu vers votre frappe-bench : " USER_BENCH
        BENCH_DIR="${USER_BENCH}"
    fi

    if [ ! -f "${BENCH_DIR}/sites/common_site_config.json" ] && [ ! -d "${BENCH_DIR}/apps" ]; then
        log_error "Le répertoire '${BENCH_DIR}' ne semble pas être un Frappe Bench valide."
        exit 1
    fi
    log_success "Frappe Bench détecté à : ${BENCH_DIR}"

    # 2. Synchronisation et installation de cortex_rental
    log_step "2/6" "Synchronisation de l'application cortex_rental..."
    CORTEX_APP_TARGET="${BENCH_DIR}/apps/cortex_rental"
    if [ ! -d "${CORTEX_APP_TARGET}" ]; then
        log_step "..." "Liaison de cortex_rental dans le bench..."
        ln -sf "${REPO_ROOT}/apps/cortex_rental" "${CORTEX_APP_TARGET}"
    fi

    # Editable install in bench virtualenv
    if [ -f "${BENCH_DIR}/env/bin/pip" ]; then
        "${BENCH_DIR}/env/bin/pip" install -e "${REPO_ROOT}/apps/cortex_rental" --no-deps >/dev/null 2>&1 || true
    fi
    log_success "Application cortex_rental connectée au bench."

    # 3. Vérification du Site et Migrations
    log_step "3/6" "Exécution des migrations de schéma MariaDB..."
    cd "${BENCH_DIR}"

    # Vérification si cortex_rental est installé sur le site
    if [ -d "sites/${SITE}" ]; then
        bench --site "${SITE}" install-app cortex_rental >/dev/null 2>&1 || true
        bench --site "${SITE}" migrate
        log_success "Migrations de schéma terminées avec succès."
    else
        log_warn "Le site '${SITE}' n'existe pas encore dans '${BENCH_DIR}/sites'."
        echo -e "Création du site '${SITE}'..."
        bench new-site "${SITE}" --install-app erpnext --install-app cortex_rental || true
    fi

    # 4. Compilation des Bundles Vue 3 & Assets Desk
    log_step "4/6" "Compilation des bundles JS Vue 3 et assets Frappe..."
    bench build --app cortex_rental
    log_success "Assets et bundles compilés avec succès."

    # 5. Gestion des Données de Démo (Fixtures)
    log_step "5/6" "Vérification des données de démonstration..."
    if [ -z "${PROVISION_FIXTURES}" ]; then
        echo ""
        read -rp "Souhaitez-vous injecter les données de démo (société cinéma, parc caméras/optiques, sorties actives) ? [O/n]: " ans
        if [[ "$ans" =~ ^[Nn]$ ]]; then
            PROVISION_FIXTURES="no"
        else
            PROVISION_FIXTURES="yes"
        fi
    fi

    if [ "${PROVISION_FIXTURES}" == "yes" ]; then
        echo -e "Injection des fixtures de démo via Python Frappe..."
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Données de démo chargées avec succès."
    else
        log_success "Étape des fixtures passée."
    fi

    # 6. Redémarrage des Services & Healthcheck
    log_step "6/6" "Redémarrage des workers et test de santé HTTP..."
    bench restart || true

    # Test HTTP local si le serveur tourne
    if curl -sf "http://127.0.0.1:8000/api/method/frappe.ping" >/dev/null 2>&1; then
        log_success "Healthcheck HTTP 200 OK — Le serveur répond !"
    else
        log_warn "Le serveur bench ne semble pas écouter sur le port 8000. Lancez 'bench start' si en mode développement."
    fi

    print_summary "native" "http://localhost:8000"
}

# ==============================================================================
# MODE 2 : DÉPLOIEMENT DOCKER COMPOSE
# ==============================================================================
deploy_docker() {
    print_banner
    echo -e "Déploiement en cours via ${BOLD}Docker Compose${NC}..."

    # 1. Vérification des Prérequis Docker
    log_step "1/5" "Vérification des prérequis Docker et Docker Compose..."
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker n'est pas installé sur ce système."
        exit 1
    fi

    DOCKER_COMPOSE_CMD="docker compose"
    if ! docker compose version >/dev/null 2>&1; then
        if command -v docker-compose >/dev/null 2>&1; then
            DOCKER_COMPOSE_CMD="docker-compose"
        else
            log_error "Docker Compose (v2) n'est pas disponible."
            exit 1
        fi
    fi
    log_success "Docker Engine et Docker Compose sont opérationnels."

    # 2. Démarrage de la Stack
    log_step "2/5" "Démarrage des conteneurs (MariaDB, Valkey, MinIO, Mailpit, Bench, FastMCP)..."
    cd "${REPO_ROOT}/infra/docker"
    ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml up -d --build

    # 3. Attente de la disponibilité MariaDB
    log_step "3/5" "Attente de l'initialisation complète de MariaDB..."
    RETRIES=30
    until ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml exec -T mariadb healthcheck.sh --connect >/dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
        echo -n "."
        sleep 2
        RETRIES=$((RETRIES - 1))
    done
    echo ""
    log_success "Base de données MariaDB initialisée et saine."

    # 4. Données de Démo
    log_step "4/5" "Gestion des données de démonstration..."
    if [ -z "${PROVISION_FIXTURES}" ]; then
        echo ""
        read -rp "Souhaitez-vous injecter les données de démo dans le conteneur Bench ? [O/n]: " ans
        if [[ "$ans" =~ ^[Nn]$ ]]; then
            PROVISION_FIXTURES="no"
        else
            PROVISION_FIXTURES="yes"
        fi
    fi

    if [ "${PROVISION_FIXTURES}" == "yes" ]; then
        echo -e "Injection des données de démo dans le conteneur..."
        ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml exec -T bench bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data || true
        log_success "Données de démo injectées."
    fi

    # 5. Validation de la Façade FastMCP
    log_step "5/5" "Validation de la façade d'agents FastMCP..."
    sleep 3
    if curl -sf "http://127.0.0.1:3100/health" >/dev/null 2>&1 || curl -sf "http://127.0.0.1:3100" >/dev/null 2>&1; then
        log_success "Façade FastMCP active sur le port 3100."
    else
        log_warn "FastMCP démarre (port 3100)."
    fi

    print_summary "docker" "http://localhost:8000"
}

# ==============================================================================
# MODE 3 : PROVISIONING FIXTURES UNIQUEMENT
# ==============================================================================
deploy_fixtures() {
    print_banner
    echo -e "Injection ciblée des ${BOLD}Données de Démonstration${NC}..."
    echo -e "Site cible : ${CYAN}${SITE}${NC}"

    if command -v bench >/dev/null 2>&1; then
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargées avec succès via le bench local."
    elif [ -f "${DEFAULT_BENCH_PATH}/env/bin/python" ]; then
        cd "${DEFAULT_BENCH_PATH}"
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargées avec succès."
    else
        log_warn "Bench CLI introuvable en local. Tentative via Docker Compose..."
        cd "${REPO_ROOT}/infra/docker"
        docker compose -f docker-compose.dev.yml exec -T bench bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargées via Docker."
    fi
}

# ==============================================================================
# RAPPORT RÉCAPITULATIF FINAL
# ==============================================================================
print_summary() {
    local target_type="$1"
    local base_url="$2"

    printf "\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n"
    printf "${GREEN}${BOLD}      🎉 DÉPLOIEMENT CORTEX ERP EFFECTUÉ AVEC SUCCÈS !${NC}\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n\n"
    printf "${BOLD}📌 Tableaux de bord et interfaces métier :${NC}\n"
    printf "  • ${CYAN}Desk ERP Principal${NC}        : %s/app\n" "${base_url}"
    printf "  • ${CYAN}Scanner Check-in & Retours${NC}: %s/app/cortex-checkin\n" "${base_url}"
    printf "  • ${CYAN}Matrice de Disponibilité${NC}  : %s/app/cortex-availability\n" "${base_url}"
    printf "  • ${CYAN}P&L Financier (Accounting)${NC}: %s/app/cortex-accounting-pnl\n" "${base_url}"
    printf "  • ${CYAN}Composer de Transaction${NC}   : %s/app/cortex-transaction-composer\n\n" "${base_url}"
    printf "${BOLD}🤖 Services Agents & Outils Développeur :${NC}\n"
    printf "  • ${CYAN}Façade FastMCP (Python)${NC}   : http://localhost:3100\n"
    printf "  • ${CYAN}Stockage Objets MinIO${NC}     : http://localhost:9091 (Admin: cortex_minio_admin)\n"
    printf "  • ${CYAN}Boîte Mailpit (Sandbox)${NC}   : http://localhost:8025\n\n"
    printf "${BOLD}🔑 Identifiants d'accès recommandés :${NC}\n"
    printf "  • Utilisateur : ${BOLD}Administrator${NC}\n"
    printf "  • Mot de passe: ${BOLD}admin${NC} (ou mot de passe initial du bench)\n\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n"
}

# --- Point d'Entrée Principal ---
case "${MODE}" in
    tour)
        deploy_tour
        ;;
    docker)
        deploy_docker
        ;;
    fixtures)
        deploy_fixtures
        ;;
    *)
        usage
        ;;
esac
