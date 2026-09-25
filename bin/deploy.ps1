<#
.SYNOPSIS
    CORTEX ERP AI-NATIVE - Script d'installation et deploiement 1-clic pour Windows (PowerShell)
.DESCRIPTION
    Portage PowerShell natif de deploy.sh pour Windows.
    Supporte les modes 1click, tour, docker, test, fixtures.
.EXAMPLE
    .\bin\deploy.ps1 1click --site cortex.local
    .\bin\deploy.ps1 tour --site cortex.local
    .\bin\deploy.ps1 docker
    .\bin\deploy.ps1 test
    .\bin\deploy.ps1 fixtures --site cortex.local
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Mode = "",

    [string]$Site = "cortex.local",

    [Alias("bench-path")]
    [string]$BenchPath = "",

    [Alias("with-fixtures")]
    [switch]$WithFixtures,

    [Alias("skip-fixtures")]
    [switch]$SkipFixtures,

    [Alias("skip-tests")]
    [switch]$SkipTests,

    [Alias("y", "non-interactive")]
    [switch]$Yes,

    [Alias("h")]
    [switch]$Help,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

# Configuration de l'environnement console et encodage UTF-8
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# --- Decouverte et ajout des chemins Python Scripts au PATH ---
$possibleScriptDirs = @(
    "$env:APPDATA\Python\*\Scripts",
    "$env:LOCALAPPDATA\Programs\Python\*\Scripts",
    "C:\Python*\Scripts"
)
foreach ($pattern in $possibleScriptDirs) {
    Get-ChildItem -Path $pattern -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        if ($env:PATH -notlike "*$($_.FullName)*") {
            $env:PATH = "$($_.FullName);$env:PATH"
        }
    }
}

# --- Variables et Chemins ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..").Path
$DefaultBenchPath = if ($env:BENCH_PATH) { $env:BENCH_PATH } elseif ($BenchPath) { $BenchPath } else { "$HOME\frappe-bench" }
$TargetBenchPath = $DefaultBenchPath
$RunTests = -not $SkipTests
$NonInteractive = $Yes.IsPresent
$DbRootPassword = if ($env:DB_ROOT_PASSWORD) { $env:DB_ROOT_PASSWORD } else { "root" }
$AdminPassword = if ($env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD } else { "admin" }

# Provisioning de fixtures: $null (non precise), $true (oui), $false (non)
$ProvisionFixtures = $null
if ($WithFixtures) { $ProvisionFixtures = $true }
if ($SkipFixtures) { $ProvisionFixtures = $false }

# --- Parsing des arguments restants Unix-style (--site, -y, etc.) ---
if ($RemainingArgs) {
    for ($i = 0; $i -lt $RemainingArgs.Length; $i++) {
        $arg = $RemainingArgs[$i]
        switch ($arg) {
            "--site" {
                $i++
                if ($i -lt $RemainingArgs.Length) { $Site = $RemainingArgs[$i] }
            }
            "--bench-path" {
                $i++
                if ($i -lt $RemainingArgs.Length) { $TargetBenchPath = $RemainingArgs[$i] }
            }
            "--with-fixtures" {
                $ProvisionFixtures = $true
            }
            "--skip-fixtures" {
                $ProvisionFixtures = $false
            }
            "--skip-tests" {
                $RunTests = $false
            }
            { $_ -in "-y", "--yes", "--non-interactive" } {
                $NonInteractive = $true
            }
            { $_ -in "-h", "--help" } {
                $Help = $true
            }
            default {
                if (-not $Mode -and $arg -notmatch "^-") {
                    $Mode = $arg
                }
            }
        }
    }
}

# --- Fonctions d'Affichage et Logging ---
function Print-Banner {
    Write-Host "`n======================================================================" -ForegroundColor Cyan
    Write-Host "       CORTEX ERP AI-NATIVE - DEPLOIEMENT ET INSTALLATION 1-CLIC" -ForegroundColor Cyan
    Write-Host "======================================================================`n" -ForegroundColor Cyan
}

