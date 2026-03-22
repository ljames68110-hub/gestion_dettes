# update.ps1 - Mise a jour Gestion Perso
param(
    [string]$Repo = "ljames68110-hub/gestion_dettes",
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host ""
Write-Host "======================================"
Write-Host "   Gestion Perso - Mise a jour"
Write-Host "======================================"
Write-Host ""

# 1. Verifier connexion internet
try {
    $null = Invoke-WebRequest -Uri "https://api.github.com" -TimeoutSec 5 -UseBasicParsing
} catch {
    Write-Host "ERREUR : Pas de connexion internet."
    exit 1
}

# 2. Recuperer la derniere version
$apiUrl = "https://api.github.com/repos/$Repo/releases/latest"
Write-Host "Verification de la derniere version..."

try {
    $headers = @{ "User-Agent" = "GestionPerso-Updater" }
    $release = Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -Headers $headers | ConvertFrom-Json
} catch {
    Write-Host "ERREUR : Impossible de contacter GitHub API"
    exit 1
}

$newVersion = $release.tag_name
$asset      = $release.assets | Where-Object { $_.name -eq "gestion_dettes.exe" } | Select-Object -First 1
if (-not $asset) {
    Write-Host "ERREUR : Exe introuvable dans la release $newVersion"
    exit 1
}
$assetUrl    = $asset.browser_download_url
$expectedSha = $null  # SHA verifie si latest.json dispo

Write-Host "Derniere version disponible : $newVersion"

# 3. Verifier la version actuelle
$localJson = Join-Path $InstallDir "latest.json"
$currentVersion = "0.0.0"
if (Test-Path $localJson) {
    try {
        $local = Get-Content $localJson -Raw | ConvertFrom-Json
        $currentVersion = $local.version
    } catch {}
}

Write-Host "Version actuelle : $currentVersion"

if ($newVersion -eq $currentVersion) {
    Write-Host ""
    Write-Host "Vous etes deja a jour ! ($currentVersion)"
    Write-Host ""
    Read-Host "Appuyez sur Entree pour quitter"
    exit 0
}

Write-Host ""
Write-Host "Mise a jour disponible : $currentVersion -> $newVersion"
$confirm = Read-Host "Voulez-vous mettre a jour ? Tapez O pour Oui"
if ($confirm -notmatch "^[Oo]") {
    Write-Host "Mise a jour annulee."
    exit 0
}

# 4. Fermer l app si elle tourne
Write-Host ""
Write-Host "Fermeture de l application..."
$procs = Get-Process -Name "gestion_dettes" -ErrorAction SilentlyContinue
if ($procs) {
    $procs | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "Application fermee."
}

# 5. Telecharger le nouvel exe
$exeName  = "gestion_dettes.exe"
$tmpExe   = Join-Path $InstallDir "gestion_dettes_new.exe"
$finalExe = Join-Path $InstallDir $exeName

Write-Host ""
Write-Host "Telechargement de $newVersion..."

try {
    Invoke-WebRequest -Uri $assetUrl -OutFile $tmpExe -UseBasicParsing
    Write-Host "Telechargement termine."
} catch {
    Write-Host "ERREUR telechargement : $_"
    if (Test-Path $tmpExe) { Remove-Item $tmpExe -Force }
    exit 1
}

# 6. Verifier le SHA256
if ($expectedSha) {
    Write-Host "Verification SHA256..."
    $actualSha = (Get-FileHash $tmpExe -Algorithm SHA256).Hash.ToLower()
    if ($actualSha -ne $expectedSha.Trim().ToLower()) {
        Write-Host "ERREUR : SHA256 invalide ! Fichier corrompu."
        Remove-Item $tmpExe -Force
        exit 1
    }
    Write-Host "SHA256 OK."
}

# 7. Remplacer l exe
Write-Host "Installation..."
if (Test-Path $finalExe) {
    $backupExe = Join-Path $InstallDir "gestion_dettes_backup.exe"
    Copy-Item $finalExe $backupExe -Force
}
Move-Item $tmpExe $finalExe -Force
Write-Host "Exe mis a jour."

# 8. Mettre a jour latest.json
$latest | ConvertTo-Json | Out-File -FilePath $localJson -Encoding utf8
Write-Host "latest.json mis a jour."

# 9. Nettoyer backup
$backupExe = Join-Path $InstallDir "gestion_dettes_backup.exe"
if (Test-Path $backupExe) { Remove-Item $backupExe -Force }

Write-Host ""
Write-Host "======================================"
Write-Host "   Mise a jour $newVersion installee !"
Write-Host "======================================"
Write-Host ""

# 10. Proposer de relancer
$relaunch = Read-Host "Relancer Gestion Perso ? Tapez O pour Oui"
if ($relaunch -match "^[Oo]") {
    Start-Process $finalExe
}

Write-Host "Termine."