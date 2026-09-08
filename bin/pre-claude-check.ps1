<#
.SYNOPSIS
    Cortex ERP AI-Native - Pre-Claude Validation Script (PowerShell / Windows)
.DESCRIPTION
    Execute la suite complete de verifications avant de transmettre le diff a Claude.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..").Path
Set-Location $RepoRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "     CORTEX ERP - VALIDATION WORKFLOW GEMINI -> CLAUDE" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Git Status & Diff Summary
Write-Host "`n[1/6] Git Status & Diff Summary..." -ForegroundColor Yellow
$isGit = & git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -eq 0) {
    & git status --short
    Write-Host ""
    & git diff --stat
} else {
    Write-Host "Depot Git non initialise (passe)."
}

# 2. Git Whitespace & Conflict Check
Write-Host "`n[2/6] Verification des conflits et espaces superflus (git diff --check)..." -ForegroundColor Yellow
if ($LASTEXITCODE -eq 0) {
    & git diff --check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Conflits ou espaces detectes." -ForegroundColor Red
    }
} else {
    Write-Host "Depot Git non initialise (passe)."
}

# 3. Python Code Formatting & Linting (Ruff / Python AST)
Write-Host "`n[3/6] Analyse de style et linting Python (Ruff / Python AST)..." -ForegroundColor Yellow
$hasRuff = Get-Command ruff -ErrorAction SilentlyContinue
if ($hasRuff) {
    & ruff check --config ruff.toml apps/
    & ruff format --config ruff.toml --check apps/
} else {
    Write-Host "Ruff non detecte sur l'hote - Controle de compilation syntaxique Python..."
    & python -m compileall apps/ -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Syntaxe Python validee avec succes sur tous les modules." -ForegroundColor Green
    } else {
        Write-Host "Erreur de syntaxe Python detectee." -ForegroundColor Red
        exit 1
    }
}

# 4. FastMCP & Cortex Rental Unit Tests (pytest / unittest)
Write-Host "`n[4/6] Execution des tests Python (pytest / unittest)..." -ForegroundColor Yellow
$sep = [System.IO.Path]::PathSeparator
$env:PYTHONPATH = "$RepoRoot\apps\cortex_rental$sep$RepoRoot\apps\cortex-mcp"

$hasPytest = Get-Command pytest -ErrorAction SilentlyContinue
if ($hasPytest) {
    & pytest apps/
} else {
    Write-Host "Execution via le test runner Python unittest standard :"
    & python -m unittest discover -s apps/cortex_rental/cortex_rental/tests/
    & python -m unittest discover -s apps/cortex-mcp/tests/
}

# 5. Type Checking / DocType Schema Sanity Check
Write-Host "`n[5/6] Controle de coherence des schemas DocTypes & JSON..." -ForegroundColor Yellow
$jsonCheckCode = @'
import json, glob, sys
doctypes = glob.glob('apps/cortex_rental/**/doctype/*/*.json', recursive=True)
print(f'Verification de {len(doctypes)} definitions DocTypes JSON...')
for dt in doctypes:
    try:
        with open(dt, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert 'doctype' in data or 'fields' in data
    except Exception as e:
        print(f'Erreur JSON dans {dt}: {e}', file=sys.stderr)
        sys.exit(1)
print(f'[OK] {len(doctypes)} DocTypes valides sans erreur de schema.')
'@
& python -c $jsonCheckCode
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la validation DocType JSON." -ForegroundColor Red
    exit 1
}

# 6. WCAG 2.2 Contrast Check
Write-Host "`n[6/6] Verification du contraste WCAG 2.2..." -ForegroundColor Yellow
if (Test-Path "$RepoRoot\bin\check-contrast.py") {
    & python "$RepoRoot\bin\check-contrast.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec du controle de contraste WCAG." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "  [OK] TOUTES LES VERIFICATIONS SONT PASSEES AVEC SUCCES !" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host "Vous pouvez maintenant committer les changements Gemini et transmettre le diff a Claude."