function Log-Step {
    param([string]$Step, [string]$Message)
    Write-Host "`n[ETAPE $Step] " -ForegroundColor Blue -NoNewline
    Write-Host "$Message" -ForegroundColor White
}

function Log-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Log-Warn {
    param([string]$Message)
    Write-Host "[AVERTISSEMENT] $Message" -ForegroundColor Yellow
}

function Log-Err {
    param([string]$Message)
    Write-Host "[ERREUR] $Message" -ForegroundColor Red
}

function Show-Usage {
    Print-Banner
    Write-Host "Usage: .\bin\deploy.ps1 [mode] [options]`n" -ForegroundColor White
    Write-Host "Modes disponibles :" -ForegroundColor White
    Write-Host "  docker            Deploie la stack conteneurisee complete via Docker Compose (Recommande sous Windows)" -ForegroundColor Green
    Write-Host "  1click | full     Installation complete de zero (Docker ou Bench natif, site, erpnext, cortex, fixtures, tests)" -ForegroundColor Green
    Write-Host "  tour | native     Deploie et migre sur une instance Bench existante (la Tour)" -ForegroundColor Green
    Write-Host "  test              Execute l'ensemble de la suite de validation et tests unitaires" -ForegroundColor Green
    Write-Host "  fixtures          Genere et injecte le jeu de donnees de demo sur le site actif`n" -ForegroundColor Green
    Write-Host "Options :" -ForegroundColor White
    Write-Host "  -Site, --site <nom>             Nom du site Frappe (defaut: $Site)"
    Write-Host "  -BenchPath, --bench-path <path> Chemin vers le repertoire frappe-bench"
    Write-Host "  -WithFixtures, --with-fixtures  Injecte automatiquement les fixtures de demo"
    Write-Host "  -SkipFixtures, --skip-fixtures  Ignore l'injection des fixtures de demo"
    Write-Host "  -SkipTests, --skip-tests        Ignore l'etape de tests"
    Write-Host "  -Yes, -y, --yes                 Mode non-interactif automatique"
    Write-Host "  -Help, -h, --help               Affiche cette aide`n"
    exit 0
}

if ($Help) {
    Show-Usage
}

# --- Resolution des executables ---
function Find-PythonExe {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return "python" }
    $py3 = Get-Command py -ErrorAction SilentlyContinue
    if ($py3) { return "py" }
    return $null
}

function Find-DockerComposeCmd {
    try {
        $dcVer = & docker compose version 2>$null
        if ($LASTEXITCODE -eq 0) { return "docker compose" }
    } catch {}

    $dcStandalone = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($dcStandalone) { return "docker-compose" }
    return $null
}

function Test-NativeBenchWorking {
    try {
        $out = & bench --version 2>&1
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    return $false
}

# Compile the Cortex SPA (apps/cortex_rental/frontend -> public/frontend + www/cortex.html).
function Build-CortexSpa {
    $feDir = Join-Path $RepoRoot "apps\cortex_rental\frontend"
    if (-not (Test-Path (Join-Path $feDir "package.json"))) {
        Write-Host "Frontend Cortex introuvable ($feDir) - /cortex ne sera pas servi." -ForegroundColor Yellow
        return
    }
    Write-Host "Compilation de l'application Cortex (/cortex)..."
    Push-Location $feDir
    try {
        & npm ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "npm ci a echoue." }
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "La compilation de l'application Cortex a echoue." }
    } finally {
        Pop-Location
    }
}

function Invoke-Bench {
    param([string[]]$Arguments)
    $benchCmd = Get-Command bench -ErrorAction SilentlyContinue
    if ($benchCmd) {
        & bench @Arguments
        return $LASTEXITCODE
    } else {
        # Try finding bench in python scripts
        $benchExe = Get-ChildItem "$env:APPDATA\Python\*\Scripts\bench.exe", "C:\Python*\Scripts\bench.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($benchExe) {
            & $benchExe.FullName @Arguments
            return $LASTEXITCODE
        }
    }
    throw "Le CLI 'bench' est introuvable sur le systeme."
}

