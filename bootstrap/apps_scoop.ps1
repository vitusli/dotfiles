Write-Host "Installing Scoop packages ..."
$apps = Get-Content "$PSScriptRoot/config/cli.txt", "$PSScriptRoot/config/gui.txt" |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' -and ($_ -match '#windows' -or $_ -notmatch '#linux|#macos') } |
    ForEach-Object { (-split $_)[0] }
if ($apps)
{ scoop install $apps
}
Write-Host "Scoop packages installed successfully."
