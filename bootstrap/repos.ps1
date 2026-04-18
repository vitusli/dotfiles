$ErrorActionPreference = "Stop"

$activeTags = @("windows")

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Skipping repos: gh is not installed yet."
    exit 0
}

& gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Skipping repos: gh is not authenticated yet (run: gh auth login)."
    exit 0
}

Write-Host "Cloning repositories..."
Get-Content "$PSScriptRoot/config/repos.txt" | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $lineTags = @([regex]::Matches($line, '#([A-Za-z0-9_-]+)') | ForEach-Object { $_.Groups[1].Value.ToLower() })
    if ($lineTags.Count -gt 0 -and -not ($lineTags | Where-Object { $activeTags -contains $_ })) {
        return
    }

    $dataPart = ($line -split '#', 2)[0].Trim()
    if (-not $dataPart) {
        return
    }

    $parts = $dataPart -split '\|', 2
    if ($parts.Count -lt 2) {
        return
    }

    $repo = $parts[0].Trim()
    $destinationParent = $parts[1].Trim().Replace('~', $HOME)
    $target = Join-Path $destinationParent ($repo.Split('/')[-1])

    if (Test-Path $target) {
        Write-Host "Skipping existing repo: $repo"
        return
    }

    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    gh repo clone $repo $target
}
Write-Host "Done."