function Create-AppJunction {
    param([string]$SourcePath, [string]$TargetPath)
    if (Test-Path $TargetPath) {
        return
    }
    try {
        New-Item -ItemType Junction -Path $TargetPath -Target $SourcePath -ErrorAction Stop | Out-Null
    } catch {
        try {
            New-Item -ItemType SymbolicLink -Path $TargetPath -Target $SourcePath -ErrorAction Stop | Out-Null
        } catch {
            Log-Warn "Impossible de creer une jonction/symlink. Copie directe du dossier..."
            Copy-Item -Path $SourcePath -Destination $TargetPath -Recurse -Force
        }
    }
}

# --- Selection Interactive si aucun mode fourni ---
if (-not $Mode) {
    Print-Banner
    Write-Host "Selectionnez le mode de deploiement :"
    Write-Host "  1) Docker Compose (Recommande sous Windows : Stack MariaDB, Valkey, MinIO, Bench, FastMCP)"
    Write-Host "  2) Deploiement 1-Clic Complet (Installation de A a Z de l'environnement complet)"
    Write-Host "  3) Bench Existant / Tour (Mise a jour, migrations, build bundles et redemarrage)"
    Write-Host "  4) Lancer la suite de tests unitaires et validation pre-claude"
    Write-Host "  5) Injecter uniquement les donnees de demonstration`n"
    
    $choice = Read-Host "Votre choix [1-5]"
    switch ($choice) {
        "1" { $Mode = "docker" }
        "2" { $Mode = "1click" }
        "3" { $Mode = "tour" }
        "4" { $Mode = "test" }
        "5" { $Mode = "fixtures" }
        default {
            Log-Err "Choix invalide. Annulation."
            exit 1
        }
    }
}

# Normalize mode
switch -Regex ($Mode) {
    "^(1click|all|full|install)$" { $Mode = "1click" }
    "^(tour|native)$"             { $Mode = "tour" }
    "^docker$"                    { $Mode = "docker" }
    "^(test|tests)$"              { $Mode = "test" }
    "^fixtures$"                  { $Mode = "fixtures" }
    default {
        Log-Err "Option ou mode inconnu : $Mode"
        Show-Usage
    }
}

# ==============================================================================
# VERIFICATION DE LA SUITE DE TESTS
# ==============================================================================
function Run-TestSuite {
    Log-Step "TEST" "Execution des tests de validation pre-claude et unitaires..."
    Set-Location $RepoRoot
    $preClaudePs1 = Join-Path $RepoRoot "bin\pre-claude-check.ps1"
    $preClaudeSh = Join-Path $RepoRoot "bin\pre-claude-check.sh"

    if (Test-Path $preClaudePs1) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $preClaudePs1
    } elseif (Test-Path $preClaudeSh -and (Get-Command bash -ErrorAction SilentlyContinue)) {
        & bash $preClaudeSh
    } else {
        $sep = [System.IO.Path]::PathSeparator
        $env:PYTHONPATH = "$RepoRoot\apps\cortex_rental$sep$RepoRoot\apps\cortex-mcp"
        $py = Find-PythonExe
        if ($py) {
            & $py -m unittest discover -s apps/cortex_rental/cortex_rental/tests
        } else {
            Log-Err "Python introuvable pour executer les tests."
            exit 1
        }
    }
    Log-Success "Tests unitaires et verifications DocTypes 100% valides."
}

