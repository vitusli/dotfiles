Write-Host "Disabling Windows services..."
Get-Content "$PSScriptRoot/config/windows-services.txt" |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' } |
    ForEach-Object { Invoke-Expression $_ }
Write-Host "Windows services disabled successfully."
