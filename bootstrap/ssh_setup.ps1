bootstrap/ssh_setup.ps1
Write-Host "Setting up SSH key..."

$KeyPath = "$HOME\.ssh\id_ed25519"

if (-not (Test-Path $KeyPath)) {
    ssh-keygen -t ed25519 -C "chezmoi-generated" -f $KeyPath -N '""'
    
    if ((Get-Service ssh-agent).Status -ne 'Running') {
        Start-Service ssh-agent
    }
    ssh-add $KeyPath

    gh ssh-key add "$KeyPath.pub" --title "$($env:COMPUTERNAME)-$(Get-Date -Format 'yyyyMMdd')"
} else {
    Write-Host "SSH key already exists. Skipping generation."
}

Write-Host "SSH setup complete."
