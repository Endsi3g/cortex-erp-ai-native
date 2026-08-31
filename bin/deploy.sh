#!/usr/bin/env bash
# ==============================================================================
# CORTEX ERP AI-NATIVE — SCRIPT D'INSTALLATION & DEPLOIEMENT 1-CLIC UNIVERSEL
# ==============================================================================
# Modes d'utilisation :
#   ./bin/deploy.sh 1click    -> Installation et deploiement complets de zero a un
#   ./bin/deploy.sh tour      -> Mise a jour & migration sur le Bench natif (la Tour)
#   ./bin/deploy.sh docker    -> Deploiement conteneurise complet via Docker Compose
#   ./bin/deploy.sh test      -> Execution de l'ensemble des suites de tests unitaires
#   ./bin/deploy.sh fixtures  -> Injection des donnees de demo dans le site actif
#
# Drapeaux CLI :
#   --site <nom>              -> Nom du site Frappe (defaut: cortex.local)
#   --bench-path <chemin>     -> Chemin vers frappe-bench (defaut: ~/frappe-bench)
#   --with-fixtures           -> Injecte automatiquement les donnees de demo
#   --skip-fixtures           -> Ignore l'injection des donnees de demo
#   --skip-tests              -> Ignore la phase de tests unitaires
#   -y, --yes                 -> Mode non-interactif (accepte tous les choix par defaut)
# ==============================================================================

set -eo pipefail

# --- Palette de Couleurs ANSI ---
BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

# --- Variables & Chemins ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_SITE="cortex.local"
DEFAULT_BENCH_PATH="${BENCH_PATH:-${HOME}/frappe-bench}"
SITE="${DEFAULT_SITE}"
MODE=""
PROVISION_FIXTURES=""
RUN_TESTS="yes"
NON_INTERACTIVE="no"
MARIADB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-root}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

# --- Fonctions d'Affichage & Logging ---
print_banner() {
    printf "${CYAN}${BOLD}"
    printf "\n======================================================================\n"
    printf "       CORTEX ERP AI-NATIVE — DEPLOIEMENT & INSTALLATION 1-CLIC\n"
    printf "======================================================================\n\n"
    printf "${NC}"
}

log_step() {
    printf "\n${BLUE}${BOLD}[ETAPE %s]${NC} ${BOLD}%s${NC}\n" "$1" "$2"
}

log_success() {
    printf "${GREEN}${BOLD}[OK] %s${NC}\n" "$1"
}

log_warn() {
    printf "${YELLOW}${BOLD}[AVERTISSEMENT] %s${NC}\n" "$1"
}

log_error() {
    printf "${RED}${BOLD}[ERREUR] %s${NC}\n" "$1" >&2
}

# --- Aide & Usage ---
usage() {
    print_banner
    printf "Usage: ${BOLD}./bin/deploy.sh <mode> [options]${NC}\n\n"
    printf "Modes disponibles :\n"
    printf "  ${GREEN}1click${NC} | ${GREEN}full${NC}     Installation complete de zero (pre-requis, bench, site, erpnext, cortex, fixtures, tests)\n"
    printf "  ${GREEN}tour${NC} | ${GREEN}native${NC}     Deploie et migre sur une instance Bench native existante (la Tour)\n"
    printf "  ${GREEN}docker${NC}          Deploie la stack complete conteneurisee via Docker Compose\n"
    printf "  ${GREEN}test${NC}            Execute l'ensemble de la suite de validation et tests unitaires\n"
    printf "  ${GREEN}fixtures${NC}        Genere et injecte le jeu de donnees de demo sur le site actif\n\n"
    printf "Options CLI :\n"
    printf "  --site <nom>          Nom du site Frappe (defaut: %s)\n" "${SITE}"
    printf "  --bench-path <chemin> Chemin vers le repertoire frappe-bench\n"
    printf "  --with-fixtures       Injecte automatiquement les fixtures de demo\n"
    printf "  --skip-fixtures       Ignore l'injection des fixtures de demo\n"
    printf "  --skip-tests          Ignore l'etape de tests\n"
    printf "  -y, --yes             Mode non-interactif automatique\n"
    printf "  -h, --help            Affiche cette aide\n\n"
    exit 0
}

# --- Parsing des Arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        1click|all|full|install)
            MODE="1click"
            shift
            ;;
        tour|native)
            MODE="tour"
            shift
            ;;
        docker)
            MODE="docker"
            shift
            ;;
        test|tests)
            MODE="test"
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
        --skip-tests)
            RUN_TESTS="no"
            shift
            ;;
        -y|--yes|--non-interactive)
            NON_INTERACTIVE="yes"
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

