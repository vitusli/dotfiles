Write-Host "Installing VS Code extensions..."
Get-Content "$PSScriptRoot/config/vscode.txt" | Where-Object { $_ -match '^[^#]' -and $_ -match '\S' } | ForEach-Object {
    code --install-extension $_
}
Write-Host "Done."
