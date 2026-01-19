# ============================================================================
# VS CODE EXTENSIONS MODULE
# Handles VS Code extension installation for Windows
# ============================================================================

# Source libraries if not already loaded
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LibDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "lib"

if (-not (Get-Command Log-Info -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "logging.ps1")
}

if (-not (Get-Command Load-Config -ErrorAction SilentlyContinue))
{
    . (Join-Path $LibDir "config.ps1")
}

# ============================================================================
# VS CODE VERIFICATION
# ============================================================================

# Check if VS Code CLI is available
function Verify-VSCodeInstalled
{
    $null = Get-Command code -ErrorAction SilentlyContinue
    return $?
}

# Get VS Code version
function Get-VSCodeVersion
{
    if (Verify-VSCodeInstalled)
    {
        $version = & code --version 2>$null | Select-Object -First 1
        return $version
    }
    return $null
}

# Check if a specific extension is installed
function Verify-ExtensionInstalled
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Extension
    )

    if (-not (Verify-VSCodeInstalled))
    {
        return $false
    }

    $installed = @(& code --list-extensions 2>$null)
    return ($installed -match [regex]::Escape($Extension))
}

# Get list of installed extensions
function Get-InstalledExtensions
{
    if (Verify-VSCodeInstalled)
    {
        return @(& code --list-extensions 2>$null)
    }
    return @()
}

# Count installed extensions
function Get-ExtensionCount
{
    if (Verify-VSCodeInstalled)
    {
        return (Get-InstalledExtensions).Count
    }
    return 0
}

# ============================================================================
# EXTENSION INSTALLATION
# ============================================================================

# Install a single extension
function Install-Extension
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Extension
    )

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Error "VS Code not installed"
        return $false
    }

    # Check if already installed
    if (Verify-ExtensionInstalled -Extension $Extension)
    {
        Log-Success "$Extension (already installed)"
        return $true
    }

    Log-Info "Installing $Extension..."
    & code --install-extension $Extension --force 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE

    # Verify installation
    if (Verify-ExtensionInstalled -Extension $Extension)
    {
        Log-Success "$Extension installed"
        return $true
    } elseif ($exitCode -eq 0)
    {
        Log-Success "$Extension install command completed"
        return $true
    } else
    {
        Log-Error "$Extension installation failed"
        return $false
    }
}

# Install extensions from config file
function Install-VSCodeExtensions
{
    Log-Header "Installing VS Code Extensions"

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Warning "VS Code not installed, skipping extensions"
        return $true
    }

    Log-Info "VS Code version: $(Get-VSCodeVersion)"
    Log-Info "Loading extensions from config..."

    $extensions = @()
    if (Get-Command Load-AllPackages -ErrorAction SilentlyContinue)
    {
        $extensions = Load-AllPackages "vscode.txt"
    } elseif (Get-Command Load-Config -ErrorAction SilentlyContinue)
    {
        $extensions = Load-Config "vscode.txt"
    }

    if (-not $extensions -or $extensions.Count -eq 0)
    {
        Log-Info "No extensions defined in config"
        return $true
    }

    $installed = Get-InstalledExtensions
    $toInstall = @()
    $alreadyInstalled = 0

    # First pass: check what's already installed
    foreach ($extension in $extensions)
    {
        if (-not $extension)
        { continue 
        }

        if ($installed -match [regex]::Escape($extension))
        {
            Log-Success $extension
            $alreadyInstalled++
        } else
        {
            $toInstall += $extension
        }
    }

    if ($toInstall.Count -eq 0)
    {
        Log-Info "All $alreadyInstalled extensions already installed"
        return $true
    }

    Log-Info "Installing $($toInstall.Count) new extensions..."

    $failed = @()

    # Second pass: install missing extensions
    foreach ($extension in $toInstall)
    {
        Log-Info "Installing $extension..."
        & code --install-extension $extension --force 2>&1 | Out-Null

        # Verify installation
        $newInstalled = Get-InstalledExtensions
        if ($newInstalled -match [regex]::Escape($extension))
        {
            Log-Success "$extension installed"
        } else
        {
            Log-Warning "$extension installation may have failed"
            $failed += $extension
        }
    }

    # Summary
    $installedCount = $toInstall.Count - $failed.Count
    if ($failed.Count -gt 0)
    {
        Log-Warning "Installed $installedCount/$($toInstall.Count) extensions. Failed: $($failed -join ', ')"
        return $false
    } else
    {
        Log-Success "All extensions installed successfully"
        return $true
    }
}

# ============================================================================
# EXTENSION REMOVAL
# ============================================================================

# Uninstall a single extension
function Uninstall-Extension
{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Extension
    )

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Error "VS Code not installed"
        return $false
    }

    # Check if installed
    if (-not (Verify-ExtensionInstalled -Extension $Extension))
    {
        Log-Info "$Extension not installed"
        return $true
    }

    Log-Info "Uninstalling $Extension..."
    & code --uninstall-extension $Extension 2>&1 | Out-Null
    $exitCode = $LASTEXITCODE

    # Verify removal
    if (-not (Verify-ExtensionInstalled -Extension $Extension))
    {
        Log-Success "$Extension uninstalled"
        return $true
    } elseif ($exitCode -eq 0)
    {
        Log-Success "$Extension uninstall command completed"
        return $true
    } else
    {
        Log-Error "$Extension uninstall failed"
        return $false
    }
}

# ============================================================================
# EXTENSION SYNC
# ============================================================================

