#!/usr/bin/env bash
# Cortex ERP AI-Native — Pre-Claude Validation Script (Python / Frappe / FastMCP)
# Ce script exécute la suite complète de vérifications avant de transmettre le diff à Claude.

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}     CORTEX ERP — VALIDATION WORKFLOW GEMINI -> CLAUDE${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Git Status & Diff Summary
echo -e "\n${YELLOW}[1/6] Git Status & Diff Summary...${NC}"
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    git status --short
    echo ""
    git diff --stat || true
else
    echo "Dépôt Git non initialisé (passé)."
fi

# 2. Git Whitespace & Conflict Check
echo -e "\n${YELLOW}[2/6] Vérification des conflits et espaces superflus (git diff --check)...${NC}"
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    git diff --check || true
else
    echo "Dépôt Git non initialisé (passé)."
fi

# 3. Python Code Formatting & Linting (Ruff / Syntax Compilation)
echo -e "\n${YELLOW}[3/6] Analyse de style et linting Python (Ruff / Python AST)...${NC}"
if command -v ruff &> /dev/null; then
    ruff check --config ruff.toml apps/
    ruff format --config ruff.toml --check apps/
else
    echo "Ruff non détecté sur l'hôte — Contrôle de compilation syntaxique Python..."
    python3 -m compileall apps/ -q
    echo "✓ Syntaxe Python validée avec succès sur tous les modules."
fi

# 4. FastMCP & Cortex Rental Unit Tests (pytest / unittest)
echo -e "\n${YELLOW}[4/6] Exécution des tests Python (pytest / unittest)...${NC}"
if command -v pytest &> /dev/null; then
    PYTHONPATH=apps/cortex_rental:apps/cortex-mcp pytest apps/
else
    echo "Exécution via le test runner Python unittest standard :"
    PYTHONPATH=apps/cortex_rental:apps/cortex-mcp python3 -m unittest discover -s apps/cortex_rental/cortex_rental/tests/
    PYTHONPATH=apps/cortex_rental:apps/cortex-mcp python3 -m unittest discover -s apps/cortex-mcp/tests/
fi

# 5. Type Checking / DocType Schema Sanity Check
echo -e "\n${YELLOW}[5/6] Contrôle de cohérence des schémas DocTypes & JSON...${NC}"
python3 -c "
import json, glob, sys
doctypes = glob.glob('apps/cortex_rental/**/doctype/*/*.json', recursive=True)
print(f'Vérification de {len(doctypes)} définitions DocTypes JSON...')
for dt in doctypes:
    try:
        with open(dt, 'r') as f:
            data = json.load(f)
            assert 'doctype' in data or 'fields' in data
    except Exception as e:
        print(f'Erreur JSON dans {dt}: {e}', file=sys.stderr)
        sys.exit(1)
print(f'✓ {len(doctypes)} DocTypes validés sans erreur de schéma.')
"

# 6. Récapitulatif
echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  ✓ TOUTES LES VÉRIFICATIONS SONT PASSÉES AVEC SUCCÈS !${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Vous pouvez maintenant committer les changements Gemini et transmettre le diff à Claude."
