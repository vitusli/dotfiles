# Windows Hardening Script
# Disables system components that can't be removed via normal uninstall

# Check if running with admin privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "This script requires administrator privileges. Restarting with elevated privileges..."
    Start-Process -FilePath PowerShell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "Windows Hardening..." -ForegroundColor Cyan

# Components to disable by renaming the executable
$disableList = @(
    @{
        Name = "LiveCaptions"
        Path = "C:\Windows\System32\LiveCaptions.exe"
    }
)

foreach ($component in $disableList) {
    $exePath = $component.Path
    $disabledPath = "$exePath.FUCK_OFF"

    if (Test-Path $exePath) {
        Write-Host "Disabling $($component.Name)..." -ForegroundColor Yellow
        try {
            # Take ownership
            $null = takeown /f $exePath 2>&1
            # Grant permissions (ignore errors about SID mapping)
            $null = icacls $exePath /grant "${env:USERNAME}:F" 2>&1
            # Rename to disable
            Rename-Item -Path $exePath -NewName ([System.IO.Path]::GetFileName($disabledPath)) -Force -ErrorAction Stop
            Write-Host "  $($component.Name) disabled successfully." -ForegroundColor Green
        } catch {
            Write-Host "  Failed to disable $($component.Name): $_" -ForegroundColor Red
        }
    } elseif (Test-Path $disabledPath) {
        Write-Host "  $($component.Name) is already disabled." -ForegroundColor DarkGray
    } else {
        Write-Host "  $($component.Name) not found, skipping." -ForegroundColor DarkGray
    }
}

Write-Host "Windows Hardening complete." -ForegroundColor Cyan