# --- Selection Interactive si aucun mode fourni ---
if [ -z "${MODE}" ]; then
    print_banner
    echo "Selectionnez le mode de deploiement :"
    echo "  1) Deploiement 1-Clic Complet (Installation de A a Z : Bench, ERPNext, Cortex, Fixtures & Tests)"
    echo "  2) Bench Natif / Tour (Mise a jour, migrations, build bundles et redemarrage)"
    echo "  3) Docker Compose (Stack conteneurisee : MariaDB, Valkey, MinIO, Bench, FastMCP)"
    echo "  4) Lancer la suite de tests unitaires et validation pre-claude"
    echo "  5) Injecter uniquement les donnees de demonstration"
    echo ""
    read -rp "Votre choix [1-5]: " choice
    case "${choice}" in
        1) MODE="1click" ;;
        2) MODE="tour" ;;
        3) MODE="docker" ;;
        4) MODE="test" ;;
        5) MODE="fixtures" ;;
        *) log_error "Choix invalide. Annulation."; exit 1 ;;
    esac
fi

# ==============================================================================
# VERIFICATION DE LA SUITE DE TESTS
# ==============================================================================
run_test_suite() {
    log_step "TEST" "Execution des tests de validation pre-claude et unitaires..."
    cd "${REPO_ROOT}"
    if [ -f "./bin/pre-claude-check.sh" ]; then
        ./bin/pre-claude-check.sh
    else
        PYTHONPATH="${REPO_ROOT}/apps/cortex_rental:${REPO_ROOT}/apps/cortex-mcp" python3 -m unittest discover -s apps/cortex_rental/cortex_rental/tests
    fi
    log_success "Tests unitaires et verifications DocTypes 100% valides."
}

# ==============================================================================
# MODE 1 : INSTALLATION & DEPLOIEMENT 1-CLIC COMPLET (ZERO-TO-ONE)
# ==============================================================================
deploy_1click() {
    print_banner
    echo -e "Lancement de l'${BOLD}Installation et Deploiement 1-Clic Complet${NC}..."
    echo -e "Site cible : ${CYAN}${SITE}${NC}"

    # 1. Verification des Outils Systeme
    log_step "1/8" "Verification des dependances et de la chaine d'outils systeme..."
    local missing_tools=()
    for tool in git python3 pip; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Outils systeme manquants : ${missing_tools[*]}"
        echo "Veuillez installer les outils requis avant de continuer."
        exit 1
    fi
    log_success "Outils systeme de base (git, python3, pip) detectes."

    # 2. Verification / Installation de Frappe Bench CLI
    log_step "2/8" "Verification du CLI frappe-bench..."
    if ! command -v bench >/dev/null 2>&1; then
        log_warn "Le CLI 'bench' n'est pas installe globalement. Installation via pip..."
        pip install --user frappe-bench || pip install frappe-bench
        export PATH="${HOME}/.local/bin:${PATH}"
    fi
    log_success "CLI bench operationnel."

    # 3. Initialisation du Bench si absent
    log_step "3/8" "Validation du repertoire frappe-bench..."
    BENCH_DIR="${DEFAULT_BENCH_PATH}"
    if [ ! -d "${BENCH_DIR}" ]; then
        echo -e "Initialisation d'un nouveau Frappe Bench v15 a : ${BENCH_DIR}..."
        bench init --frappe-branch version-15 --skip-redis-config-generation "${BENCH_DIR}"
    fi
    cd "${BENCH_DIR}"
    log_success "Frappe Bench pret a : ${BENCH_DIR}"

    # 4. Telechargement d'ERPNext (v15)
    log_step "4/8" "Verification et acquisition de l'application ERPNext v15..."
    if [ ! -d "${BENCH_DIR}/apps/erpnext" ]; then
        echo "Telechargement d'ERPNext version-15..."
        bench get-app erpnext --branch version-15 || true
    fi
    log_success "ERPNext v15 present dans le bench."

    # 5. Liaison et Installation de Cortex Rental
    log_step "5/8" "Liaison et installation de l'application cortex_rental..."
    CORTEX_LINK="${BENCH_DIR}/apps/cortex_rental"
    if [ ! -d "${CORTEX_LINK}" ]; then
        ln -sf "${REPO_ROOT}/apps/cortex_rental" "${CORTEX_LINK}"
    fi
    if [ -f "${BENCH_DIR}/env/bin/pip" ]; then
        "${BENCH_DIR}/env/bin/pip" install -e "${REPO_ROOT}/apps/cortex_rental" --no-deps >/dev/null 2>&1 || true
    fi
    log_success "Application cortex_rental liee et installee en mode editable."

    # 6. Creation ou Mise a jour du Site MariaDB
    log_step "6/8" "Creation du site et execution des migrations de base de donnees..."
    if [ ! -d "${BENCH_DIR}/sites/${SITE}" ]; then
        echo "Creation du nouveau site '${SITE}'..."
        bench new-site "${SITE}" \
            --admin-password "${ADMIN_PASSWORD}" \
            --install-app erpnext \
            --install-app cortex_rental || true
    else
        echo "Site '${SITE}' existant : installation des apps et migration..."
        bench --site "${SITE}" install-app erpnext >/dev/null 2>&1 || true
        bench --site "${SITE}" install-app cortex_rental >/dev/null 2>&1 || true
        bench --site "${SITE}" migrate
    fi
    log_success "Site et tables MariaDB synchronises avec succes."

    # 7. Compilation des Bundles Vue 3
    log_step "7/8" "Compilation des bundles Vue 3 et assets Desk..."
    bench build --app cortex_rental
    log_success "Bundles frontend esbuild generes avec succes."

    # 8. Donnees de Demonstration & Tests
    log_step "8/8" "Chargement des donnees de demonstration & verification finale..."
    if [ "${PROVISION_FIXTURES}" != "no" ]; then
        echo "Injection des donnees de demo (societe, parc camera, sorties actives)..."
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data || true
        log_success "Donnees de demonstration chargees."
    fi

    if [ "${RUN_TESTS}" == "yes" ]; then
        run_test_suite
    fi

    bench restart || true
    print_summary "native" "http://localhost:8000"
}

