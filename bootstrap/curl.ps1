Write-Host "Downloading and installing apps from curl.txt ..."

$downloadDir = "$env:USERPROFILE\Downloads"
$configFile = "$PSScriptRoot/config/curl.txt"

$entries = Get-Content $configFile |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' -and ($_ -match '#windows' -or $_ -notmatch '#linux|#macos') }

foreach ($entry in $entries) {
    $cleaned = $entry -replace '#\w+', '' | ForEach-Object { $_.Trim() }
    $parts = $cleaned -split '\|'
    $url = $parts[0].Trim()
    $filename = if ($parts.Length -gt 1) { $parts[1].Trim() } else { [System.IO.Path]::GetFileName($url) }
    $outputPath = Join-Path $downloadDir $filename
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($filename)
    $extension = [System.IO.Path]::GetExtension($filename).ToLower()

    Write-Host "Downloading $filename ..."
    try {
        curl.exe -L -sS -o $outputPath $url

        switch ($extension) {
            ".msi" {
                Write-Host "Installing $filename ..."
                Start-Process msiexec.exe -ArgumentList "/i", "`"$outputPath`"", "/quiet", "/norestart" -Wait
            }
            ".exe" {
                Write-Host "Running $filename ..."
                Start-Process -FilePath $outputPath -Wait
            }
            ".zip" {
                $extractPath = Join-Path $env:LOCALAPPDATA $baseName
                Write-Host "Extracting to $extractPath ..."

                if (Test-Path $extractPath) { Remove-Item -Path $extractPath -Recurse -Force }
                Expand-Archive -Path $outputPath -DestinationPath $extractPath -Force

                # Find main executable
                $exe = Get-ChildItem -Path $extractPath -Filter "*GUI.exe" -Recurse | Select-Object -First 1
                if (-not $exe) { $exe = Get-ChildItem -Path $extractPath -Filter "*.exe" -Recurse | Select-Object -First 1 }

                if ($exe) {
                    $shell = New-Object -ComObject WScript.Shell

                    # Start Menu shortcut
                    $startMenuPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$baseName.lnk"
                    $shortcut = $shell.CreateShortcut($startMenuPath)
                    $shortcut.TargetPath = $exe.FullName
                    $shortcut.WorkingDirectory = $exe.DirectoryName
                    $shortcut.Save()

                    # Startup shortcut
                    $startupPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\$baseName.lnk"
                    $shortcut = $shell.CreateShortcut($startupPath)
                    $shortcut.TargetPath = $exe.FullName
                    $shortcut.WorkingDirectory = $exe.DirectoryName
                    $shortcut.Save()

                    Write-Host "Created shortcuts for $baseName"
                }
            }
        }
        Write-Host "Completed: $filename" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed: $filename - $_" -ForegroundColor Red
    }
}

Write-Host "Done."