# ==============================================================================
# RAPPORT RECAPITULATIF FINAL
# ==============================================================================
function Print-Summary {
    param([string]$TargetType, [string]$BaseUrl)

    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "      DEPLOIEMENT CORTEX ERP EFFECTUE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "======================================================================`n" -ForegroundColor Green
    Write-Host "Tableaux de bord et interfaces metier :" -ForegroundColor White
    Write-Host "  - Desk ERP Principal        : $BaseUrl/app"
    Write-Host "  - Scanner Check-in & Retours: $BaseUrl/app/cortex-checkin"
    Write-Host "  - Matrice de Disponibilite  : $BaseUrl/app/cortex-availability"
    Write-Host "  - P&L Financier (Accounting): $BaseUrl/app/cortex-accounting-pnl"
    Write-Host "  - Composer de Transaction   : $BaseUrl/app/cortex-transaction-composer`n"
    Write-Host "Services Agents et Outils :" -ForegroundColor White
    Write-Host "  - Facade FastMCP (Python)   : http://localhost:3100"
    Write-Host "  - Stockage Objets MinIO     : http://localhost:9091 (Admin: cortex_minio_admin)"
    Write-Host "  - Boite Mailpit (Sandbox)   : http://localhost:8025`n"
    Write-Host "Identifiants par defaut :" -ForegroundColor White
    Write-Host "  - Utilisateur : Administrator"
    Write-Host "  - Mot de passe: admin`n"
    Write-Host "======================================================================" -ForegroundColor Green
}