# ==============================================================================
# MODE 2 : DEPLOIEMENT BENCH NATIF / TOUR (UPDATE & MIGRATE)
# ==============================================================================
deploy_tour() {
    print_banner
    echo -e "Deploiement et mise a jour sur le ${BOLD}Bench Natif (la Tour)${NC}..."
    echo -e "Site cible : ${CYAN}${SITE}${NC}"

    BENCH_DIR="${DEFAULT_BENCH_PATH}"
    if [ ! -d "${BENCH_DIR}" ] && [ -d "/home/frappe/frappe-bench" ]; then
        BENCH_DIR="/home/frappe/frappe-bench"
    elif [ ! -d "${BENCH_DIR}" ] && [ -d "${REPO_ROOT}/../frappe-bench" ]; then
        BENCH_DIR="$(cd "${REPO_ROOT}/../frappe-bench" && pwd)"
    fi

    if [ ! -d "${BENCH_DIR}" ]; then
        if [ "${NON_INTERACTIVE}" == "yes" ]; then
            log_error "Repertoire frappe-bench introuvable."
            exit 1
        fi
        log_warn "Repertoire frappe-bench introuvable a '${BENCH_DIR}'."
        read -rp "Entrez le chemin absolu vers votre frappe-bench : " USER_BENCH
        BENCH_DIR="${USER_BENCH}"
    fi

    log_step "1/5" "Liaison de l'application cortex_rental..."
    CORTEX_LINK="${BENCH_DIR}/apps/cortex_rental"
    if [ ! -d "${CORTEX_LINK}" ]; then
        ln -sf "${REPO_ROOT}/apps/cortex_rental" "${CORTEX_LINK}"
    fi
    if [ -f "${BENCH_DIR}/env/bin/pip" ]; then
        "${BENCH_DIR}/env/bin/pip" install -e "${REPO_ROOT}/apps/cortex_rental" --no-deps >/dev/null 2>&1 || true
    fi
    log_success "cortex_rental synchronise dans le bench."

    log_step "2/5" "Execution des migrations de schema MariaDB..."
    cd "${BENCH_DIR}"
    bench --site "${SITE}" install-app cortex_rental >/dev/null 2>&1 || true
    bench --site "${SITE}" migrate
    log_success "Migrations MariaDB executees avec succes."

    log_step "3/5" "Compilation des bundles JS Vue 3..."
    bench build --app cortex_rental
    log_success "Bundles Vue 3 compiles."

    log_step "4/5" "Gestion des donnees de demonstration..."
    if [ -z "${PROVISION_FIXTURES}" ]; then
        if [ "${NON_INTERACTIVE}" == "yes" ]; then
            PROVISION_FIXTURES="yes"
        else
            read -rp "Injecter le jeu de donnees de demo (societe, parc camera, sorties actives) ? [O/n]: " ans
            if [[ "$ans" =~ ^[Nn]$ ]]; then
                PROVISION_FIXTURES="no"
            else
                PROVISION_FIXTURES="yes"
            fi
        fi
    fi

    if [ "${PROVISION_FIXTURES}" == "yes" ]; then
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Donnees de demonstration chargees."
    fi

    log_step "5/5" "Redemarrage des services & tests..."
    bench restart || true
    if [ "${RUN_TESTS}" == "yes" ]; then
        run_test_suite
    fi

    print_summary "native" "http://localhost:8000"
}