# Sync extensions: install missing, optionally remove unlisted
function Sync-Extensions
{
    param(
        [switch]$RemoveUnlisted
    )

    Log-Header "Syncing VS Code Extensions"

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Warning "VS Code not installed"
        return $false
    }

    Log-Info "Loading desired extensions from config..."

    $desiredExtensions = @()
    if (Get-Command Load-AllPackages -ErrorAction SilentlyContinue)
    {
        $desiredExtensions = Load-AllPackages "vscode.txt"
    } elseif (Get-Command Load-Config -ErrorAction SilentlyContinue)
    {
        $desiredExtensions = Load-Config "vscode.txt"
    }

    $installedExtensions = Get-InstalledExtensions

    # Find extensions to install
    $toInstall = @()
    foreach ($ext in $desiredExtensions)
    {
        if (-not $ext)
        { continue 
        }
        $found = $false
        foreach ($installed in $installedExtensions)
        {
            if ($ext.ToLower() -eq $installed.ToLower())
            {
                $found = $true
                break
            }
        }
        if (-not $found)
        {
            $toInstall += $ext
        }
    }

    # Find extensions to remove (if requested)
    $toRemove = @()
    if ($RemoveUnlisted)
    {
        foreach ($installed in $installedExtensions)
        {
            if (-not $installed)
            { continue 
            }
            $found = $false
            foreach ($ext in $desiredExtensions)
            {
                if ($installed.ToLower() -eq $ext.ToLower())
                {
                    $found = $true
                    break
                }
            }
            if (-not $found)
            {
                $toRemove += $installed
            }
        }
    }

    # Install missing
    if ($toInstall.Count -gt 0)
    {
        Log-Info "Installing $($toInstall.Count) missing extensions..."
        foreach ($ext in $toInstall)
        {
            Install-Extension -Extension $ext | Out-Null
        }
    } else
    {
        Log-Success "No extensions to install"
    }

    # Remove unlisted
    if ($toRemove.Count -gt 0)
    {
        Log-Warning "Extensions to remove ($($toRemove.Count)):"
        foreach ($ext in $toRemove)
        {
            Write-Output "  - $ext"
        }

        $confirm = Read-Host "Remove these extensions? (y/n)"
        if ($confirm -match "^[yY]$")
        {
            foreach ($ext in $toRemove)
            {
                Uninstall-Extension -Extension $ext | Out-Null
            }
        } else
        {
            Log-Info "Removal skipped by user"
        }
    }

    Log-Success "Extension sync complete"
    return $true
}

# ============================================================================
# EXTENSION UPDATE
# ============================================================================

# Update all extensions
function Update-Extensions
{
    Log-Header "Updating VS Code Extensions"

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Warning "VS Code not installed"
        return $false
    }

    Log-Info "Updating all extensions..."

    $extensions = Get-InstalledExtensions
    $updated = 0

    foreach ($extension in $extensions)
    {
        if (-not $extension)
        { continue 
        }

        Log-Info "Updating $extension..."
        & code --install-extension $extension --force 2>&1 | Out-Null
        $updated++
    }

    Log-Success "Updated $updated extensions"
    return $true
}

# ============================================================================
# EXTENSION EXPORT
# ============================================================================

# Export installed extensions to stdout (for config file)
function Export-Extensions
{
    Log-Header "Exporting Installed Extensions"

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Error "VS Code not installed"
        return $null
    }

    Log-Info "Installed extensions:"
    Write-Output ""
    $extensions = Get-InstalledExtensions
    $extensions | ForEach-Object { Write-Output $_ }
    Write-Output ""

    $count = $extensions.Count
    Log-Info "Total: $count extensions"

    return $extensions
}

# ============================================================================
# STATUS
# ============================================================================

# Show VS Code extension status
function Get-VSCodeStatus
{
    Log-Header "VS Code Extension Status"

    if (Verify-VSCodeInstalled)
    {
        Log-Success "VS Code: installed ($(Get-VSCodeVersion))"
    } else
    {
        Log-Error "VS Code: not installed"
        return
    }

    # Count installed
    $installedCount = Get-ExtensionCount
    Log-Info "Installed extensions: $installedCount"

    # Compare with config
    $desiredExtensions = @()
    if (Get-Command Load-AllPackages -ErrorAction SilentlyContinue)
    {
        $desiredExtensions = Load-AllPackages "vscode.txt"
    } elseif (Get-Command Load-Config -ErrorAction SilentlyContinue)
    {
        $desiredExtensions = Load-Config "vscode.txt"
    }

    $desiredCount = $desiredExtensions.Count
    Log-Info "Desired extensions (from config): $desiredCount"

    # Find differences
    $missing = 0
    foreach ($ext in $desiredExtensions)
    {
        if (-not $ext)
        { continue 
        }
        if (-not (Verify-ExtensionInstalled -Extension $ext))
        {
            $missing++
        }
    }

    if ($missing -eq 0)
    {
        Log-Success "All desired extensions are installed"
    } else
    {
        Log-Warning "$missing extensions from config are not installed"
    }
}

# ============================================================================
# COMBINED SETUP
# ============================================================================

# Run full VS Code extensions setup
function Setup-VSCodeExtensions
{
    $errors = 0

    if (-not (Verify-VSCodeInstalled))
    {
        Log-Warning "VS Code not installed, skipping extensions"
        return $true
    }

    if (-not (Install-VSCodeExtensions))
    { $errors++
    }

    if ($errors -gt 0)
    {
        Log-Warning "VS Code extensions setup completed with issues"
        return $false
    }

    Log-Success "VS Code extensions setup complete"
    return $true
}
