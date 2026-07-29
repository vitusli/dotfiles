$ErrorActionPreference = "Stop"

Write-Host "Setting up SSH key..."

$KeyPath = Join-Path $HOME ".ssh\id_ed25519"
$PubKeyPath = "$KeyPath.pub"
$SshDir = Split-Path -Parent $KeyPath

if (-not (Test-Path $SshDir)) {
    New-Item -ItemType Directory -Path $SshDir -Force | Out-Null
}

if (-not (Test-Path $KeyPath)) {
    ssh-keygen -t ed25519 -C "chezmoi-generated" -f $KeyPath -N ""
    if ($LASTEXITCODE -ne 0) {
        throw "ssh-keygen failed with exit code $LASTEXITCODE"
    }
}
else {
    Write-Host "SSH key already exists. Skipping generation."
}

$agentService = Get-Service ssh-agent -ErrorAction SilentlyContinue
if ($agentService -and $agentService.Status -ne 'Running') {
    Start-Service ssh-agent
}

ssh-add $KeyPath | Out-Null

$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    gh auth status *> $null
    if ($LASTEXITCODE -eq 0) {
        gh ssh-key add "$PubKeyPath" --title "$($env:COMPUTERNAME)-$(Get-Date -Format 'yyyyMMdd')" *> $null
    }
    else {
        Write-Host "gh is installed but not authenticated. Skipping GitHub SSH key upload."
    }
}
else {
    Write-Host "gh not found. Skipping GitHub SSH key upload."
}

Write-Host "SSH setup complete."