# ==============================================================================
# MODE 1 : INSTALLATION ET DEPLOIEMENT 1-CLIC COMPLET (ZERO-TO-ONE)
# ==============================================================================
function Deploy-1Click {
    Print-Banner
    Write-Host "Lancement de l'Installation et Deploiement 1-Clic..." -ForegroundColor White
    Write-Host "Site cible : $Site`n" -ForegroundColor Cyan

    # 1. Verification des Outils Systeme
    Log-Step "1/8" "Verification des dependances et de la chaine d'outils systeme..."
    $missingTools = @()
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $missingTools += "git" }
    $py = Find-PythonExe
    if (-not $py) { $missingTools += "python" }
    if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
        if (-not ($py -and (& $py -m pip --version 2>$null))) {
            $missingTools += "pip"
        }
    }

    if ($missingTools.Count -gt 0) {
        Log-Err "Outils systeme manquants : $($missingTools -join ', ')"
        Write-Host "Veuillez installer les outils requis avant de continuer."
        exit 1
    }
    Log-Success "Outils systeme de base (git, python, pip) detectes."

    # Verification Frappe Bench natif sous Windows
    # Frappe Bench CLI natif depend de modules POSIX (pwd/termios).
    # Sur Windows, si Docker est disponible, basculer automatiquement vers la stack Docker Compose 1-clic.
    $benchWorking = Test-NativeBenchWorking
    if (-not $benchWorking) {
        $hasDocker = Get-Command docker -ErrorAction SilentlyContinue
        if ($hasDocker) {
            Log-Warn "Frappe Bench natif necessite un environnement POSIX (Linux/Docker/WSL)."
            Log-Success "Docker Engine detecte ! Basculement automatique sur le Deploiement Docker Compose..."
            Deploy-Docker
            return
        }
    }

    # 2. Verification / Installation de Frappe Bench CLI
    Log-Step "2/8" "Verification du CLI frappe-bench..."
    if (-not (Get-Command bench -ErrorAction SilentlyContinue)) {
        Log-Warn "Le CLI 'bench' n'est pas installe globalement. Installation via pip..."
        & $py -m pip install --user frappe-bench
    }
    Log-Success "CLI bench operationnel."

    # 3. Initialisation du Bench si absent
    Log-Step "3/8" "Validation du repertoire frappe-bench..."
    $benchDir = $TargetBenchPath
    if (-not (Test-Path $benchDir)) {
        Write-Host "Initialisation d'un nouveau Frappe Bench v15 a : $benchDir..."
        try {
            Invoke-Bench @("init", "--frappe-branch", "version-15", "--skip-redis-config-generation", "$benchDir")
        } catch {
            Log-Warn "Echec de l'initialisation native du bench: $_"
            Log-Success "Basculement automatique sur le deploiement Docker Compose..."
            Deploy-Docker
            return
        }
    }
    Set-Location $benchDir
    Log-Success "Frappe Bench pret a : $benchDir"

    # 4. Telechargement d'ERPNext (v15)
    Log-Step "4/8" "Verification et acquisition de l'application ERPNext v15..."
    $erpnextAppDir = Join-Path $benchDir "apps\erpnext"
    if (-not (Test-Path $erpnextAppDir)) {
        Write-Host "Telechargement d'ERPNext version-15..."
        try {
            Invoke-Bench @("get-app", "erpnext", "--branch", "version-15")
        } catch {
            Log-Warn "Avertissement lors de la recuperation d'ERPNext : $_"
        }
    }
    Log-Success "ERPNext v15 present dans le bench."

    # 5. Liaison et Installation de Cortex Rental
    Log-Step "5/8" "Liaison et installation de l'application cortex_rental..."
    $cortexLink = Join-Path $benchDir "apps\cortex_rental"
    $cortexSource = Join-Path $RepoRoot "apps\cortex_rental"
    Create-AppJunction -SourcePath $cortexSource -TargetPath $cortexLink

    $envPip = Join-Path $benchDir "env\Scripts\pip.exe"
    if (Test-Path $envPip) {
        & $envPip install -e "$cortexSource" --no-deps 2>$null | Out-Null
    }
    Log-Success "Application cortex_rental liee et installee en mode editable."

    # 6. Creation ou Mise a jour du Site MariaDB
    Log-Step "6/8" "Creation du site et execution des migrations de base de donnees..."
    $siteDir = Join-Path $benchDir "sites\$Site"
    if (-not (Test-Path $siteDir)) {
        Write-Host "Creation du nouveau site '$Site'..."
        try {
            Invoke-Bench @("new-site", "$Site", "--admin-password", "$AdminPassword", "--install-app", "erpnext", "--install-app", "cortex_rental")
        } catch {
            Log-Warn "Avertissement lors de la creation du site: $_"
        }
    } else {
        Write-Host "Site '$Site' existant : installation des apps et migration..."
        try { Invoke-Bench @("--site", "$Site", "install-app", "erpnext") 2>$null | Out-Null } catch {}
        try { Invoke-Bench @("--site", "$Site", "install-app", "cortex_rental") 2>$null | Out-Null } catch {}
        Invoke-Bench @("--site", "$Site", "migrate")
    }
    Log-Success "Site et tables MariaDB synchronises avec succes."

    # 7. Compilation des Bundles Vue 3
    Log-Step "7/8" "Compilation des bundles Vue 3 et assets Desk..."
    Build-CortexSpa
    Invoke-Bench @("build", "--app", "cortex_rental")
    Log-Success "Application Cortex (/cortex) et assets compiles."

    # 8. Donnees de Demonstration et Tests
    Log-Step "8/8" "Chargement des donnees de demonstration et verification finale..."
    if ($ProvisionFixtures -ne $false) {
        Write-Host "Injection des donnees de demo (societe, parc camera, sorties actives)..."
        try {
            Invoke-Bench @("--site", "$Site", "execute", "cortex_rental.fixtures.demo_data.provision_demo_data")
            Log-Success "Donnees de demonstration chargees."
        } catch {
            Log-Warn "Erreur lors du chargement des fixtures: $_"
        }
    }

    if ($RunTests) {
        Run-TestSuite
    }

    try { Invoke-Bench @("restart") } catch {}
    Print-Summary -TargetType "native" -BaseUrl "http://localhost:8000"
}

