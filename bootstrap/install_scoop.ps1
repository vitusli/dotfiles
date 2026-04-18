$ErrorActionPreference = "Stop"

if (Get-Command scoop -ErrorAction SilentlyContinue) {
    Write-Host "Scoop already installed"
    exit 0
}

Write-Host "Installing Scoop..."
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
Invoke-RestMethod -Uri "https://get.scoop.sh" | Invoke-Expression
