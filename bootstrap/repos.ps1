Write-Host "Cloning repositories..."
Get-Content "$PSScriptRoot/config/repos.txt" | Where-Object { $_ -match '^[^#]' } | ForEach-Object {
    $r, $d = $_ -split '\|'
    $target = Join-Path ($d.Replace('~', $HOME)) ($r.Split('/')[-1])
    if (!(Test-Path $target))
    { gh repo clone $r $target 
    }
}
Write-Host "Done."