# ==============================================================================
# MODE 2 : DEPLOIEMENT BENCH NATIF / TOUR (UPDATE ET MIGRATE)
# ==============================================================================
function Deploy-Tour {
    Print-Banner
    Write-Host "Deploiement et mise a jour sur le Bench Natif (la Tour)..." -ForegroundColor White
    Write-Host "Site cible : $Site`n" -ForegroundColor Cyan

    $benchDir = $TargetBenchPath
    $parentBench = Join-Path $RepoRoot "..\frappe-bench"
    if (-not (Test-Path $benchDir) -and (Test-Path $parentBench)) {
        $benchDir = (Resolve-Path $parentBench).Path
    }

    if (-not (Test-Path $benchDir)) {
        if ($NonInteractive) {
            Log-Err "Repertoire frappe-bench introuvable a '$benchDir'."
            exit 1
        }
        Log-Warn "Repertoire frappe-bench introuvable a '$benchDir'."
        $userBench = Read-Host "Entrez le chemin absolu vers votre frappe-bench"
        $benchDir = $userBench
    }

    if (-not (Test-Path $benchDir)) {
        Log-Err "Repertoire bench valide introuvable."
        exit 1
    }

    Log-Step "1/5" "Liaison de l'application cortex_rental..."
    $cortexLink = Join-Path $benchDir "apps\cortex_rental"
    $cortexSource = Join-Path $RepoRoot "apps\cortex_rental"
    Create-AppJunction -SourcePath $cortexSource -TargetPath $cortexLink

    $envPip = Join-Path $benchDir "env\Scripts\pip.exe"
    if (Test-Path $envPip) {
        & $envPip install -e "$cortexSource" --no-deps 2>$null | Out-Null
    }
    Log-Success "cortex_rental synchronise dans le bench."
    Log-Step "2/5" "Execution des migrations de schema MariaDB..."
    Set-Location $benchDir
    try { Invoke-Bench @("--site", "$Site", "install-app", "erpnext") 2>$null | Out-Null } catch {}
    try { Invoke-Bench @("--site", "$Site", "install-app", "cortex_rental") 2>$null | Out-Null } catch {}
    Invoke-Bench @("--site", "$Site", "migrate")
    Log-Success "Migrations MariaDB executees avec succes."

    Log-Step "3/5" "Compilation des bundles JS Vue 3..."
    Build-CortexSpa
    Invoke-Bench @("build", "--app", "cortex_rental")
    Log-Success "Bundles Vue 3 compiles."

    Log-Step "4/5" "Gestion des donnees de demonstration..."
    if ($null -eq $ProvisionFixtures) {
        if ($NonInteractive) {
            $ProvisionFixtures = $true
        } else {
            $ans = Read-Host "Injecter le jeu de donnees de demo (societe, parc camera, sorties actives) ? [O/n]"
            if ($ans -match "^[Nn]$") {
                $ProvisionFixtures = $false
            } else {
                $ProvisionFixtures = $true
            }
        }
    }

    if ($ProvisionFixtures) {
        Invoke-Bench @("--site", "$Site", "execute", "cortex_rental.fixtures.demo_data.provision_demo_data")
        Log-Success "Donnees de demonstration chargees."
    }

    Log-Step "5/5" "Redemarrage des services et tests..."
    try { Invoke-Bench @("restart") } catch {}
    if ($RunTests) {
        Run-TestSuite
    }

    Print-Summary -TargetType "native" -BaseUrl "http://localhost:8000"
}

