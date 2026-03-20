param(
  [string]$RepoPath = "C:\Users\Yoann\Documents\GitHub\gestion_dettes",
  [string]$Tag = "v0.1.16",
  [string]$CommitMessage = "ci: use GITHUB_TOKEN for release + upload and create latest.json PR"
)

# Aller dans le repo
Set-Location -Path $RepoPath

# Vérifier working tree propre
$porcelain = git status --porcelain
if ($porcelain) {
  Write-Host "Working tree not clean. Commit or stash changes before running this script." -ForegroundColor Yellow
  exit 1
}

# Contenu du workflow (here-string non interpolé pour préserver ${ { ... } } )
$workflow = @'
name: Build and Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install system deps
        run: |
          sudo apt-get update
          sudo apt-get install -y jq zip unzip

      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller

      - name: Build exe with PyInstaller
        run: |
          rm -rf dist build
          pyinstaller --onefile main.py --name gestion_dettes
          ls -la dist

      - name: Create GitHub Release
        id: create_release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref_name }}
          release_name: ${{ github.ref_name }}
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload exe to release
        id: upload_asset
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: dist/gestion_dettes
          asset_name: gestion_dettes.exe
          asset_content_type: application/octet-stream
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Compute sha256 of exe
        id: compute_sha
        run: |
          ASSET_PATH="dist/gestion_dettes"
          if [ -f "$ASSET_PATH" ]; then
            sha256sum "$ASSET_PATH" | awk '{print $1}' > dist/gestion_dettes.sha256
            echo "sha256=$(cat dist/gestion_dettes.sha256)" >> $GITHUB_OUTPUT
          else
            echo "sha256=" >> $GITHUB_OUTPUT
          fi

      - name: Prepare latest.json
        id: prepare_latest
        run: |
          TAG="${{ github.ref_name }}"
          RELEASE_URL="${{ steps.create_release.outputs.html_url }}"
          ASSET_URL="${{ steps.upload_asset.outputs.browser_download_url }}"
          SHA256="${{ steps.compute_sha.outputs.sha256 }}"
          published_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
          cat > latest.json <<EOF
{
  "version": "${TAG}",
  "tag": "${TAG}",
  "release_url": "${RELEASE_URL}",
  "asset_url": "${ASSET_URL}",
  "sha256": "${SHA256}",
  "published_at": "${published_at}"
}
EOF
          cat latest.json

      - name: Commit and push latest.json branch
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          BRANCH="update-latest-${{ github.ref_name }}"
          git checkout -b "$BRANCH"
          git add latest.json
          git commit -m "chore: update latest.json for ${{ github.ref_name }}" || echo "No changes to commit"
          git push --set-upstream origin "$BRANCH"

      - name: Create Pull Request for latest.json
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "chore: update latest.json for ${{ github.ref_name }}"
          branch: "update-latest-${{ github.ref_name }}"
          title: "Update latest.json for ${{ github.ref_name }}"
          body: |
            This PR updates latest.json with the new release information.
          base: main
          labels: automated, release
'@

# Écrire le fichier workflow
$workflowPath = Join-Path -Path $RepoPath -ChildPath ".github\workflows\release.yml"
$dir = Split-Path $workflowPath -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

Set-Content -Path $workflowPath -Value $workflow -Encoding UTF8
Write-Host "Wrote workflow to $workflowPath" -ForegroundColor Green

# Ajouter au git et commit seulement si changement
git add .github/workflows/release.yml

# Vérifier s'il y a quelque chose à committer
$staged = git diff --cached --name-only
if (-not $staged) {
  Write-Host "Aucun changement à committer pour .github/workflows/release.yml" -ForegroundColor Yellow
} else {
  git commit -m $CommitMessage
  git push origin main
  Write-Host "Fichier committé et poussé sur main." -ForegroundColor Green
}

# Créer et pousser le tag (remplace si existe localement)
$existingTag = git tag -l $Tag
if ($existingTag) {
  git tag -d $Tag
}
git tag $Tag
git push origin $Tag --force

Write-Host "Tag $Tag créé et poussé. Vérifie GitHub Actions pour le run." -ForegroundColor Green