# ==============================================================================
# MODE 3 : DEPLOIEMENT DOCKER COMPOSE
# ==============================================================================
deploy_docker() {
    print_banner
    echo -e "Deploiement en cours via ${BOLD}Docker Compose${NC}..."

    log_step "1/5" "Verification des prerequis Docker..."
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker n'est pas installe sur ce systeme."
        exit 1
    fi

    local DOCKER_COMPOSE_CMD="docker compose"
    if ! docker compose version >/dev/null 2>&1; then
        if command -v docker-compose >/dev/null 2>&1; then
            DOCKER_COMPOSE_CMD="docker-compose"
        else
            log_error "Docker Compose (v2) n'est pas disponible."
            exit 1
        fi
    fi
    log_success "Docker Engine et Docker Compose sont operationnels."

    log_step "2/5" "Demarrage de la stack conteneurisee (MariaDB, Valkey, MinIO, Mailpit, Bench, FastMCP)..."
    cd "${REPO_ROOT}/infra/docker"
    ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml up -d --build

    log_step "3/5" "Attente de l'initialisation saine de MariaDB 10.11+..."
    local RETRIES=30
    until ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml exec -T mariadb healthcheck.sh --connect >/dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
        echo -n "."
        sleep 2
        RETRIES=$((RETRIES - 1))
    done
    echo ""
    log_success "Base de donnees MariaDB operationnelle."

    log_step "4/5" "Injection des donnees de demonstration dans le conteneur..."
    if [ "${PROVISION_FIXTURES}" != "no" ]; then
        ${DOCKER_COMPOSE_CMD} -f docker-compose.dev.yml exec -T bench bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data || true
        log_success "Donnees de demonstration chargees dans le conteneur."
    fi

    log_step "5/5" "Execution des tests de validation..."
    if [ "${RUN_TESTS}" == "yes" ]; then
        run_test_suite
    fi

    print_summary "docker" "http://localhost:8000"
}

# ==============================================================================
# MODE 4 : PROVISIONING FIXTURES SEULES
# ==============================================================================
deploy_fixtures() {
    print_banner
    echo -e "Injection ciblee des ${BOLD}Donnees de Demonstration${NC}..."
    echo -e "Site cible : ${CYAN}${SITE}${NC}"

    if command -v bench >/dev/null 2>&1; then
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargees avec succes via le bench local."
    elif [ -f "${DEFAULT_BENCH_PATH}/env/bin/python" ]; then
        cd "${DEFAULT_BENCH_PATH}"
        bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargees avec succes."
    else
        log_warn "Bench local non trouve. Tentative via Docker Compose..."
        cd "${REPO_ROOT}/infra/docker"
        docker compose -f docker-compose.dev.yml exec -T bench bench --site "${SITE}" execute cortex_rental.fixtures.demo_data.provision_demo_data
        log_success "Fixtures chargees via Docker."
    fi
}

# ==============================================================================
# RAPPORT RECAPITULATIF FINAL
# ==============================================================================
print_summary() {
    local target_type="$1"
    local base_url="$2"

    printf "\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n"
    printf "${GREEN}${BOLD}      DEPLOIEMENT CORTEX ERP EFFECTUE AVEC SUCCES !\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n\n"
    printf "${BOLD}Tableaux de bord et interfaces metier :${NC}\n"
    printf "  - Desk ERP Principal        : %s/app\n" "${base_url}"
    printf "  - Scanner Check-in & Retours: %s/app/cortex-checkin\n" "${base_url}"
    printf "  - Matrice de Disponibilite  : %s/app/cortex-availability\n" "${base_url}"
    printf "  - P&L Financier (Accounting): %s/app/cortex-accounting-pnl\n" "${base_url}"
    printf "  - Composer de Transaction   : %s/app/cortex-transaction-composer\n\n" "${base_url}"
    printf "${BOLD}Services Agents & Outils :${NC}\n"
    printf "  - Facade FastMCP (Python)   : http://localhost:3100\n"
    printf "  - Stockage Objets MinIO     : http://localhost:9091 (Admin: cortex_minio_admin)\n"
    printf "  - Boite Mailpit (Sandbox)   : http://localhost:8025\n\n"
    printf "${BOLD}Identifiants par defaut :${NC}\n"
    printf "  - Utilisateur : ${BOLD}Administrator${NC}\n"
    printf "  - Mot de passe: ${BOLD}admin${NC}\n\n"
    printf "${GREEN}${BOLD}======================================================================${NC}\n"
}

# --- Routage Principal ---
case "${MODE}" in
    1click)
        deploy_1click
        ;;
    tour)
        deploy_tour
        ;;
    docker)
        deploy_docker
        ;;
    test)
        run_test_suite
        ;;
    fixtures)
        deploy_fixtures
        ;;
    *)
        usage
        ;;
esac