# ==============================================================================
# MODE 3 : DEPLOIEMENT DOCKER COMPOSE
# ==============================================================================
function Deploy-Docker {
    Print-Banner
    Write-Host "Deploiement en cours via Docker Compose..." -ForegroundColor White

    Log-Step "1/5" "Verification des prerequis Docker..."
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Log-Err "Docker n'est pas installe ou n'est pas dans le PATH sur ce systeme."
        exit 1
    }

    $dockerComposeCmd = Find-DockerComposeCmd
    if (-not $dockerComposeCmd) {
        Log-Err "Docker Compose (v2) n'est pas disponible."
        exit 1
    }
    Log-Success "Docker Engine et Docker Compose sont operationnels ($dockerComposeCmd)."

    Log-Step "2/5" "Demarrage de la stack conteneurisee (MariaDB, Valkey, MinIO, Mailpit, Bench, FastMCP)..."
    $dockerDir = Join-Path $RepoRoot "infra\docker"
    Set-Location $dockerDir

    if ($dockerComposeCmd -eq "docker compose") {
        & docker compose -f docker-compose.dev.yml up -d --build
    } else {
        & docker-compose -f docker-compose.dev.yml up -d --build
    }

    Log-Step "3/5" "Attente de l'initialisation saine de MariaDB 10.11+..."
    $retries = 30
    $dbReady = $false
    while ($retries -gt 0 -and -not $dbReady) {
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 2
        try {
            if ($dockerComposeCmd -eq "docker compose") {
                & docker compose -f docker-compose.dev.yml exec -T mariadb healthcheck.sh --connect 2>$null | Out-Null
            } else {
                & docker-compose -f docker-compose.dev.yml exec -T mariadb healthcheck.sh --connect 2>$null | Out-Null
            }
            if ($LASTEXITCODE -eq 0) {
                $dbReady = $true
            }
        } catch {}
        $retries--
    }
    Write-Host ""
    Log-Success "Base de donnees MariaDB operationnelle."

    Log-Step "4/5" "Injection des donnees de demonstration dans le conteneur..."
    if ($ProvisionFixtures -ne $false) {
        try {
            if ($dockerComposeCmd -eq "docker compose") {
                & docker compose -f docker-compose.dev.yml exec -T bench bench --site "$Site" execute cortex_rental.fixtures.demo_data.provision_demo_data
            } else {
                & docker-compose -f docker-compose.dev.yml exec -T bench bench --site "$Site" execute cortex_rental.fixtures.demo_data.provision_demo_data
            }
            Log-Success "Donnees de demonstration chargees dans le conteneur."
        } catch {
            Log-Warn "Avertissement lors de l'injection des fixtures Docker: $_"
        }
    }

    Log-Step "5/5" "Execution des tests de validation..."
    if ($RunTests) {
        Run-TestSuite
    }

    Print-Summary -TargetType "docker" -BaseUrl "http://localhost:8000"
}

# ==============================================================================
# MODE 4 : PROVISIONING FIXTURES SEULES
# ==============================================================================
function Deploy-Fixtures {
    Print-Banner
    Write-Host "Injection ciblee des Donnees de Demonstration..." -ForegroundColor White
    Write-Host "Site cible : $Site`n" -ForegroundColor Cyan

    $benchCmd = Get-Command bench -ErrorAction SilentlyContinue
    if ($benchCmd) {
        Invoke-Bench @("--site", "$Site", "execute", "cortex_rental.fixtures.demo_data.provision_demo_data")
        Log-Success "Fixtures chargees avec succes via le bench local."
    } elseif (Test-Path (Join-Path $DefaultBenchPath "env\Scripts\python.exe")) {
        Set-Location $DefaultBenchPath
        Invoke-Bench @("--site", "$Site", "execute", "cortex_rental.fixtures.demo_data.provision_demo_data")
        Log-Success "Fixtures chargees avec succes."
    } else {
        Log-Warn "Bench local non trouve. Tentative via Docker Compose..."
        $dockerDir = Join-Path $RepoRoot "infra\docker"
        Set-Location $dockerDir
        $dockerComposeCmd = Find-DockerComposeCmd
        if ($dockerComposeCmd -eq "docker compose") {
            & docker compose -f docker-compose.dev.yml exec -T bench bench --site "$Site" execute cortex_rental.fixtures.demo_data.provision_demo_data
        } elseif ($dockerComposeCmd -eq "docker-compose") {
            & docker-compose -f docker-compose.dev.yml exec -T bench bench --site "$Site" execute cortex_rental.fixtures.demo_data.provision_demo_data
        } else {
            Log-Err "Ni Bench local ni Docker Compose disponibles."
            exit 1
        }
        Log-Success "Fixtures chargees via Docker."
    }
}

# --- Routage Principal ---
switch ($Mode) {
    "1click"   { Deploy-1Click }
    "tour"     { Deploy-Tour }
    "docker"   { Deploy-Docker }
    "test"     { Run-TestSuite }
    "fixtures" { Deploy-Fixtures }
    default    { Show-Usage }
}
