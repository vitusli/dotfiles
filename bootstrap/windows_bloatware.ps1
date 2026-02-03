Write-Host "Removing Windows bloatware..."
Get-Content "$PSScriptRoot/config/windows-bloatware.txt" |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' } |
    ForEach-Object {
        $pkg = (-split $_)[0]
        Get-AppxPackage -AllUsers -Name $pkg -ErrorAction SilentlyContinue | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
    }
Write-Host "Bloatware removal complete."
