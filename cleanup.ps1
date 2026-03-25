# cleanup.ps1 — Nettoyage du dossier projet DebtManager
# Lance depuis le dossier du projet : .\cleanup.ps1

$projectDir = $PSScriptRoot

Write-Host "Nettoyage de : $projectDir" -ForegroundColor Cyan
Write-Host ""

# Fichiers à garder absolument
$keep = @(
    "main.py", "api.py", "db.py", "updater.py",
    "requirements.txt", "installer.iss", "release.yml",
    "latest.json", "sha256.txt", "README.md", "dettes.db",
    "cleanup.ps1", ".gitignore"
)

# Dossiers à garder
$keepDirs = @("web", ".github", ".git")

$deleted = 0

# Supprimer fichiers inutiles à la racine
Get-ChildItem -Path $projectDir -File | ForEach-Object {
    $name = $_.Name
    if ($name -notin $keep) {
        Write-Host "  Suppression fichier : $name" -ForegroundColor Yellow
        Remove-Item $_.FullName -Force
        $deleted++
    }
}

# Supprimer dossiers inutiles
Get-ChildItem -Path $projectDir -Directory | ForEach-Object {
    $name = $_.Name
    if ($name -notin $keepDirs) {
        Write-Host "  Suppression dossier : $name\" -ForegroundColor Yellow
        Remove-Item $_.FullName -Recurse -Force
        $deleted++
    }
}

# Supprimer cache Python
$pycache = Join-Path $projectDir "__pycache__"
if (Test-Path $pycache) {
    Remove-Item $pycache -Recurse -Force
    Write-Host "  Suppression cache : __pycache__\" -ForegroundColor Yellow
    $deleted++
}

# Supprimer fichiers .pyc
Get-ChildItem -Path $projectDir -Filter "*.pyc" -Recurse | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "  Suppression : $($_.Name)" -ForegroundColor Yellow
    $deleted++
}

# Supprimer fichiers .spec PyInstaller
Get-ChildItem -Path $projectDir -Filter "*.spec" | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "  Suppression spec : $($_.Name)" -ForegroundColor Yellow
    $deleted++
}

Write-Host ""
if ($deleted -eq 0) {
    Write-Host "Dossier deja propre !" -ForegroundColor Green
} else {
    Write-Host "$deleted element(s) supprime(s)." -ForegroundColor Green
}

Write-Host ""
Write-Host "Fichiers restants :" -ForegroundColor Cyan
Get-ChildItem -Path $projectDir | Select-Object Name, LastWriteTime | Format-Table -AutoSize
