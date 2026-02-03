Write-Host "Applying Windows registry tweaks..."
Get-Content "$PSScriptRoot/config/windows-registry.txt" |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' } |
    ForEach-Object { Invoke-Expression $_ }
Write-Host "Registry tweaks applied successfully."
